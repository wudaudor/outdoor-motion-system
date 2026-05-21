#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
户外监控统一入口 — 所有可调参数集中在此文件顶部

用法:
    python run.py
    python run.py --sckey SCT你的SCKEY
    python run.py --upload-url http://192.168.137.1:5000/upload
"""

# ============================================================
# 摄像头
# ============================================================
CAMERA_INDEX = 4               # /dev/videoX
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
RECORD_FPS = 15.0

# ============================================================
# GPIO（物理引脚编号）
# ============================================================
LED_PIN = 36
BUZZER_PIN = 38
ALERT_TIMES = 3
ALERT_ON_SEC = 0.3
ALERT_OFF_SEC = 0.2

# ============================================================
# ROI (x, y, w, h)
# ============================================================
ROI_X = 320
ROI_Y = 180
ROI_W = 640
ROI_H = 360

# ============================================================
# MOG2 背景建模
# ============================================================
AREA_THRESHOLD = 1200          # 最小运动面积(px)
MOG2_HISTORY = 500
MOG2_VAR_THRESHOLD = 40        # 方差阈值，越大越不敏感，户外30-50
MOG2_DETECT_SHADOWS = True
MOG2_SHADOW_THRESHOLD = 200    # 阴影灰度阈值
MORPH_KERNEL_SIZE = 5
MORPH_KERNEL_SHAPE = "ellipse" # ellipse|rect|cross

# ============================================================
# HOG 行人检测
# ============================================================
HOG_MIN_WEIGHT = 0.65          # SVM置信度(0-1)，越高越严格
HOG_MAX_WIDTH = 640            # 检测前缩放宽度
HOG_HIT_THRESHOLD = 0.0
HOG_WIN_STRIDE = (8, 8)
HOG_PADDING = (16, 16)
HOG_SCALE = 1.05

# ============================================================
# 几何过滤
# ============================================================
GEOM_MIN_HEIGHT = 64           # 候选框最小高度
GEOM_MIN_ASPECT = 1.5          # 高/宽最小比（人体~2-3）

# ============================================================
# 肤色验证 HSV
# ============================================================
SKIN_H_LOW = 0
SKIN_H_HIGH = 20
SKIN_S_LOW = 60                # 饱和度下限，排除米色/灰色
SKIN_S_HIGH = 255
SKIN_V_LOW = 80
SKIN_V_HIGH = 255
SKIN_MIN_PIXELS = 80
SKIN_MIN_RATIO = 0.05

# ============================================================
# NMS 去重
# ============================================================
NMS_OVERLAP = 0.35

# ============================================================
# 帧过滤
# ============================================================
DARK_THRESHOLD = 55.0          # 平均灰度低于此值跳过
BLUR_THRESHOLD = 80.0          # Laplacian方差低于此值跳过，VF2建议降至50
SHAKE_RATIO = 0.45             # 运动面积占比超此值判为抖动

# ============================================================
# 防抖 + 确认
# ============================================================
SHAKE_COOLDOWN_FRAMES = 20
PERSON_CONFIRM_FRAMES = 2      # 连续N帧检测到人才触发

# ============================================================
# 清晰帧选取
# ============================================================
BEST_FRAME_CAPTURES = 5

# ============================================================
# 运行
# ============================================================
WORK_SECONDS = 20
RECORD_SECONDS = 10
DETECT_INTERVAL = 0.1

# ============================================================
# I/O（命令行可覆盖）
# ============================================================
UPLOAD_URL = "http://your-server-ip:5000/upload"
DEVICE_ID = "VF2-01"
SCKEY = "your-sc-key-here"
SAVE_DIR = "./data"

# ============================================================
# ============ 以下组装运行，一般无需改动 ============
# ============================================================

import cv2
import time
import argparse
import requests
import os
import sys
from pathlib import Path
from datetime import datetime
from threading import Thread
from urllib.parse import urljoin
import VisionFive.gpio as GPIO

from motion_detection import MotionDetector, PersonDetector, measure_sharpness
from push_notification import ServerChanPusher


def _build_parser():
    p = argparse.ArgumentParser(description="户外监控 - VisionFive 2")
    p.add_argument('--upload-url', default=UPLOAD_URL)
    p.add_argument('--device-id', default=DEVICE_ID)
    p.add_argument('--sckey', default=os.environ.get("SCKEY", SCKEY))
    p.add_argument('--no-push', action='store_true')
    p.add_argument('--save-dir', default=SAVE_DIR)
    p.add_argument('--work-sec', type=int, default=WORK_SECONDS)
    p.add_argument('--record-sec', type=int, default=RECORD_SECONDS)
    return p


class _GPIO:
    def __init__(self):
        self._t = None
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

    def alert(self):
        def _run():
            for _ in range(ALERT_TIMES):
                GPIO.output(LED_PIN, GPIO.HIGH); GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(ALERT_ON_SEC)
                GPIO.output(LED_PIN, GPIO.LOW); GPIO.output(BUZZER_PIN, GPIO.LOW)
                time.sleep(ALERT_OFF_SEC)
        if not (self._t and self._t.is_alive()):
            self._t = Thread(target=_run, daemon=True); self._t.start()

    def cleanup(self):
        if self._t and self._t.is_alive(): self._t.join(timeout=2)
        GPIO.cleanup()


class Runner:
    def __init__(self, args):
        self.args = args
        self.base = args.upload_url.rsplit("/upload", 1)[0].rstrip("/")
        sd = Path(args.save_dir)
        self.snap_dir = sd / "snapshots"; self.vid_dir = sd / "videos"
        self.snap_dir.mkdir(parents=True, exist_ok=True)
        self.vid_dir.mkdir(parents=True, exist_ok=True)

        roi = (ROI_X, ROI_Y, ROI_W, ROI_H)

        self.md = MotionDetector(
            roi=roi, area_threshold=AREA_THRESHOLD,
            history=MOG2_HISTORY, var_threshold=MOG2_VAR_THRESHOLD,
            detect_shadows=MOG2_DETECT_SHADOWS, shadow_threshold=MOG2_SHADOW_THRESHOLD,
            morph_kernel_size=MORPH_KERNEL_SIZE, morph_kernel_shape=MORPH_KERNEL_SHAPE
        )
        self.pd = PersonDetector(
            roi=roi, min_weight=HOG_MIN_WEIGHT, max_width=HOG_MAX_WIDTH,
            hit_threshold=HOG_HIT_THRESHOLD, win_stride=HOG_WIN_STRIDE,
            padding=HOG_PADDING, scale=HOG_SCALE,
            geom_min_height=GEOM_MIN_HEIGHT, geom_min_aspect=GEOM_MIN_ASPECT,
            skin_h_low=SKIN_H_LOW, skin_h_high=SKIN_H_HIGH,
            skin_s_low=SKIN_S_LOW, skin_s_high=SKIN_S_HIGH,
            skin_v_low=SKIN_V_LOW, skin_v_high=SKIN_V_HIGH,
            skin_min_pixels=SKIN_MIN_PIXELS, skin_min_ratio=SKIN_MIN_RATIO,
            nms_overlap=NMS_OVERLAP
        )

        self.push_ok = not args.no_push and args.sckey != "your-sc-key-here"
        self.pusher = ServerChanPusher(args.sckey) if self.push_ok else None
        self.gpio = _GPIO()
        self.cap = None
        self._cooldown = 0

    def _open_cam(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        time.sleep(2)
        if not self.cap.isOpened():
            print(f"摄像头 /dev/video{CAMERA_INDEX} 打开失败")
            return False
        print(f"摄像头就绪 {FRAME_WIDTH}x{FRAME_HEIGHT}")
        return True

    def _snap(self, label="snapshot"):
        if not self.cap or not self.cap.isOpened(): return None
        ret, f = self.cap.read()
        if not ret: return None
        p = self.snap_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{label}.jpg"
        cv2.imwrite(str(p), f)
        return p

    def _upload(self, path, kind="image"):
        if not path or not path.exists(): return None
        try:
            with open(path, 'rb') as fh:
                r = requests.post(self.args.upload_url, files={'file': fh},
                    data={'device_id': self.args.device_id, 'kind': kind,
                          'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, timeout=30)
            if r.status_code == 200:
                j = r.json()
                u = j.get("url", "")
                return urljoin(self.base.rstrip("/") + "/", u.lstrip("/")) if u else f"{self.base}/uploads/{j.get('filename', path.name)}"
        except requests.exceptions.RequestException as e:
            print(f"上传失败: {e}")
        return None

    def _push(self, url, count=1):
        if self.pusher:
            self.pusher.send_motion_alert(device_id=self.args.device_id, image_url=url,
                                          location="监控区域", threshold=count)

    def _is_shake(self, contours):
        if not contours: return False
        a = sum(cv2.contourArea(c) for c in contours)
        if a / (ROI_W * ROI_H) >= SHAKE_RATIO:
            print(f"镜头抖动 占比{a/(ROI_W*ROI_H):.2f}")
            return True
        return False

    def _record(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = self.vid_dir / f"{ts}_event.mp4"
        out = cv2.VideoWriter(str(fp), cv2.VideoWriter_fourcc(*'mp4v'),
                              RECORD_FPS, (FRAME_WIDTH, FRAME_HEIGHT))
        t0 = time.time()
        while time.time() - t0 < RECORD_SECONDS:
            ok, f = self.cap.read()
            if not ok: break
            cv2.putText(f, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            out.write(f)
        out.release()
        print(f"录像: {fp}")

    def run(self):
        print(f"设备:{self.args.device_id}  上传:{self.args.upload_url}")
        if not self._open_cam(): sys.exit(1)

        snap = self._snap("scheduled")
        if snap: self._upload(snap, "snapshot")

        hit = False; cnt = 0; streak = 0; t0 = time.time()

        while time.time() - t0 < WORK_SECONDS:
            ret, frame = self.cap.read()
            if not ret: continue

            if self._cooldown > 0:
                self._cooldown -= 1; time.sleep(DETECT_INTERVAL); continue

            if cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean() < DARK_THRESHOLD:
                streak = 0; time.sleep(DETECT_INTERVAL); continue

            if measure_sharpness(frame) < BLUR_THRESHOLD:
                streak = 0; time.sleep(DETECT_INTERVAL); continue

            is_motion, _, contours = self.md.detect(frame)

            if is_motion:
                if self._is_shake(contours):
                    streak = 0; self._cooldown = SHAKE_COOLDOWN_FRAMES
                    self.md.reset_background(); time.sleep(DETECT_INTERVAL); continue

                pok, boxes = self.pd.detect(frame)
                if not pok:
                    streak = 0; time.sleep(DETECT_INTERVAL); continue

                streak += 1
                if streak < PERSON_CONFIRM_FRAMES:
                    time.sleep(DETECT_INTERVAL); continue

                cnt += 1; streak = 0
                print(f"检测到人 #{cnt}  框:{len(boxes)}")

                if not hit:
                    hit = True
                    best, best_s = frame, measure_sharpness(frame)
                    for _ in range(BEST_FRAME_CAPTURES - 1):
                        ok, f = self.cap.read()
                        if ok:
                            s = measure_sharpness(f)
                            if s > best_s: best_s, best = s, f

                    ep = self.snap_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_event.jpg"
                    for x, y, w, h, wt in boxes:
                        cv2.rectangle(best, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(best, f"person {wt:.2f}", (x, max(20, y-8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.imwrite(str(ep), best)
                    self.gpio.alert()
                    u = self._upload(ep, "event")
                    self._push(u, count=cnt)
                    self._record()
            else:
                streak = 0

            if cv2.waitKey(1) & 0xFF == ord('q'): break
            time.sleep(DETECT_INTERVAL)

        self.gpio.cleanup()
        print(f"周期结束，检测{'到' if hit else '无'}人")


if __name__ == "__main__":
    Runner(_build_parser().parse_args()).run()
