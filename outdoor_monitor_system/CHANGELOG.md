# 改动记录

## v1.1 — 2026-05-21 降低非人类误检率

### 问题描述
非人类运动物体（动物、汽车、风吹草动）被误报为人员入侵，识别准确率低。

### 根本原因
1. HOG 置信度阈值 `min_weight=0.2` 过低，几乎不做筛选
2. MOG2 背景建模对户外场景过于敏感（`var_threshold=25`）
3. 无宽高比过滤，横向物体（动物/车）可通过 HOG
4. 单帧触发报警，偶发干扰直接报警
5. `DARK_THRESHOLD` 已声明但从未启用，夜间噪点可触发

---

### 文件改动

#### `motion_detection.py`

| 参数 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| `MotionDetector.var_threshold` 默认值 | `25` | `40` | 减少户外光照/风动误触发 |
| `PersonDetector.min_weight` 默认值 | `0.2` | `0.65` | 只保留 HOG 高置信度检测 |
| `PersonDetector.detect` — 新增过滤 | 无 | `sh/sw < 1.5` 或 `sh < 64px` 则丢弃 | 人体框高宽比约 2~3，排除动物/车辆的横向框 |

#### `monitor_uploader.py`

| 参数 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| `Config.PERSON_MIN_WEIGHT` | `0.2` | `0.65` | 与检测器保持一致 |
| `Config.PERSON_CONFIRM_FRAMES`（新增） | — | `2` | 连续 N 帧检测到人才触发，可调 |
| 主循环 — 低照度跳过 | 未实现 | `gray.mean() < DARK_THRESHOLD` 时跳过 | 启用原本闲置的 `DARK_THRESHOLD=55` |
| 主循环 — 连续帧防抖 | 无 | `confirm_streak` 计数达到 `PERSON_CONFIRM_FRAMES` 才报警 | 防止单帧闪烁误报 |

---

---

## v1.2 — 2026-05-21 修复镜头抖动误报 + 推送图模糊问题

### 问题描述
- 相机被物理碰动后，对准桌面/线材/手仍触发报警
- 报警推送图人脸模糊，为运动中抓取的模糊帧

### 根本原因
1. 抖动阈值 0.65 太高，相机缓慢移位时运动面积不触发
2. 抖动后未重置背景模型，MOG2 继续用旧背景判断，导致持续误报
3. 模糊帧（运动模糊）未过滤，直接进入 HOG 检测
4. 事件图使用首帧而非最清晰帧

### 文件改动

#### `motion_detection.py`
- 新增模块级函数 `measure_sharpness(frame)` — Laplacian 方差衡量清晰度

#### `monitor_uploader.py`

| 参数/逻辑 | 旧值/旧行为 | 新值/新行为 | 说明 |
|-----------|------------|------------|------|
| `Config.CAMERA_SHAKE_RATIO` | `0.65` | `0.45` | 更早拦截镜头移位 |
| `Config.BLUR_THRESHOLD`（新增） | — | `80` | Laplacian 方差低于此值跳过帧 |
| `Config.SHAKE_COOLDOWN_FRAMES`（新增） | — | `20` | 抖动后冷却约 2 秒 |
| `init_camera` | 无 | `CAP_PROP_AUTOFOCUS=1` | 启用摄像头自动对焦 |
| 镜头抖动处理 | 仅跳过当帧 | 重置背景模型 + 进入冷却期 | 防止 MOG2 用错误背景继续判断 |
| 模糊帧过滤 | 无 | `measure_sharpness < BLUR_THRESHOLD` 跳过 | 相机晃动时画面模糊，直接丢弃 |
| 事件推送图 | 首个确认帧 | 确认后连抓 5 帧取最清晰 | 人脸更清晰 |

---

---

## v1.3 — 2026-05-21 肤色验证 + 轮廓坐标修复

### 问题描述
样本图 2/3/4 中完全没有人体元素（仅显示器、线材、桌面），但仍触发报警。
HOG 对整个 ROI 全局扫描，矩形线束/显示器边框能以 ≥0.65 置信度通过几何过滤。

### 根本原因
纯几何过滤（权重阈值 + 宽高比）无法区分人体与非人体矩形物体，需要引入语义特征。

### 文件改动

#### `motion_detection.py`

| 位置 | 改动 | 说明 |
|------|------|------|
| `PersonDetector` 新增 `_has_skin_tone()` | — | 检测 HOG 候选框内肤色像素占比 |
| `PersonDetector.detect()` 循环内 | 宽高比过滤后加肤色检查 | 无肤色（线材/显示器/桌面）→ 拒绝 |
| `MotionDetector.detect()` 返回值 | `valid_contours` → `valid_contours_shifted` | 修复轮廓坐标始终为 ROI 局部坐标的 bug |

### 肤色检测逻辑
- HSV 范围 H∈[0,25], S∈[20,255], V∈[70,255]，覆盖亚洲/深色/浅色多种肤色
- 绝对像素数 ≥ 80 **且** 占候选框面积 ≥ 5% 才通过
- 显示器、线材、木质桌面均不含此范围的肤色像素

---

### 调参建议

如果实际部署后仍有漏报或误报，可按以下方向调整：

- **误报多（非人触发）**：提高 `PERSON_MIN_WEIGHT`（0.7~0.8）或增大 `PERSON_CONFIRM_FRAMES`（3）
- **漏报多（真实人员未触发）**：降低 `PERSON_MIN_WEIGHT`（0.55~0.6）或减小 `PERSON_CONFIRM_FRAMES`（1）
- **夜间噪点**：提高 `DARK_THRESHOLD`（60~80）
- **风吹草木**：提高 `var_threshold`（45~50）或缩小 `ROI` 区域避开植被
