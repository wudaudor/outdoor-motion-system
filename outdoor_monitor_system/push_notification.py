# -*- coding: utf-8 -*-
"""
Server酱微信推送模块
用于向用户手机发送微信通知
"""

import requests
import time
from datetime import datetime
from typing import Optional


class ServerChanPusher:
    """Server酱微信推送器"""

    # Server酱 API 地址（新版 v2）
    API_URL = "https://push.example.com/{sckey}.send"

    def __init__(self, sc_key: str):
        """
        参数:
            sc_key: Server酱的 SCKEY
        """
        self.sc_key = sc_key
        self.api_url = self.API_URL.replace("{sckey}", sc_key)

    def send(
        self,
        title: str,
        desp: str = "",
        short: bool = False
    ) -> bool:
        """
        发送微信通知

        参数:
            title: 消息标题（最多64字节）
            desp: 消息内容（支持 Markdown，最大 64KB）
            short: 是否使用新版 API（False 兼容旧版）

        返回:
            是否发送成功
        """
        try:
            payload = {
                "text": title,
                "desp": desp
            }

            response = requests.post(self.api_url, data=payload, timeout=10)
            result = response.json()

            if result.get("errno") == 0 or result.get("code") == 0:
                return True
            else:
                print(f"推送失败: {result.get("errmsg", "未知错误")}")
                return False

        except requests.exceptions.Timeout:
            print("推送超时")
            return False
        except requests.exceptions.RequestException as e:
            print(f"推送请求异常: {e}")
            return False
        except Exception as e:
            print(f"推送异常: {e}")
            return False

    def send_motion_alert(
        self,
        device_id: str,
        image_url: Optional[str] = None,
        location: str = "监控区域",
        threshold: int = 1
    ) -> bool:
        """
        发送运动检测报警

        参数:
            device_id: 设备ID
            image_url: 事件图片 URL
            location: 位置描述
            threshold: 检测到的目标数量

        返回:
            是否发送成功
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"🚨 监控报警 [{device_id}]"

        desp = f"""
## 检测到人员入侵

- **设备ID**: {device_id}
- **检测时间**: {now}
- **位置**: {location}
- **检测目标数**: {threshold} 个

{f"**事件图片**: [点击查看]({image_url})" if image_url else ""}

> 本消息由 VisionFive 2 监控系统自动发送
"""

        return self.send(title, desp)

    def send_status(
        self,
        device_id: str,
        status: str,
        battery_level: Optional[int] = None,
        extra_info: str = ""
    ) -> bool:
        """
        发送设备状态通知

        参数:
            device_id: 设备ID
            status: 状态描述
            battery_level: 电量百分比（低功耗模式）
            extra_info: 额外信息
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = f"📷 设备状态 [{device_id}]"

        battery_info = f"\n- **电量**: {battery_level}%" if battery_level else ""

        desp = f"""
## 设备状态更新

- **设备ID**: {device_id}
- **状态**: {status}
- **时间**: {now}{battery_info}

{extra_info}
"""

        return self.send(title, desp)

    def send_test(self) -> bool:
        """发送测试消息"""
        print(f"正在发送测试消息...")
        return self.send(
            title="✅ 测试消息",
            desp=f"这是来自 VisionFive 2 的测试消息\n\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )


# ============ 使用示例 ============

if __name__ == "__main__":
    import sys

    # 从命令行参数获取 SCKEY
    if len(sys.argv) < 2:
        print("用法: python push_notification.py <SCKEY>")
        print("请先访问 https://sc.ftqq.com/ 注册并获取 SCKEY")
        sys.exit(1)

    sckey = sys.argv[1]
    pusher = ServerChanPusher(sckey)

    # 发送测试消息
    if pusher.send_test():
        print("✅ 测试消息发送成功！")
    else:
        print("❌ 测试消息发送失败，请检查 SCKEY 是否正确")

    # 发送报警测试
    print("\n发送报警测试...")
    pusher.send_motion_alert(
        device_id="VF2-01",
        image_url="http://your-server.com/uploads/test.jpg",
        location="门口",
        threshold=1
    )
