"""向网关下发控制指令。"""
from typing import Optional, Tuple
import requests
from config_loader import GATEWAY_IPS


def send_play_voice(region: str, device_id: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """
    向指定区域的网关发送 PLAY_VOICE 指令。
    返回 (是否成功, 失败时错误信息)。
    """
    gateway_ip = GATEWAY_IPS.get(region)
    if not gateway_ip:
        return False, f"no gateway configured for region {region!r}"
    try:
        response = requests.get(
            f"{gateway_ip}/control?cmd=PLAY_VOICE&target={device_id}",
            timeout=timeout,
        )
        if response.status_code == 200:
            return True, None
        return False, f"gateway returned {response.status_code}"
    except requests.RequestException as e:
        return False, str(e)


def send_query(region: str, device_id: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """
    请求清醒状态下的标签立即上报。

    QUERY 不能唤醒处于深睡状态的 ESP32 标签，因为当前硬件没有把
    LoRa DIO0 配置为深睡唤醒源。
    返回 (是否成功, 失败时错误信息)。
    """
    gateway_ip = GATEWAY_IPS.get(region)
    if not gateway_ip:
        return False, f"no gateway configured for region {region!r}"
    try:
        response = requests.get(
            f"{gateway_ip}/control?cmd=QUERY&target={device_id}",
            timeout=timeout,
        )
        if response.status_code == 200:
            return True, None
        return False, f"gateway returned {response.status_code}"
    except requests.RequestException as e:
        return False, str(e)
