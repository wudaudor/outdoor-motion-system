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

# 导入自定义模块
from motion_detection import MotionDetector, PersonDetector, measure_sharpness
from push_notification import ServerChanPusher


# ============ 配置参数 ============

class Config:
    """配置类"""
    # 摄像头参数
    CAMERA_INDEX = 4
    CAMERA_CANDIDATES = [4, 5, 8, 0, 1, 2, 3, 6, 7]
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720

    # GPIO 参数
    LED_PIN = 36     # GPIO36 对应物理引脚 36
    BUZZER_PIN = 38  # GPIO38 对应物理引脚 38（有源蜂鸣器）

    # 检测参数
    ROI = None  # 检测区域 (x, y, w, h)，None 表示全画面检测，避免人从边缘经过时漏检
    AREA_THRESHOLD = 1200  # 最小检测面积
    DARK_THRESHOLD = 55  # 低照度阈值
    PERSON_DETECT_ENABLE = True
    PERSON_MIN_WEIGHT = 0.55
    PERSON_CONFIRM_FRAMES = 2   # 连续 N 帧检测到人才触发报警，防止静物误检后连发
    CAMERA_SHAKE_RATIO = 0.85   # 运动面积占比超过此值才判定为镜头抖动，避免近距离人员被误判为抖动
    BLUR_THRESHOLD = 80         # Laplacian 方差低于此值判定为模糊帧，跳过
    SHAKE_COOLDOWN_FRAMES = 20  # 镜头抖动后冷却帧数（约 2 秒），期间重建背景
    ALERT_COOLDOWN_SECONDS = 60  # 报警冷却时间，避免同一目标或误检连续刷屏

    # 检测模式
    # 1: 事件触发抓拍 + 运动检测
    DETECT_MODE = 1
    SCHEDULED_SNAPSHOT_ENABLE = False

    # 定时任务参数
    WORK_SECONDS = 20  # 单次任务运行时长
    RECORD_SECONDS = 0  # 录像时长；0 表示只保存报警抓拍，不录制视频以减少存储占用

    # 上传参数
    UPLOAD_URL = "http://your-server-ip:5000/upload"
    SERVER_BASE_URL = "http://your-server-ip:5000"

    # 微信推送
    PUSH_ENABLE = True
    TEST_PUSH_ON_START = False
    SCKEY = "your-sc-key-here"
    DEVICE_ID = "VF2-01"

    # 存储路径
    SAVE_DIR = Path("./data")
    SNAPSHOT_DIR = SAVE_DIR / "snapshots"
    VIDEO_DIR = SAVE_DIR / "videos"
    LOG_DIR = SAVE_DIR / "logs"


# ============ GPIO 控制 ============

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

    def led_on(self):
        GPIO.output(self.led_pin, GPIO.HIGH)

    def led_off(self):
        GPIO.output(self.led_pin, GPIO.LOW)

    def led_blink(self, times: int = 3, interval: float = 0.3):
        """LED 闪烁"""
        for _ in range(times):
            self.led_on()
            time.sleep(interval)
            self.led_off()
            time.sleep(interval)

    def buzzer_on(self):
        GPIO.output(self.buzzer_pin, GPIO.HIGH)

    def buzzer_off(self):
        GPIO.output(self.buzzer_pin, GPIO.LOW)

    def alert(self, times: int = 3, on_sec: float = 0.3, off_sec: float = 0.2):
        """LED 闪烁 + 蜂鸣同步触发，后台线程运行不阻塞主循环"""
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


# ============ 主监控类 ============

class OutdoorMonitor:
    """户外监控器"""

    def __init__(self, config: Config):
        self.config = config
        self.running = False

        # 初始化目录
        config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.gpio = GPIOController(config.LED_PIN, config.BUZZER_PIN)
        self.motion_detector = MotionDetector(
            roi=config.ROI,
            area_threshold=config.AREA_THRESHOLD
        )
        self.person_detector = PersonDetector(
            roi=config.ROI,
            min_weight=config.PERSON_MIN_WEIGHT
        ) if config.PERSON_DETECT_ENABLE else None
        self.pusher = ServerChanPusher(config.SCKEY) if config.PUSH_ENABLE else None

        # 摄像头
        self.cap = None
        self._shake_cooldown = 0
        self._last_alert_at = 0.0

    def init_camera(self) -> bool:
        """初始化摄像头"""
        candidates = [self.config.CAMERA_INDEX]
        for idx in self.config.CAMERA_CANDIDATES:
            if idx not in candidates:
                candidates.append(idx)

        for idx in candidates:
            cap = cv2.VideoCapture(idx)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            time.sleep(0.8)

            if not cap.isOpened():
                cap.release()
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                continue

            self.cap = cap
            self.config.CAMERA_INDEX = idx
            print(f"摄像头初始化成功: /dev/video{idx}, 画面尺寸: {frame.shape[1]}x{frame.shape[0]}")
            return True

        print(f"错误: 无法打开摄像头，已尝试: {candidates}")
        return False

    def capture_snapshot(self, label: str = "snapshot") -> tuple:
        """抓拍一张图片"""
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
        """上传文件到服务器"""
        if not filepath.exists():
            print(f"文件不存在: {filepath}")
            return None

        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                data = {
                    'device_id': self.config.DEVICE_ID,
                    'kind': kind,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                response = requests.post(
                    self.config.UPLOAD_URL,
                    files=files,
                    data=data,
                    timeout=30
                )

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
        """
        上传文件并发送微信推送

        返回:
            图片的 URL 地址
        """
        # 先上传获取 URL
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

        # 发送微信推送
        if self.pusher and self.config.PUSH_ENABLE:
            self.pusher.send_motion_alert(
                device_id=self.config.DEVICE_ID,
                image_url=image_url,
                location="监控区域",
                threshold=count
            )
            print("微信推送已发送")

        return image_url

    def is_camera_shake(self, contours: list) -> bool:
        """运动区域过大时通常是镜头晃动、强光变化或整体画面变化。"""
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

        if ratio >= 0.65:
            frame_w = self.config.ROI[2] if self.config.ROI else self.config.FRAME_WIDTH
            frame_h = self.config.ROI[3] if self.config.ROI else self.config.FRAME_HEIGHT
            xs, ys, xe, ye = [], [], [], []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                xs.append(x)
                ys.append(y)
                xe.append(x + w)
                ye.append(y + h)
            if xs and ys:
                bbox_w = max(xe) - min(xs)
                bbox_h = max(ye) - min(ys)
                if bbox_w >= frame_w * 0.85 and bbox_h >= frame_h * 0.85:
                    print(f"忽略疑似整幅画面变化，运动面积占比: {ratio:.2f}")
                    return True
        return False

    def record_video(self, duration: int = 10) -> Path:
        """
        录制视频

        参数:
            duration: 录像时长（秒）

        返回:
            视频文件路径
        """
        if not self.cap or not self.cap.isOpened():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_event.mp4"
        filepath = self.config.VIDEO_DIR / filename

        # 获取视频编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 15.0

        out = cv2.VideoWriter(
            str(filepath),
            fourcc,
            fps,
            (self.config.FRAME_WIDTH, self.config.FRAME_HEIGHT)
        )

        print(f"开始录像: {filepath}")
        start_time = time.time()

        while time.time() - start_time < duration:
            ret, frame = self.cap.read()
            if not ret:
                break

            # 添加时间戳
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, ts, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            out.write(frame)

            # 显示录像状态
            elapsed = int(time.time() - start_time)
            print(f"\r录像中... {elapsed}/{duration}秒", end='', flush=True)

        out.release()
        print(f"\n录像完成: {filepath}")

        return filepath

    def run_monitoring_cycle(self):
        """执行一次监控周期"""
        print(f"\n{'='*50}")
        print(f"监控周期开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        # 1. 可选定时抓拍；默认关闭，避免无人时持续保存图片占用存储。
        if self.config.SCHEDULED_SNAPSHOT_ENABLE:
            print("Step 1: 定时抓拍...")
            ret, snapshot_path = self.capture_snapshot("scheduled")

            if ret and snapshot_path:
                self.upload_file(snapshot_path, "snapshot")
        else:
            print("Step 1: 事件触发模式，跳过定时抓拍")

        # 2. 进行运动检测
        if self.config.DETECT_MODE == 1:
            print("Step 2: 运动检测中...")

            motion_detected = False
            detection_count = 0
            confirm_streak = 0  # 连续检测到人的帧计数
            detect_start = time.time()

            # 持续检测直到超时
            while time.time() - detect_start < self.config.WORK_SECONDS:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                # 镜头抖动冷却期：跳过检测，等待背景模型重建稳定
                if self._shake_cooldown > 0:
                    self._shake_cooldown -= 1
                    time.sleep(0.1)
                    continue

                # 低照度时跳过检测，避免夜间噪点误触发
                if cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean() < self.config.DARK_THRESHOLD:
                    confirm_streak = 0
                    time.sleep(0.1)
                    continue

                # 画面模糊（相机晃动或目标快速移动）时跳过，避免误触发
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
                        person_detected, person_boxes = self.person_detector.detect(frame, contours)

                    if not person_detected:
                        print("检测到运动，但未识别到人，忽略本次触发")
                        confirm_streak = 0
                        time.sleep(0.1)
                        continue

                    confirm_streak += 1
                    if confirm_streak < self.config.PERSON_CONFIRM_FRAMES:
                        time.sleep(0.1)
                        continue

                    now = time.time()
                    if now - self._last_alert_at < self.config.ALERT_COOLDOWN_SECONDS:
                        remaining = int(self.config.ALERT_COOLDOWN_SECONDS - (now - self._last_alert_at))
                        print(f"人员目标仍在报警冷却期，剩余 {remaining} 秒，跳过重复推送")
                        confirm_streak = 0
                        time.sleep(0.1)
                        continue

                    detection_count += 1
                    confirm_streak = 0
                    self._last_alert_at = now
                    print(f"检测到人员目标 #{detection_count}，人形框数量: {len(person_boxes)}")

                    if not motion_detected:
                        motion_detected = True

                        # 连续抓取数帧，选清晰度最高的作为推送图
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

                        # LED 闪烁 + 蜂鸣报警（后台线程，不阻塞）
                        self.gpio.alert(times=3)

                        # 上传并推送微信
                        self.upload_and_push(event_path, "event", count=detection_count)

                        # 可选录像；默认关闭以减少存储占用。
                        if self.config.RECORD_SECONDS > 0:
                            self.record_video(self.config.RECORD_SECONDS)

                else:
                    confirm_streak = 0

                # 无界面运行时跳过显示，按 q 退出（仅有桌面时有效）
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                time.sleep(0.1)

            # 任务结束，关闭 LED
            self.gpio.led_off()

            if motion_detected:
                print(f"✓ 本周期检测到 {detection_count} 次运动目标")
            else:
                print("✓ 本周期无运动目标")

        print(f"监控周期结束")

    def start(self):
        """启动监控"""
        print("户外监控程序启动...")
        print(f"设备ID: {self.config.DEVICE_ID}")
        print(f"上传地址: {self.config.UPLOAD_URL}")
        print(f"推送功能: {'开启' if self.config.PUSH_ENABLE else '关闭'}")
        print(f"检测模式: {'事件触发抓拍+运动检测' if self.config.DETECT_MODE == 1 else '仅手动/定时抓拍'}")

        # 测试摄像头
        if not self.init_camera():
            print("摄像头初始化失败，程序退出")
            sys.exit(1)

        # 测试微信推送
        if self.pusher and self.config.PUSH_ENABLE and self.config.TEST_PUSH_ON_START:
            print("测试微信推送...")
            if self.pusher.send_test():
                print("微信推送测试成功")
            else:
                print("微信推送测试失败，请检查 SCKEY")

        self.running = True

        try:
            while self.running:
                self.run_monitoring_cycle()
        except KeyboardInterrupt:
            print("\n用户中断")
        finally:
            self.stop()

    def stop(self):
        """停止监控"""
        print("正在停止监控...")
        self.running = False

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()
        self.gpio.cleanup()

        print("监控已停止")


# ============ 命令行入口 ============

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="户外监控程序 - VisionFive 2")

    parser.add_argument('--camera-index', type=int, default=Config.CAMERA_INDEX,
                        help=f'摄像头索引 (默认: {Config.CAMERA_INDEX})')
    parser.add_argument('--device-id', type=str, default=Config.DEVICE_ID,
                        help=f'设备ID (默认: {Config.DEVICE_ID})')
    parser.add_argument('--upload-url', type=str, default=Config.UPLOAD_URL,
                        help=f'上传地址 (默认: {Config.UPLOAD_URL})')
    parser.add_argument('--work-sec', type=int, default=Config.WORK_SECONDS,
                        help=f'工作时长秒数 (默认: {Config.WORK_SECONDS})')
    parser.add_argument('--record-sec', type=int, default=Config.RECORD_SECONDS,
                        help=f'录像时长秒数 (默认: {Config.RECORD_SECONDS})')
    parser.add_argument('--save-dir', type=str, default=str(Config.SAVE_DIR),
                        help=f'存储目录 (默认: {Config.SAVE_DIR})')
    parser.add_argument('--sckey', type=str, default=os.environ.get("SCKEY", Config.SCKEY),
                        help='Server酱 SCKEY')
    parser.add_argument('--no-push', action='store_true',
                        help='禁用微信推送')
    parser.add_argument('--test-push-on-start', action='store_true',
                        help='启动时发送一条微信测试消息')
    parser.add_argument('--detect-mode', type=int, choices=[0, 1], default=Config.DETECT_MODE,
                        help='检测模式: 0=仅抓拍, 1=事件触发抓拍+运动检测')
    parser.add_argument('--scheduled-snapshot', action='store_true',
                        help='启用无人时的周期性定时抓拍（默认关闭）')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 更新配置
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
    Config.SCHEDULED_SNAPSHOT_ENABLE = args.scheduled_snapshot

    # 创建并启动监控器
    monitor = OutdoorMonitor(Config)
    monitor.start()
