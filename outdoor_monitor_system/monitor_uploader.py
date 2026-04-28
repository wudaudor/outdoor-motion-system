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
import VisionFive.gpio as GPIO

# 导入自定义模块
from motion_detection import MotionDetector
from push_notification import ServerChanPusher


# ============ 配置参数 ============

class Config:
    """配置类"""
    # 摄像头参数
    CAMERA_INDEX = 4
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720

    # GPIO 参数
    LED_PIN = 36  # GPIO36 对应物理引脚 36

    # 检测参数
    ROI = (320, 180, 640, 360)  # 检测区域 (x, y, w, h)
    AREA_THRESHOLD = 1200  # 最小检测面积
    DARK_THRESHOLD = 55  # 低照度阈值

    # 检测模式
    # 0: 仅定时抓拍
    # 1: 定时抓拍 + 运动检测
    DETECT_MODE = 1

    # 定时任务参数
    WORK_SECONDS = 20  # 单次任务运行时长
    RECORD_SECONDS = 10  # 录像时长

    # 上传参数
    UPLOAD_URL = "http://your-server-ip:5000/upload"
    SERVER_BASE_URL = "http://your-server-ip:5000"

    # 微信推送
    PUSH_ENABLE = True
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

    def __init__(self, led_pin: int = Config.LED_PIN):
        self.led_pin = led_pin
        self._init_gpio()

    def _init_gpio(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.led_pin, GPIO.OUT, initial=GPIO.LOW)
        print(f"GPIO 初始化完成，LED 引脚: {self.led_pin}")

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

    def cleanup(self):
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
        self.gpio = GPIOController(config.LED_PIN)
        self.motion_detector = MotionDetector(
            roi=config.ROI,
            area_threshold=config.AREA_THRESHOLD
        )
        self.pusher = ServerChanPusher(config.SCKEY) if config.PUSH_ENABLE else None

        # 摄像头
        self.cap = None

    def init_camera(self) -> bool:
        """初始化摄像头"""
        self.cap = cv2.VideoCapture(self.config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)

        # 等待摄像头稳定
        time.sleep(2)

        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 /dev/video{self.config.CAMERA_INDEX}")
            return False

        print(f"摄像头初始化成功: {self.config.FRAME_WIDTH}x{self.config.FRAME_HEIGHT}")
        return True

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

    def upload_file(self, filepath: Path, kind: str = "image") -> bool:
        """上传文件到服务器"""
        if not filepath.exists():
            print(f"文件不存在: {filepath}")
            return False

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
                return True
            else:
                print(f"上传失败: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"上传异常: {e}")
            return False

    def upload_and_push(self, filepath: Path, kind: str = "event") -> str:
        """
        上传文件并发送微信推送

        返回:
            图片的 URL 地址
        """
        # 先上传获取 URL
        if self.upload_file(filepath, kind):
            image_url = f"{self.config.SERVER_BASE_URL}/uploads/{filepath.name}"
        else:
            image_url = None

        # 发送微信推送
        if self.pusher and self.config.PUSH_ENABLE:
            self.pusher.send_motion_alert(
                device_id=self.config.DEVICE_ID,
                image_url=image_url,
                location="监控区域",
                threshold=1
            )
            print("微信推送已发送")

        return image_url

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

        # 1. 前 2 秒内抓拍一张定时图并上传
        print("Step 1: 定时抓拍...")
        ret, snapshot_path = self.capture_snapshot("scheduled")

        if ret and snapshot_path:
            self.upload_file(snapshot_path, "snapshot")

        # 2. 进行运动检测
        if self.config.DETECT_MODE == 1:
            print("Step 2: 运动检测中...")

            motion_detected = False
            detection_count = 0
            detect_start = time.time()

            # 持续检测直到超时
            while time.time() - detect_start < self.config.WORK_SECONDS:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                is_motion, mask, contours = self.motion_detector.detect(frame)

                if is_motion:
                    detection_count += 1
                    print(f"检测到运动目标 #{detection_count}")

                    # 第一次检测到时：
                    # 1. 保存事件图
                    # 2. 上传并推送微信
                    # 3. 开始录像
                    # 4. 点亮 LED
                    if not motion_detected:
                        motion_detected = True

                        # 保存事件图
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        event_path = self.config.SNAPSHOT_DIR / f"{timestamp}_event.jpg"
                        cv2.imwrite(str(event_path), frame)

                        # 上传并推送微信
                        self.upload_and_push(event_path, "event")

                        # 录像
                        self.record_video(self.config.RECORD_SECONDS)

                        # LED 亮起
                        self.gpio.led_on()

                # 显示检测画面（可注释掉以减少资源消耗）
                result = self.motion_detector.draw_detection(frame, mask, contours)
                cv2.imshow("Monitor", result)

                # 按 q 退出
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
        print(f"检测模式: {'定时+运动检测' if self.config.DETECT_MODE == 1 else '仅定时抓拍'}")

        # 测试摄像头
        if not self.init_camera():
            print("摄像头初始化失败，程序退出")
            sys.exit(1)

        # 测试微信推送
        if self.pusher and self.config.PUSH_ENABLE:
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
    parser.add_argument('--sckey', type=str, default=Config.SCKEY,
                        help='Server酱 SCKEY')
    parser.add_argument('--no-push', action='store_true',
                        help='禁用微信推送')
    parser.add_argument('--detect-mode', type=int, choices=[0, 1], default=Config.DETECT_MODE,
                        help='检测模式: 0=仅抓拍, 1=抓拍+运动检测')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 更新配置
    Config.CAMERA_INDEX = args.camera_index
    Config.DEVICE_ID = args.device_id
    Config.UPLOAD_URL = args.upload_url
    Config.WORK_SECONDS = args.work_sec
    Config.RECORD_SECONDS = args.record_sec
    Config.SAVE_DIR = Path(args.save_dir)
    Config.SCKEY = args.sckey
    Config.PUSH_ENABLE = not args.no_push and args.sckey != "your-sc-key-here"
    Config.DETECT_MODE = args.detect_mode

    # 创建并启动监控器
    monitor = OutdoorMonitor(Config)
    monitor.start()
