# -*- coding: utf-8 -*-
"""
运动检测模块
使用背景建模 + 帧差法检测运动目标
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class MotionDetector:
    """运动检测器"""

    def __init__(
        self,
        roi: Optional[Tuple[int, int, int, int]] = None,
        area_threshold: int = 1200,
        history: int = 500,
        var_threshold: int = 25,
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
            else [pt + np.array([x, y]) for pt in cnt]
            for cnt in valid_contours
        ]

        is_motion = len(valid_contours) > 0

        return is_motion, fg_mask, valid_contours

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
