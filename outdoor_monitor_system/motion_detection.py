# -*- coding: utf-8 -*-
"""
运动检测模块
使用背景建模 + 帧差法检测运动目标
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple


def measure_sharpness(frame: np.ndarray) -> float:
    """Laplacian 方差衡量清晰度，值越高越清晰"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


class MotionDetector:
    """运动检测器"""

    def __init__(
        self,
        roi: Optional[Tuple[int, int, int, int]] = None,
        area_threshold: int = 1200,
        history: int = 500,
        var_threshold: int = 40,
        detect_shadows: bool = True
    ):
        """
        参数:
            roi: ROI 区域 (x, y, w, h)，None 表示全帧检测
            area_threshold: 最小连通区域面积阈值
            history: 背景建模帧数
            var_threshold: 方差阈值
            detect_shadows: 是否检测阴影
        """
        self.roi = roi
        self.area_threshold = area_threshold
        self.history = history
        self.var_threshold = var_threshold
        self.detect_shadows = detect_shadows

        # 创建背景分割器（MOG2 对光线变化更鲁棒）
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )

        self.first_frame = None

    def detect(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, list]:
        """
        检测运动目标

        参数:
            frame: 当前帧 (BGR 格式)

        返回:
            (is_motion, mask, contours): 是否检测到运动、检测掩码、轮廓列表
        """
        # 应用 ROI 掩码
        if self.roi is not None:
            x, y, w, h = self.roi
            roi_frame = frame[y:y+h, x:x+w]
        else:
            roi_frame = frame
            x, y = 0, 0

        # 背景建模获取前景掩码
        fg_mask = self.bg_subtractor.apply(roi_frame)

        # 去阴影（如果检测阴影开启，MOG2 会标记阴影为灰色）
        if self.detect_shadows:
            fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)[1]

        # 开运算：去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # 闭运算：填充空洞
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        # 找到连通区域
        contours, _ = cv2.findContours(
            fg_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # 过滤小区域
        valid_contours = [
            cnt for cnt in contours
            if cv2.contourArea(cnt) >= self.area_threshold
        ]

        # 转换轮廓坐标到原图坐标系
        valid_contours_shifted = [
            cnt if self.roi is None
            else cnt + np.array([[[x, y]]], dtype=cnt.dtype)
            for cnt in valid_contours
        ]

        is_motion = len(valid_contours) > 0

        return is_motion, fg_mask, valid_contours_shifted

    def detect_with_frame_diff(
        self,
        frame: np.ndarray,
        prev_frame: Optional[np.ndarray] = None
    ) -> Tuple[bool, np.ndarray, np.ndarray]:
        """
        使用帧差法检测运动（作为补充）

        参数:
            frame: 当前帧
            prev_frame: 上一帧，None 则自动使用第一帧

        返回:
            (is_motion, diff, thresh): 是否检测到运动、帧差图、二值化结果
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            self.first_frame = gray
            return False, np.zeros_like(gray), np.zeros_like(gray)

        if self.first_frame is None:
            self.first_frame = gray

        # 背景建模的帧差
        frame_delta = cv2.absdiff(self.first_frame, gray)

        # 当前帧与上一帧的差（更灵敏）
        if prev_frame is not None:
            frame_delta = cv2.absdiff(prev_frame, gray)

        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # 膨胀连接相邻区域
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = [
            cnt for cnt in contours
            if cv2.contourArea(cnt) >= self.area_threshold
        ]

        is_motion = len(valid_contours) > 0

        return is_motion, frame_delta, thresh

    def draw_detection(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        contours: list,
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        在帧上绘制检测结果

        参数:
            frame: 原帧
            mask: 检测掩码
            contours: 有效轮廓列表
            color: 绘制颜色 (B, G, R)

        返回:
            绘制了检测结果的帧
        """
        result = frame.copy()

        # 绘制 ROI 区域
        if self.roi is not None:
            x, y, w, h = self.roi
            cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # 绘制所有检测到的运动区域
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(result, (x, y), (x+w, y+h), color, 2)

        # 在左上角显示检测状态
        status = "MOTION DETECTED!" if contours else "No Motion"
        status_color = (0, 0, 255) if contours else (0, 255, 0)
        cv2.putText(
            result, status, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2
        )

        return result

    def reset_background(self):
        """重置背景模型"""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows
        )
        self.first_frame = None


class PersonDetector:
    """轻量人员检测器：DNN 人体模型优先，运动区域内 HOG+肤色作为低机位补充。"""

    def __init__(
        self,
        roi: Optional[Tuple[int, int, int, int]] = None,
        min_weight: float = 0.65,
        max_width: int = 640,
        dnn_confidence: float = 0.35,
        hog_fallback_min_weight: float = 0.45
    ):
        self.roi = roi
        self.min_weight = min_weight
        self.max_width = max_width
        self.dnn_confidence = dnn_confidence
        self.hog_fallback_min_weight = hog_fallback_min_weight
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.dnn_net = self._load_dnn_model()

    def detect(self, frame: np.ndarray, motion_contours: Optional[list] = None) -> Tuple[bool, list]:
        if self.roi is not None:
            x0, y0, w0, h0 = self.roi
            detect_frame = frame[y0:y0+h0, x0:x0+w0]
        else:
            x0, y0 = 0, 0
            detect_frame = frame

        if detect_frame.size == 0:
            return False, []

        boxes = []
        boxes.extend(self._detect_dnn(detect_frame, x0, y0))

        if motion_contours:
            boxes.extend(self._detect_dnn_on_motion_crops(frame, motion_contours))

        # 低机位/近距离时 DNN 可能只看到半身或边缘，HOG 只在运动区域内做补充。
        if not boxes and motion_contours:
            boxes.extend(self._detect_hog_on_motion_crops(frame, motion_contours))

        if not boxes and motion_contours:
            boxes.extend(self._detect_near_person_motion(frame, motion_contours))

        if motion_contours:
            boxes = [
                box for box in boxes
                if self._box_overlaps_motion(box, motion_contours)
            ]

        boxes = self._non_max_suppression(boxes)
        return len(boxes) > 0, boxes

    def _detect_dnn(self, detect_frame: np.ndarray, x0: int, y0: int) -> list:
        if self.dnn_net is None:
            return []

        h, w = detect_frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(detect_frame, (300, 300)),
            0.007843,
            (300, 300),
            127.5
        )
        self.dnn_net.setInput(blob)
        detections = self.dnn_net.forward()

        boxes = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            class_id = int(detections[0, 0, i, 1])
            if class_id != 15 or confidence < self.dnn_confidence:
                continue

            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            start_x, start_y, end_x, end_y = box.astype("int")
            start_x = max(0, min(w - 1, start_x))
            start_y = max(0, min(h - 1, start_y))
            end_x = max(start_x + 1, min(w, end_x))
            end_y = max(start_y + 1, min(h, end_y))
            bw = end_x - start_x
            bh = end_y - start_y

            if bw < 24 or bh < 48:
                continue
            box_ratio = (bw * bh) / max(1, w * h)
            aspect = bh / max(1, bw)
            if box_ratio > 0.72 or aspect < 0.40:
                continue

            boxes.append((
                int(start_x + x0),
                int(start_y + y0),
                int(bw),
                int(bh),
                confidence
            ))

        return boxes

    def _detect_dnn_on_motion_crops(self, frame: np.ndarray, motion_contours: list) -> list:
        if self.dnn_net is None:
            return []

        boxes = []
        frame_h, frame_w = frame.shape[:2]
        frame_area = max(1, frame_w * frame_h)

        for x, y, w, h in self._motion_regions(motion_contours, frame_w, frame_h):
            if (w * h) / frame_area > 0.65:
                continue

            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                continue

            for bx, by, bw, bh, score in self._detect_dnn(crop, x, y):
                boxes.append((bx, by, bw, bh, score))

        return boxes

    def _detect_hog(self, detect_frame: np.ndarray, frame: np.ndarray, x0: int, y0: int) -> list:
        scale_back = 1.0
        if detect_frame.shape[1] > self.max_width:
            scale_back = detect_frame.shape[1] / self.max_width
            new_height = int(detect_frame.shape[0] / scale_back)
            detect_frame = cv2.resize(detect_frame, (self.max_width, new_height))

        rects, weights = self.hog.detectMultiScale(
            detect_frame,
            hitThreshold=0,
            winStride=(8, 8),
            padding=(16, 16),
            scale=1.05
        )

        boxes = []
        for i, (x, y, w, h) in enumerate(rects):
            weight = float(weights[i]) if len(weights) > i else 1.0
            if weight < self.min_weight:
                continue
            sx = int(x * scale_back + x0)
            sy = int(y * scale_back + y0)
            sw = int(w * scale_back)
            sh = int(h * scale_back)
            # 人体框高/宽 ≈ 2~3，过矮/过宽的框通常是动物、车辆或树丛
            if sh < 56 or sw == 0 or sh / sw < 1.15:
                continue
            if PersonDetector._has_skin_tone(frame, (sx, sy, sw, sh)):
                weight += 0.15
            boxes.append((sx, sy, sw, sh, weight))

        return boxes

    def _detect_hog_on_motion_crops(self, frame: np.ndarray, motion_contours: list) -> list:
        boxes = []
        frame_h, frame_w = frame.shape[:2]
        frame_area = max(1, frame_w * frame_h)

        for x, y, w, h in self._motion_regions(motion_contours, frame_w, frame_h):
            region_ratio = (w * h) / frame_area
            if region_ratio < 0.025 or region_ratio > 0.45:
                continue

            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                continue

            for bx, by, bw, bh, score in self._detect_hog(crop, frame, x, y):
                if score < self.hog_fallback_min_weight:
                    continue
                aspect = bh / max(1, bw)
                box_ratio = (bw * bh) / frame_area
                if bh < max(80, frame_h * 0.16):
                    continue
                if aspect < 1.05:
                    continue
                if box_ratio < 0.025:
                    continue
                if not self._has_skin_tone(frame, (bx, by, bw, bh), min_ratio=0.035):
                    continue
                boxes.append((bx, by, bw, bh, min(0.89, score)))

        return boxes

    def _detect_near_person_motion(self, frame: np.ndarray, motion_contours: list) -> list:
        """低机位近距离人体兜底：只接受大块、靠画面上方进入的运动区域。"""
        frame_h, frame_w = frame.shape[:2]
        frame_area = max(1, frame_w * frame_h)
        boxes = []

        for x, y, w, h in self._motion_regions(motion_contours, frame_w, frame_h, expand=0.12):
            region_ratio = (w * h) / frame_area
            h_ratio = h / max(1, frame_h)
            w_ratio = w / max(1, frame_w)
            top_ratio = y / max(1, frame_h)
            aspect = h / max(1, w)

            if region_ratio < 0.12 or region_ratio > 0.88:
                continue
            if h_ratio < 0.45:
                continue
            if top_ratio > 0.28 and h_ratio < 0.68:
                continue
            if aspect < 0.58 and region_ratio < 0.28:
                continue
            if w_ratio > 0.95:
                continue

            skin_px, skin_ratio = self._skin_stats(frame, (x, y, w, h))
            skin_ok = skin_px >= 350 and skin_ratio >= 0.0035
            close_body_ok = top_ratio < 0.18 and h_ratio >= 0.65 and 0.18 <= w_ratio <= 0.88
            if not (skin_ok or close_body_ok):
                continue

            boxes.append((int(x), int(y), int(w), int(h), 0.52))

        return boxes

    @staticmethod
    def _motion_regions(motion_contours: list, frame_w: int, frame_h: int, expand: float = 0.30) -> list:
        frame_area = max(1, frame_w * frame_h)
        regions = []

        for contour in motion_contours:
            if contour is None:
                continue
            area = cv2.contourArea(contour)
            if area < frame_area * 0.002:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            pad_x = int(w * expand)
            pad_y = int(h * expand)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(frame_w, x + w + pad_x)
            y2 = min(frame_h, y + h + pad_y)
            rw = x2 - x1
            rh = y2 - y1
            if rw < 48 or rh < 64:
                continue
            regions.append((x1, y1, rw, rh))

        regions.sort(key=lambda r: r[2] * r[3], reverse=True)
        return regions[:4]

    @staticmethod
    def _box_overlaps_motion(box: tuple, motion_contours: list, min_overlap: float = 0.18) -> bool:
        bx, by, bw, bh = box[:4]
        box_area = max(1, bw * bh)

        for contour in motion_contours:
            if contour is None:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            x1 = max(bx, x)
            y1 = max(by, y)
            x2 = min(bx + bw, x + w)
            y2 = min(by + bh, y + h)
            inter = max(0, x2 - x1) * max(0, y2 - y1)

            if inter / box_area >= min_overlap:
                return True

        return False

    @staticmethod
    def _load_cascade(filename: str):
        candidates = []
        haar_dir = getattr(getattr(cv2, "data", None), "haarcascades", "")
        if haar_dir:
            candidates.append(Path(haar_dir) / filename)
        candidates.extend([
            Path("/usr/share/opencv4/haarcascades") / filename,
            Path("/usr/local/share/opencv4/haarcascades") / filename,
        ])

        for path in candidates:
            if path.exists():
                cascade = cv2.CascadeClassifier(str(path))
                if not cascade.empty():
                    return cascade
        return None

    @staticmethod
    def _load_dnn_model():
        base_dir = Path(__file__).resolve().parent / "models"
        prototxt = base_dir / "MobileNetSSD_deploy.prototxt"
        weights = base_dir / "MobileNetSSD_deploy.caffemodel"

        if not prototxt.exists() or not weights.exists():
            return None

        try:
            return cv2.dnn.readNetFromCaffe(str(prototxt), str(weights))
        except Exception as exc:
            print(f"MobileNet-SSD 模型加载失败，回退到 HOG/人脸检测: {exc}")
            return None

    @staticmethod
    def _has_skin_tone(frame: np.ndarray, box: tuple, min_ratio: float = 0.05) -> bool:
        skin_px, ratio = PersonDetector._skin_stats(frame, box)
        return skin_px >= 80 and ratio >= min_ratio

    @staticmethod
    def _skin_stats(frame: np.ndarray, box: tuple) -> tuple:
        x, y, w, h = box[:4]
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + w), min(fh, y + h)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return 0, 0.0
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # 真实肤色 S≥60（纸箱/米色墙面饱和度通常 <40，此阈值可区分）
        mask = cv2.inRange(hsv,
                           np.array([0, 60, 80], dtype=np.uint8),
                           np.array([20, 255, 255], dtype=np.uint8))
        skin_px = int(np.count_nonzero(mask))
        total_px = (x2 - x1) * (y2 - y1)
        return skin_px, (skin_px / total_px) if total_px else 0.0

    @staticmethod
    def _non_max_suppression(boxes: list, overlap_threshold: float = 0.35) -> list:
        if not boxes:
            return []

        boxes = sorted(boxes, key=lambda box: box[4], reverse=True)
        kept = []
        for box in boxes:
            if all(PersonDetector._iou(box, kept_box) < overlap_threshold for kept_box in kept):
                kept.append(box)
        return kept

    @staticmethod
    def _iou(a: tuple, b: tuple) -> float:
        ax, ay, aw, ah, _ = a
        bx, by, bw, bh, _ = b
        x1 = max(ax, bx)
        y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw)
        y2 = min(ay + ah, by + bh)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = aw * ah + bw * bh - inter
        return inter / union if union else 0.0


# ============ 测试代码 ============

if __name__ == "__main__":
    import sys

    # 从命令行参数获取摄像头索引
    cam_index = int(sys.argv[1]) if len(sys.argv) > 1 else 4

    print(f"使用摄像头 /dev/video{cam_index}")

    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # 创建检测器，检测画面中心区域
    detector = MotionDetector(
        roi=(320, 180, 640, 360),  # 中心区域
        area_threshold=1200,
        history=500
    )

    print("按 'r' 重置背景模型，按 'q' 退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("摄像头读取失败")
            break

        is_motion, mask, contours = detector.detect(frame)

        # 绘制结果
        result = detector.draw_detection(frame, mask, contours)

        # 显示
        cv2.imshow("Original", frame)
        cv2.imshow("Motion Mask", mask)
        cv2.imshow("Detection", result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            detector.reset_background()
            print("背景模型已重置")

    cap.release()
    cv2.destroyAllWindows()
