# VisionFive 2 部署说明

本项目在 VisionFive 2 上运行监控端，主要依赖 Python、OpenCV、USB 摄像头、GPIO、HTTP 上传和微信推送。

## 1. 先把项目放到板子上

在 MobaXterm 左侧 SFTP 面板里，把本项目整个文件夹拖到板子的：

```bash
/home/user/outdoor_monitor
```

如果你的登录用户名不是 `user`，也可以放到：

```bash
~/outdoor_monitor
```

## 2. 安装运行环境和中文包

在 MobaXterm 的 SSH 终端里执行：

```bash
cd ~/outdoor_monitor
chmod +x scripts/*.sh
APP_DIR=~/outdoor_monitor ./scripts/vf2_install_deps.sh
```

这个脚本会安装：

- Python 3、pip、venv
- OpenCV、NumPy、Requests、Flask
- v4l-utils、ffmpeg、gpiod、screen、curl、vim
- VisionFive.gpio
- 中文环境 `zh_CN.UTF-8`
- 中文字体 `fonts-noto-cjk`、文泉驿字体
- fcitx5 中文输入法相关组件

装完后建议重启一次：

```bash
sudo reboot
```

如果你想安装 Debian 的完整简体中文任务包，可以这样运行，下载量会更大：

```bash
INSTALL_FULL_CHINESE_TASK=1 APP_DIR=~/outdoor_monitor ./scripts/vf2_install_deps.sh
```

## 3. 检查摄像头和依赖

重连 MobaXterm 后执行：

```bash
cd ~/outdoor_monitor
./scripts/vf2_smoke_test.sh
```

如果摄像头不是 `/dev/video4`，例如是 `/dev/video0`，这样测：

```bash
CAMERA_INDEX=0 ./scripts/vf2_smoke_test.sh
```

## 4. Windows 端先启动接收服务器

在 Windows 项目目录里执行：

```cmd
python server_receive.py
```

如果你是电脑通过网线给板子共享网络，Windows 共享网卡常见地址是：

```text
192.168.137.1
```

板子上的上传地址通常就是：

```text
http://192.168.137.1:5000/upload
```

## 5. 前台调试运行

先在板子上前台跑一次，方便看错误：

```bash
cd ~/outdoor_monitor
sudo ./.venv/bin/python monitor_uploader.py \
  --camera-index 4 \
  --device-id VF2-01 \
  --upload-url http://192.168.137.1:5000/upload \
  --sckey SCT你的Server酱Key \
  --work-sec 20 \
  --record-sec 10
```

如果暂时不测试微信推送：

```bash
sudo ./.venv/bin/python monitor_uploader.py \
  --camera-index 4 \
  --device-id VF2-01 \
  --upload-url http://192.168.137.1:5000/upload \
  --no-push
```

## 6. 设置开机自启

前台确认能跑后，再安装 systemd 服务：

```bash
cd ~/outdoor_monitor
UPLOAD_URL=http://192.168.137.1:5000/upload \
SCKEY=SCT你的Server酱Key \
CAMERA_INDEX=4 \
DEVICE_ID=VF2-01 \
./scripts/vf2_install_service.sh
```

查看状态：

```bash
sudo systemctl status outdoor-monitor
tail -f ~/outdoor_monitor/data/logs/monitor.log
```

停止或重启：

```bash
sudo systemctl stop outdoor-monitor
sudo systemctl restart outdoor-monitor
```

## 注意

StarFive 官方快速手册提示当前 Debian 镜像不要执行 `apt upgrade`，因为可能覆盖 StarFive 提供的定制包。这里的脚本只执行 `apt-get update` 和 `apt-get install`。
