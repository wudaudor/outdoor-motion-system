# 户外监控系统

基于 VisionFive 2 单板计算机的低功耗定时监控系统，实现**人物经过 → 自动拍照 → 蜂鸣/LED 报警 → 上传图片 → 微信推送通知**的完整链路。

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                 VisionFive 2 监控端               │
│                                                 │
│  USB 摄像头 ──→ motion_detection.py             │
│                  （MOG2 背景建模运动检测）         │
│                       │ 检测到人                 │
│                       ↓                         │
│              monitor_uploader.py                │
│              ① 保存事件图片                      │
│              ② GPIOController.alert()           │
│                 LED 闪 + 蜂鸣（后台线程）         │
│              ③ 上传图片到服务器                   │
│              ④ 调用 push_notification.py         │
│                 发送微信通知                      │
│              ⑤ 录制 10 秒事件视频                │
└─────────────────────────────────────────────────┘
                        │ HTTP POST
                        ↓
┌─────────────────────────────────────────────────┐
│              server_receive.py（服务器端）        │
│  接收文件 → 存储 → 提供图片访问 URL               │
└─────────────────────────────────────────────────┘
                        │ 图片 URL 写入推送消息
                        ↓
                   用户微信通知
```

---

## 文件说明

| 文件 | 运行位置 | 职责 |
|------|----------|------|
| `monitor_uploader.py` | VisionFive 2 | 主程序：调度摄像头、检测、报警、上传、推送 |
| `motion_detection.py` | VisionFive 2 | 运动检测模块：MOG2 背景建模，判断是否有人经过 |
| `push_notification.py` | VisionFive 2 | 微信推送模块：通过 Server酱 API 向手机发送通知 |
| `http_client.py` | 通用 | 轻量 HTTP 封装工具（GET/POST/PUT/DELETE） |
| `server_receive.py` | 服务器 | Flask 文件接收服务：存储上传图片并提供 Web 浏览 |

---

## 部署步骤

### 第一步：在 Windows 上部署服务器

#### 1.1 安装 Python

前往 [https://www.python.org/downloads/](https://www.python.org/downloads/) 下载 Python 3.10 或以上版本。

安装时勾选 **"Add Python to PATH"**，否则后续命令行无法识别 `python` 命令。

安装完成后验证：

```cmd
python --version
```

#### 1.2 安装 Flask

打开命令提示符（Win + R → 输入 `cmd`）：

```cmd
pip install flask
```

#### 1.3 启动服务器

进入项目目录，运行服务器：

```cmd
cd C:\你的项目路径\outdoor_monitor_system
python server_receive.py
```

看到以下输出说明启动成功：

```
========================================
  监控系统 - Flask 文件服务器
========================================
  上传地址: http://your-server-ip:5000/upload
  Web界面:  http://your-server-ip:5000/
========================================
 * Running on http://0.0.0.0:5000
```

#### 1.4 查看本机 IP 地址

打开命令提示符：

```cmd
ipconfig
```

找到当前网络适配器（以太网或 WLAN）下的 **IPv4 地址**，例如 `192.168.1.100`，这就是 VisionFive 2 上传时填写的地址。

> VisionFive 2 和 Windows 电脑必须在**同一局域网**下（连同一个路由器/交换机），否则无法互相访问。

#### 1.5 开放 Windows 防火墙端口

Flask 默认使用 5000 端口，Windows 防火墙默认拦截外部访问，需要手动放行。

**方法一：命令行（管理员权限）**

以管理员身份打开命令提示符（右键开始菜单 → "终端(管理员)"），执行：

```cmd
netsh advfirewall firewall add rule name="Flask Monitor 5000" protocol=TCP dir=in localport=5000 action=allow
```

**方法二：图形界面**

1. 打开「控制面板」→「Windows Defender 防火墙」→「高级设置」
2. 左侧点击「入站规则」→ 右侧点击「新建规则」
3. 规则类型选「端口」→ 下一步
4. 选「TCP」，特定本地端口填 `5000` → 下一步
5. 操作选「允许连接」→ 下一步
6. 三个复选框全勾（域/专用/公用）→ 下一步
7. 名称填 `Flask Monitor 5000` → 完成

#### 1.6 验证服务器可访问

在 Windows 本机浏览器访问：

```
http://localhost:5000/health
```

在局域网内另一台设备（或 VisionFive 2）访问：

```
http://192.168.1.100:5000/health
```

两者均返回 `OK` 说明部署完成。

#### 1.7 设置开机自启（可选）

如果希望 Windows 开机后服务器自动运行，创建一个批处理文件 `start_server.bat`：

```bat
@echo off
cd /d C:\你的项目路径\outdoor_monitor_system
python server_receive.py
```

然后将该 `.bat` 文件的快捷方式放入开机启动目录：

按 Win + R，输入 `shell:startup`，打开启动文件夹，将快捷方式拖入即可。

---

### 第一步补充：网络连通方案

服务器和开发板必须能互相访问 5000 端口。按实际网络环境选择对应方案：

| 场景 | 方案 |
|------|------|
| 有路由器且有管理权限 | 方案 A：路由器局域网 |
| 校园网 / 需要门户登录的网络 | 方案 B：Windows ICS 网线直连 |
| 户外部署，开发板独立联网 | 方案 C：云服务器 |

---

#### 方案 A：路由器局域网（有路由器管理权限）

开发板和电脑都接同一路由器，在路由器管理页给电脑绑定固定内网 IP，之后上传地址永远不变。

**第一步：查看电脑网卡 MAC 地址**

```cmd
ipconfig /all
```

找到当前网络适配器下的「物理地址」，格式为 `XX-XX-XX-XX-XX-XX`。

**第二步：在路由器绑定固定 IP**

1. 浏览器打开路由器管理页（通常为 `192.168.1.1` 或 `192.168.0.1`）
2. 找到「DHCP 地址绑定」或「静态 IP 分配」
3. 按上一步的 MAC 地址绑定一个固定 IP，例如 `192.168.1.100`

**第三步：验证连通性**

在开发板上执行：

```bash
ping 192.168.1.100
curl http://192.168.1.100:5000/health
# 返回 OK 说明可以正常上传
```

**开发板填写的上传地址：**

```bash
--upload-url http://192.168.1.100:5000/upload
```

---

#### 方案 B：Windows ICS 网线直连（校园网 / 手机热点 / 需门户登录的网络）

电脑连上已认证的网络（校园 WiFi 登录后、手机热点），再用网线把电脑和开发板直连，通过 Windows 网络共享（ICS）把网络桥接给开发板。电脑在网线口的 IP 固定为 `192.168.137.1`，开发板自动获取 `192.168.137.x` 的地址，两者互通且开发板可以上网。

**第一步：电脑连上已认证的网络**

校园网在浏览器完成门户登录，确保电脑本身已能正常上网。

**第二步：用网线连接电脑和开发板**

电脑网口 ←→ 网线 ←→ 开发板网口。

**第三步：开启 ICS**

1. Win + R 输入 `ncpa.cpl` 打开网络连接
2. 右键「当前已联网的适配器（校园网 WiFi 或热点）」→ 属性 → 共享
3. 勾选「允许其他网络用户通过此计算机的 Internet 连接来连接」
4. 下拉菜单选择网线对应的以太网适配器 → 确定

**第四步：开发板确认获取到 IP**

```bash
ip a
# 以太网口应显示 192.168.137.x 的地址
```

若没有自动获取，手动设置：

```bash
sudo ip addr add 192.168.137.2/24 dev eth0
sudo ip route add default via 192.168.137.1
```

**第五步：验证连通性**

```bash
ping 192.168.137.1
curl http://192.168.137.1:5000/health
# 返回 OK 说明连通
```

**开发板填写的上传地址（固定不变）：**

```bash
--upload-url http://192.168.137.1:5000/upload
```

---

#### 方案 C：云服务器（户外部署，开发板插 4G 网卡）

开发板在户外通过 USB 4G 网卡自行联网，电脑不在同一网络，无法互访。此时将 `server_receive.py` 部署到云服务器上（有固定公网 IP），开发板直接上传到云服务器，与电脑是否开机无关。

**云服务器选择**

阿里云、腾讯云均提供学生优惠机（约 10 元/月），系统选 Ubuntu 22.04。

**第一步：在云服务器上部署**

SSH 登录云服务器后：

```bash
pip3 install flask
# 将 server_receive.py 上传到服务器，然后运行
python3 server_receive.py
```

**第二步：开放云服务器安全组端口**

在云服务器控制台找到「安全组」或「防火墙」，添加入站规则：协议 TCP，端口 5000，来源 `0.0.0.0/0`。

**第三步：开发板填写云服务器公网 IP**

```bash
--upload-url http://云服务器公网IP:5000/upload
```

验证：

```bash
curl http://云服务器公网IP:5000/health
# 返回 OK
```

> 微信推送消息中的图片链接也指向云服务器，手机点击可直接查看，无需电脑保持开机。

---

### 第二步：配置微信推送（Server酱）

Server酱是一个将消息推送到微信的免费服务。

1. 访问 [https://sct.ftqq.com/](https://sct.ftqq.com/) 用微信扫码登录
2. 登录后进入「SendKey」页面，复制你的 SCKEY（形如 `SCT12345abcdef`）
3. 关注「方糖」微信公众号（扫码即可），之后推送消息会出现在该公众号对话框中

测试推送是否可用：

```bash
python3 push_notification.py SCT你的SCKEY
# 手机微信收到「✅ 测试消息」则说明配置正确
```

---

### 第三步：VisionFive 2 端部署

安装依赖：

```bash
sudo apt install -y python3 python3-pip python3-opencv
pip3 install requests
```

确认摄像头已识别：

```bash
ls /dev/video*
# 应出现 /dev/video4 或类似设备节点
```

---

#### 启动方式一：前台运行（调试用）

直接在终端运行，日志实时打印，Ctrl+C 退出：

```bash
python3 monitor_uploader.py \
    --camera-index 4 \
    --device-id VF2-01 \
    --upload-url http://你的服务器IP:5000/upload \
    --sckey SCT你的SCKEY \
    --work-sec 20 \
    --record-sec 10
```

适合首次调试，确认运动检测和推送均正常后再改为后台模式。

---

#### 启动方式二：nohup 后台挂起（快速部署）

关闭 SSH 终端后进程继续运行，日志写入文件：

```bash
nohup python3 monitor_uploader.py \
    --camera-index 4 \
    --device-id VF2-01 \
    --upload-url http://你的服务器IP:5000/upload \
    --sckey SCT你的SCKEY \
    --work-sec 20 \
    --record-sec 10 \
    > ~/outdoor_monitor/logs/monitor.log 2>&1 &

echo "进程 PID: $!"
```

查看日志：

```bash
tail -f ~/outdoor_monitor/logs/monitor.log
```

停止进程：

```bash
# 查找 PID
pgrep -f monitor_uploader.py

# 终止
kill <PID>
```

---

#### 启动方式三：screen 会话（开发调试推荐）

screen 可以在断开 SSH 后保持会话，随时重新接入查看实时输出：

```bash
# 安装 screen（Debian 通常已预装）
sudo apt install -y screen

# 新建名为 monitor 的会话并启动程序
screen -S monitor python3 monitor_uploader.py \
    --camera-index 4 \
    --device-id VF2-01 \
    --upload-url http://你的服务器IP:5000/upload \
    --sckey SCT你的SCKEY \
    --work-sec 20 \
    --record-sec 10
```

断开 SSH 后程序继续运行。下次 SSH 登录后重新接入会话：

```bash
screen -r monitor
```

在会话内按 `Ctrl+A` 再按 `D` 可挂起回到普通终端，不终止程序。

---

#### 启动方式四：systemd 服务（开机自启 / 生产部署）

板子上电后自动启动，异常退出后自动重启，适合正式部署。

创建服务文件 `/etc/systemd/system/outdoor-monitor.service`：

```ini
[Unit]
Description=Outdoor Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=on-failure
RestartSec=10
WorkingDirectory=/home/user/outdoor_monitor
ExecStart=/usr/bin/python3 /home/user/outdoor_monitor/monitor_uploader.py \
    --camera-index 4 \
    --device-id VF2-01 \
    --upload-url http://你的服务器IP:5000/upload \
    --sckey SCT你的SCKEY \
    --work-sec 20 \
    --record-sec 10
StandardOutput=append:/home/user/outdoor_monitor/logs/monitor.log
StandardError=append:/home/user/outdoor_monitor/logs/monitor.log

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now outdoor-monitor
```

常用管理命令：

```bash
sudo systemctl status outdoor-monitor    # 查看运行状态
sudo systemctl stop outdoor-monitor      # 停止
sudo systemctl restart outdoor-monitor   # 重启
journalctl -u outdoor-monitor -f         # 实时查看系统日志
```

---

#### 四种方式对比

| 方式 | SSH 断开后存活 | 开机自启 | 实时查看输出 | 适用场景 |
|------|--------------|---------|------------|---------|
| 前台运行 | ✗ | ✗ | ✓ | 首次调试 |
| nohup | ✓ | ✗ | 查日志文件 | 快速临时部署 |
| screen | ✓ | ✗ | ✓（重新接入） | 开发调试 |
| systemd | ✓ | ✓ | journalctl | 正式生产部署 |

---

## 硬件接线

### LED 指示灯

```
物理引脚 36（GPIO36）→ 470Ω 电阻 → LED 正极
LED 负极 → 物理引脚 34（GND）
```

### 有源蜂鸣器

```
物理引脚 38（GPIO38）→ 蜂鸣器正极（＋）
蜂鸣器负极（－）→ 物理引脚 34（GND）
```

> 如果蜂鸣器工作电流超过 10mA，需加 S8050 三极管驱动，不可直连 GPIO。

### USB 摄像头

直接插入 VisionFive 2 的 USB Host 口，系统自动识别为 `/dev/videoX`。

---

## 模块工作原理

### `motion_detection.py` — 运动检测

使用 OpenCV 的 **MOG2 背景建模**算法逐帧分析摄像头画面：

1. 对每一帧调用 `bg_subtractor.apply(frame)`，得到前景掩码（运动区域为白色）
2. 用开运算去除噪点，用闭运算填充空洞
3. 提取连通轮廓，过滤掉面积小于 `area_threshold`（默认 1200 像素）的区域，排除树叶晃动等干扰
4. 有效轮廓数 > 0 时返回 `is_motion = True`

MOG2 对光线缓慢变化（云遮日、时间推移）具有自适应能力，适合户外场景。

```python
detector = MotionDetector(roi=(320, 180, 640, 360), area_threshold=1200)
is_motion, mask, contours = detector.detect(frame)
```

`roi` 参数限定检测区域为 `(x, y, w, h)`，只关注画面中的特定位置，减少误报。

---

### `push_notification.py` — 微信推送

封装 Server酱 HTTP API，调用一次即向绑定微信发送通知：

```python
pusher = ServerChanPusher(sckey="SCT你的KEY")
pusher.send_motion_alert(device_id="VF2-01", image_url="http://服务器/uploads/xxx.jpg")
```

推送到微信的消息格式（Markdown）：

```
🚨 监控报警 [VF2-01]

检测到人员入侵
- 设备ID: VF2-01
- 检测时间: 2026-04-29 15:30:45
- 位置: 监控区域
- 检测目标数: 1 个

事件图片: [点击查看](http://服务器IP:5000/uploads/xxx.jpg)
```

`send_status()` 用于发送设备上线/离线等状态通知，`send_test()` 用于部署后验证推送链路。

---

### `monitor_uploader.py` — 主监控程序

每次执行一个**监控周期**，流程如下：

```
初始化摄像头、GPIO、运动检测器、推送器
         ↓
抓拍一张定时图 → 上传到服务器
         ↓
进入运动检测循环（持续 work-sec 秒）
    ├── 读取摄像头帧
    ├── 调用 MotionDetector.detect()
    └── 检测到运动？
          是 → 保存事件图片
             → GPIOController.alert()  ← LED 闪 3 次 + 蜂鸣 3 次（后台线程）
             → 上传图片到服务器
             → 发送微信推送通知
             → 录制 10 秒事件视频
          否 → 继续读帧
         ↓
周期结束，GPIO 清理
```

**`GPIOController.alert()` 的非阻塞设计**：蜂鸣和 LED 闪烁在独立的后台 `Thread` 中执行，主循环在报警的同时立刻继续处理上传和录像，不会因等待 GPIO 操作而延迟。

---

### `server_receive.py` — 文件服务器

Flask 应用，部署在有公网 IP 的服务器上：

- 接收 VisionFive 2 上传的图片/视频，按 `时间戳_设备ID_类型.扩展名` 重命名存储
- 通过 `/uploads/<文件名>` 提供 HTTP 访问，URL 直接写入微信推送消息，手机点击可查看图片
- `/` 提供简单的 Web 界面，显示最近 20 条上传记录

---

## 命令行参数

```
python3 monitor_uploader.py [选项]

  --camera-index  摄像头设备号，默认 4（对应 /dev/video4）
  --device-id     设备标识，用于区分多台设备，默认 VF2-01
  --upload-url    服务器上传地址，默认 http://your-server-ip:5000/upload
  --work-sec      每次监控周期时长（秒），默认 20
  --record-sec    检测到人后录像时长（秒），默认 10
  --save-dir      本地存储目录，默认 ./data
  --sckey         Server酱 SCKEY
  --no-push       禁用微信推送
  --detect-mode   0 = 仅定时抓拍；1 = 抓拍 + 运动检测（默认）
```

---

## 预期效果

当有人经过摄像头视野时：

1. LED 和蜂鸣器同步闪烁/鸣响 3 次（约 1.5 秒，后台执行）
2. 事件图片保存至 `data/snapshots/`
3. 图片上传到服务器 `uploads/` 目录
4. 手机微信收到报警通知，附带可点击的图片链接
5. 录制 10 秒事件视频保存至 `data/videos/`

---

## 改进说明

相比原设计方案（`面向户外环境的国产开发板低功耗定时监控与实时回传系统设计方案.docx`）的改动：

| 文件 | 改动点 | 原因 |
|------|--------|------|
| `push_notification.py` | 修正 Server酱 API 地址 | 原地址为占位符，推送请求无法送达 |
| `monitor_uploader.py` | 新增 `BUZZER_PIN` 配置及蜂鸣器控制方法 | 增加蜂鸣报警功能 |
| `monitor_uploader.py` | 新增 `alert()` 非阻塞报警方法 | LED 闪烁与蜂鸣同步，后台线程执行不阻塞主监控循环 |
| `monitor_uploader.py` | 修正 LED 触发时序 | 原代码在录像结束后才亮灯，改为检测触发时立即报警 |
| `monitor_uploader.py` | `upload_and_push` 增加 `count` 参数 | 原 `threshold` 硬编码为 `1`，改为传入实际检测数量 |
| `monitor_uploader.py` | 移除 `cv2.imshow` 调用 | 无显示器的开发板运行时直接崩溃退出 |
5. 录制 10 秒事件视频保存至 `data/videos/`
