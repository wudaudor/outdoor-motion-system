#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
户外监控主程序 - VisionFive 2 版本
功能：定时抓拍 + 运动检测 + 微信推送 + 文件上传
"""

import cv2
import time
import argparse
import requests
import os
import sys
from pathlib import Path
from datetime import datetime
from threading import Thread
from typing import Any, Dict, Optional
from urllib.parse import urljoin
import VisionFive.gpio as GPIO

from motion_detection import MotionDetector, PersonDetector, measure_sharpness
from push_notification import ServerChanPusher


class Config:
    """配置类"""
    CAMERA_INDEX = 4
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720

    LED_PIN = 36
    BUZZER_PIN = 38

    ROI = (320, 180, 640, 360)
    AREA_THRESHOLD = 1200
    DARK_THRESHOLD = 55
    PERSON_DETECT_ENABLE = True
    PERSON_MIN_WEIGHT = 0.65
    PERSON_CONFIRM_FRAMES = 2
    CAMERA_SHAKE_RATIO = 0.45
    BLUR_THRESHOLD = 80
    SHAKE_COOLDOWN_FRAMES = 20

    DETECT_MODE = 1

    WORK_SECONDS = 20
    RECORD_SECONDS = 10

    UPLOAD_URL = "http://your-server-ip:5000/upload"
    SERVER_BASE_URL = "http://your-server-ip:5000"

    PUSH_ENABLE = True
    TEST_PUSH_ON_START = False
    SCKEY = "your-sc-key-here"
    DEVICE_ID = "VF2-01"

    SAVE_DIR = Path("./data")
    SNAPSHOT_DIR = SAVE_DIR / "snapshots"
    VIDEO_DIR = SAVE_DIR / "videos"
    LOG_DIR = SAVE_DIR / "logs"


class GPIOController:
    """GPIO 控制器"""
    def __init__(self, led_pin: int = Config.LED_PIN, buzzer_pin: int = Config.BUZZER_PIN):
        self.led_pin = led_pin
        self.buzzer_pin = buzzer_pin
        self._alert_thread = None
        self._init_gpio()

    def _init_gpio(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.led_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.buzzer_pin, GPIO.OUT, initial=GPIO.LOW)
        print(f"GPIO 初始化完成，LED 引脚: {self.led_pin}，蜂鸣器引脚: {self.buzzer_pin}")

    def led_on(self): GPIO.output(self.led_pin, GPIO.HIGH)
    def led_off(self): GPIO.output(self.led_pin, GPIO.LOW)

    def led_blink(self, times: int = 3, interval: float = 0.3):
        for _ in range(times):
            self.led_on(); time.sleep(interval)
            self.led_off(); time.sleep(interval)

    def buzzer_on(self): GPIO.output(self.buzzer_pin, GPIO.HIGH)
    def buzzer_off(self): GPIO.output(self.buzzer_pin, GPIO.LOW)

    def alert(self, times: int = 3, on_sec: float = 0.3, off_sec: float = 0.2):
        def _run():
            for _ in range(times):
                GPIO.output(self.led_pin, GPIO.HIGH)
                GPIO.output(self.buzzer_pin, GPIO.HIGH)
                time.sleep(on_sec)
                GPIO.output(self.led_pin, GPIO.LOW)
                GPIO.output(self.buzzer_pin, GPIO.LOW)
                time.sleep(off_sec)
        if self._alert_thread and self._alert_thread.is_alive():
            return
        self._alert_thread = Thread(target=_run, daemon=True)
        self._alert_thread.start()

    def cleanup(self):
        if self._alert_thread and self._alert_thread.is_alive():
            self._alert_thread.join(timeout=2)
        GPIO.cleanup()


class OutdoorMonitor:
    """户外监控器"""
    def __init__(self, config: Config):
        self.config = config
        self.running = False

        config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)

        self.gpio = GPIOController(config.LED_PIN, config.BUZZER_PIN)
        self.motion_detector = MotionDetector(roi=config.ROI, area_threshold=config.AREA_THRESHOLD)
        self.person_detector = PersonDetector(
            roi=config.ROI, min_weight=config.PERSON_MIN_WEIGHT
        ) if config.PERSON_DETECT_ENABLE else None
        self.pusher = ServerChanPusher(config.SCKEY) if config.PUSH_ENABLE else None

        self.cap = None
        self._shake_cooldown = 0

    def init_camera(self) -> bool:
        self.cap = cv2.VideoCapture(self.config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        time.sleep(2)
        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 /dev/video{self.config.CAMERA_INDEX}")
            return False
        print(f"摄像头初始化成功: {self.config.FRAME_WIDTH}x{self.config.FRAME_HEIGHT}")
        return True

    def capture_snapshot(self, label: str = "snapshot") -> tuple:
        if not self.cap or not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{label}.jpg"
        filepath = self.config.SNAPSHOT_DIR / filename
        cv2.imwrite(str(filepath), frame)
        print(f"抓拍保存: {filepath}")
        return True, filepath

    def upload_file(self, filepath: Path, kind: str = "image") -> Optional[Dict[str, Any]]:
        if not filepath.exists():
            print(f"文件不存在: {filepath}")
            return None
        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                data = {'device_id': self.config.DEVICE_ID, 'kind': kind,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                response = requests.post(self.config.UPLOAD_URL, files=files, data=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                print(f"上传成功: {result.get('path', '')}")
                return result
            else:
                print(f"上传失败: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"上传异常: {e}")
            return None

    def upload_and_push(self, filepath: Path, kind: str = "event", count: int = 1) -> str:
        result = self.upload_file(filepath, kind)
        if result:
            image_url = result.get("url")
            if image_url:
                image_url = urljoin(self.config.SERVER_BASE_URL.rstrip("/") + "/", image_url.lstrip("/"))
            else:
                filename = result.get("filename", filepath.name)
                image_url = f"{self.config.SERVER_BASE_URL}/uploads/{filename}"
        else:
            image_url = None
        if self.pusher and self.config.PUSH_ENABLE:
            self.pusher.send_motion_alert(device_id=self.config.DEVICE_ID, image_url=image_url,
                                          location="监控区域", threshold=count)
            print("微信推送已发送")
        return image_url

    def is_camera_shake(self, contours: list) -> bool:
        if not contours:
            return False
        motion_area = sum(cv2.contourArea(cnt) for cnt in contours)
        if self.config.ROI:
            _, _, roi_w, roi_h = self.config.ROI
            frame_area = roi_w * roi_h
        else:
            frame_area = self.config.FRAME_WIDTH * self.config.FRAME_HEIGHT
        ratio = motion_area / frame_area if frame_area else 0
        if ratio >= self.config.CAMERA_SHAKE_RATIO:
            print(f"忽略整体画面晃动/光照变化，运动面积占比: {ratio:.2f}")
            return True
        return False

    def record_video(self, duration: int = 10) -> Path:
        if not self.cap or not self.cap.isOpened():
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_event.mp4"
        filepath = self.config.VIDEO_DIR / filename
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 15.0
        out = cv2.VideoWriter(str(filepath), fourcc, fps,
                              (self.config.FRAME_WIDTH, self.config.FRAME_HEIGHT))
        print(f"开始录像: {filepath}")
        start_time = time.time()
        while time.time() - start_time < duration:
            ret, frame = self.cap.read()
            if not ret:
                break
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, ts, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            out.write(frame)
            elapsed = int(time.time() - start_time)
            print(f"\r录像中... {elapsed}/{duration}秒", end='', flush=True)
        out.release()
        print(f"\n录像完成: {filepath}")
        return filepath

    def run_monitoring_cycle(self):
        print(f"\n{'='*50}")
        print(f"监控周期开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        print("Step 1: 定时抓拍...")
        ret, snapshot_path = self.capture_snapshot("scheduled")
        if ret and snapshot_path:
            self.upload_file(snapshot_path, "snapshot")

        if self.config.DETECT_MODE == 1:
            print("Step 2: 运动检测中...")
            motion_detected = False
            detection_count = 0
            confirm_streak = 0
            detect_start = time.time()

            while time.time() - detect_start < self.config.WORK_SECONDS:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                if self._shake_cooldown > 0:
                    self._shake_cooldown -= 1
                    time.sleep(0.1)
                    continue

                if cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean() < self.config.DARK_THRESHOLD:
                    confirm_streak = 0
                    time.sleep(0.1)
                    continue

                if measure_sharpness(frame) < self.config.BLUR_THRESHOLD:
                    confirm_streak = 0
                    time.sleep(0.1)
                    continue

                is_motion, mask, contours = self.motion_detector.detect(frame)

                if is_motion:
                    if self.is_camera_shake(contours):
                        confirm_streak = 0
                        self._shake_cooldown = self.config.SHAKE_COOLDOWN_FRAMES
                        self.motion_detector.reset_background()
                        print(f"检测到镜头抖动，重置背景模型，冷却 {self.config.SHAKE_COOLDOWN_FRAMES} 帧")
                        time.sleep(0.1)
                        continue

                    person_detected = True
                    person_boxes = []
                    if self.person_detector:
                        person_detected, person_boxes = self.person_detector.detect(frame)

                    if not person_detected:
                        print("检测到运动，但未识别到人，忽略本次触发")
                        confirm_streak = 0
                        time.sleep(0.1)
                        continue

                    confirm_streak += 1
                    if confirm_streak < self.config.PERSON_CONFIRM_FRAMES:
                        time.sleep(0.1)
                        continue

                    detection_count += 1
                    confirm_streak = 0
                    print(f"检测到人员目标 #{detection_count}，人形框数量: {len(person_boxes)}")

                    if not motion_detected:
                        motion_detected = True

                        best_frame = frame
                        best_sharpness = measure_sharpness(frame)
                        for _ in range(4):
                            ret_b, f = self.cap.read()
                            if ret_b:
                                s = measure_sharpness(f)
                                if s > best_sharpness:
                                    best_sharpness = s
                                    best_frame = f

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        event_path = self.config.SNAPSHOT_DIR / f"{timestamp}_event.jpg"
                        for x, y, w, h, weight in person_boxes:
                            cv2.rectangle(best_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(best_frame, f"person {weight:.2f}", (x, max(20, y-8)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.imwrite(str(event_path), best_frame)

                        self.gpio.alert(times=3)
                        self.upload_and_push(event_path, "event", count=detection_count)
                        self.record_video(self.config.RECORD_SECONDS)
                else:
                    confirm_streak = 0

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                time.sleep(0.1)

            self.gpio.led_off()

            if motion_detected:
                print(f"✓ 本周期检测到 {detection_count} 次运动目标")
            else:
                print("✓ 本周期无运动目标")

        print(f"监控周期结束")

    def start(self):
        print("户外监控程序启动...")
        print(f"设备ID: {self.config.DEVICE_ID}")
        print(f"上传地址: {self.config.UPLOAD_URL}")
        print(f"推送功能: {'开启' if self.config.PUSH_ENABLE else '关闭'}")
        print(f"检测模式: {'定时+运动检测' if self.config.DETECT_MODE == 1 else '仅定时抓拍'}")

        if not self.init_camera():
            print("摄像头初始化失败，程序退出")
            sys.exit(1)

        if self.pusher and self.config.PUSH_ENABLE and self.config.TEST_PUSH_ON_START:
            print("测试微信推送...")
            if self.pusher.send_test():
                print("微信推送测试成功")
            else:
                print("微信推送测试失败，请检查 SCKEY")

        self.running = True
        try:
            self.run_monitoring_cycle()
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            self.stop()

    def stop(self):
        print("正在停止监控...")
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.gpio.cleanup()
        print("监控已停止")


def parse_args():
    parser = argparse.ArgumentParser(description="户外监控程序 - VisionFive 2")
    parser.add_argument('--camera-index', type=int, default=Config.CAMERA_INDEX)
    parser.add_argument('--device-id', type=str, default=Config.DEVICE_ID)
    parser.add_argument('--upload-url', type=str, default=Config.UPLOAD_URL)
    parser.add_argument('--work-sec', type=int, default=Config.WORK_SECONDS)
    parser.add_argument('--record-sec', type=int, default=Config.RECORD_SECONDS)
    parser.add_argument('--save-dir', type=str, default=str(Config.SAVE_DIR))
    parser.add_argument('--sckey', type=str, default=os.environ.get("SCKEY", Config.SCKEY))
    parser.add_argument('--no-push', action='store_true', help='禁用微信推送')
    parser.add_argument('--test-push-on-start', action='store_true', help='启动时发送微信测试消息')
    parser.add_argument('--detect-mode', type=int, choices=[0, 1], default=Config.DETECT_MODE)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    Config.CAMERA_INDEX = args.camera_index
    Config.DEVICE_ID = args.device_id
    Config.UPLOAD_URL = args.upload_url
    Config.SERVER_BASE_URL = args.upload_url.rsplit("/upload", 1)[0].rstrip("/")
    Config.WORK_SECONDS = args.work_sec
    Config.RECORD_SECONDS = args.record_sec
    Config.SAVE_DIR = Path(args.save_dir)
    Config.SNAPSHOT_DIR = Config.SAVE_DIR / "snapshots"
    Config.VIDEO_DIR = Config.SAVE_DIR / "videos"
    Config.LOG_DIR = Config.SAVE_DIR / "logs"
    Config.SCKEY = args.sckey
    Config.PUSH_ENABLE = not args.no_push and args.sckey != "your-sc-key-here"
    Config.TEST_PUSH_ON_START = args.test_push_on_start
    Config.DETECT_MODE = args.detect_mode

    monitor = OutdoorMonitor(Config)
    monitor.start()
