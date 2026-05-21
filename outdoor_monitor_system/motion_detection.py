# -*- coding: utf-8 -*-
"""
运动检测模块
使用背景建模 + 帧差法检测运动目标
"""

import cv2
import numpy as np
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
        detect_shadows: bool = True,
        shadow_threshold: int = 200,
        morph_kernel_size: int = 5,
        morph_kernel_shape: str = "ellipse"
    ):
        self.roi = roi
        self.area_threshold = area_threshold
        self.history = history
        self.var_threshold = var_threshold
        self.detect_shadows = detect_shadows
        self.shadow_threshold = shadow_threshold
        self.morph_kernel_size = morph_kernel_size
        self.morph_kernel_shape = morph_kernel_shape

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )
        self.first_frame = None

    def detect(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, list]:
        if self.roi is not None:
            x, y, w, h = self.roi
            roi_frame = frame[y:y+h, x:x+w]
        else:
            roi_frame = frame
            x, y = 0, 0

        fg_mask = self.bg_subtractor.apply(roi_frame)

        if self.detect_shadows:
            fg_mask = cv2.threshold(fg_mask, self.shadow_threshold, 255, cv2.THRESH_BINARY)[1]

        shape = {"ellipse": cv2.MORPH_ELLIPSE, "rect": cv2.MORPH_RECT, "cross": cv2.MORPH_CROSS}
        kernel = cv2.getStructuringElement(
            shape.get(self.morph_kernel_shape, cv2.MORPH_ELLIPSE),
            (self.morph_kernel_size, self.morph_kernel_size)
        )
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = [
            cnt for cnt in contours
            if cv2.contourArea(cnt) >= self.area_threshold
        ]

        valid_contours_shifted = [
            cnt if self.roi is None
            else [pt + np.array([x, y]) for pt in cnt]
            for cnt in valid_contours
        ]

        is_motion = len(valid_contours) > 0
        return is_motion, fg_mask, valid_contours_shifted

    def detect_with_frame_diff(
        self, frame: np.ndarray, prev_frame: Optional[np.ndarray] = None
    ) -> Tuple[bool, np.ndarray, np.ndarray]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            self.first_frame = gray
            return False, np.zeros_like(gray), np.zeros_like(gray)

        if self.first_frame is None:
            self.first_frame = gray

        frame_delta = cv2.absdiff(self.first_frame, gray)
        if prev_frame is not None:
            frame_delta = cv2.absdiff(prev_frame, gray)

        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = [
            cnt for cnt in contours
            if cv2.contourArea(cnt) >= self.area_threshold
        ]

        is_motion = len(valid_contours) > 0
        return is_motion, frame_delta, thresh

    def draw_detection(
        self, frame: np.ndarray, mask: np.ndarray, contours: list,
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        result = frame.copy()
        if self.roi is not None:
            x, y, w, h = self.roi
            cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(result, (x, y), (x+w, y+h), color, 2)
        status = "MOTION DETECTED!" if contours else "No Motion"
        status_color = (0, 0, 255) if contours else (0, 255, 0)
        cv2.putText(result, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        return result

    def reset_background(self):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows
        )
        self.first_frame = None


class PersonDetector:
    """基于 OpenCV HOG 的行人检测器"""

    def __init__(
        self,
        roi: Optional[Tuple[int, int, int, int]] = None,
        min_weight: float = 0.65,
        max_width: int = 640,
        hit_threshold: float = 0.0,
        win_stride: Tuple[int, int] = (8, 8),
        padding: Tuple[int, int] = (16, 16),
        scale: float = 1.05,
        geom_min_height: int = 64,
        geom_min_aspect: float = 1.5,
        skin_h_low: int = 0,
        skin_h_high: int = 20,
        skin_s_low: int = 60,
        skin_s_high: int = 255,
        skin_v_low: int = 80,
        skin_v_high: int = 255,
        skin_min_pixels: int = 80,
        skin_min_ratio: float = 0.05,
        nms_overlap: float = 0.35
    ):
        self.roi = roi
        self.min_weight = min_weight
        self.max_width = max_width
        self.hit_threshold = hit_threshold
        self.win_stride = win_stride
        self.padding = padding
        self.scale = scale
        self.geom_min_height = geom_min_height
        self.geom_min_aspect = geom_min_aspect
        self.skin_h_low = skin_h_low
        self.skin_h_high = skin_h_high
        self.skin_s_low = skin_s_low
        self.skin_s_high = skin_s_high
        self.skin_v_low = skin_v_low
        self.skin_v_high = skin_v_high
        self.skin_min_pixels = skin_min_pixels
        self.skin_min_ratio = skin_min_ratio
        self.nms_overlap = nms_overlap

        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> Tuple[bool, list]:
        if self.roi is not None:
            x0, y0, w0, h0 = self.roi
            detect_frame = frame[y0:y0+h0, x0:x0+w0]
        else:
            x0, y0 = 0, 0
            detect_frame = frame

        if detect_frame.size == 0:
            return False, []

        scale_back = 1.0
        if detect_frame.shape[1] > self.max_width:
            scale_back = detect_frame.shape[1] / self.max_width
            new_height = int(detect_frame.shape[0] / scale_back)
            detect_frame = cv2.resize(detect_frame, (self.max_width, new_height))

        rects, weights = self.hog.detectMultiScale(
            detect_frame,
            hitThreshold=self.hit_threshold,
            winStride=self.win_stride,
            padding=self.padding,
            scale=self.scale
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
            if sh < self.geom_min_height or sw == 0 or sh / sw < self.geom_min_aspect:
                continue
            if not self._has_skin_tone(frame, (sx, sy, sw, sh)):
                continue
            boxes.append((sx, sy, sw, sh, weight))

        boxes = self._non_max_suppression(boxes)
        return len(boxes) > 0, boxes

    def _has_skin_tone(self, frame: np.ndarray, box: tuple) -> bool:
        x, y, w, h = box[:4]
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + w), min(fh, y + h)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv,
                           np.array([self.skin_h_low, self.skin_s_low, self.skin_v_low], dtype=np.uint8),
                           np.array([self.skin_h_high, self.skin_s_high, self.skin_v_high], dtype=np.uint8))
        skin_px = int(np.count_nonzero(mask))
        total_px = (x2 - x1) * (y2 - y1)
        return skin_px >= self.skin_min_pixels and (skin_px / total_px) >= self.skin_min_ratio

    def _non_max_suppression(self, boxes: list) -> list:
        if not boxes:
            return []
        boxes = sorted(boxes, key=lambda box: box[4], reverse=True)
        kept = []
        for box in boxes:
            if all(PersonDetector._iou(box, kept_box) < self.nms_overlap
                   for kept_box in kept):
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


if __name__ == "__main__":
    import sys
    cam_index = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    print(f"使用摄像头 /dev/video{cam_index}")
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    detector = MotionDetector(roi=(320, 180, 640, 360), area_threshold=1200, history=500)
    print("按 'r' 重置背景模型，按 'q' 退出")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("摄像头读取失败")
            break
        is_motion, mask, contours = detector.detect(frame)
        result = detector.draw_detection(frame, mask, contours)
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
