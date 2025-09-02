import os
import subprocess
from typing import List

AP_CONF = "/etc/hostapd/hostapd.conf"
AP_INTERFACE = "wlan0"


def _hostname() -> str:
    return os.uname().nodename


def read_ap_ssid() -> str:
    try:
        with open(AP_CONF) as f:
            for line in f:
                if line.startswith("ssid="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return _hostname()


def set_ap_ssid(ssid: str) -> None:
    lines: List[str] = []
    try:
        with open(AP_CONF) as f:
            for line in f:
                if line.startswith("ssid="):
                    lines.append(f"ssid={ssid}\n")
                else:
                    lines.append(line)
    except FileNotFoundError:
        lines = [
            f"interface={AP_INTERFACE}\n",
            "driver=nl80211\n",
            f"ssid={ssid}\n",
            "hw_mode=g\n",
            "channel=1\n",
            "auth_algs=1\n",
            "ignore_broadcast_ssid=0\n",
        ]
    with open(AP_CONF, "w") as f:
        f.writelines(lines)
    try:
        subprocess.run(["sudo", "systemctl", "restart", "hostapd"], check=False)
    except Exception:
        pass


def list_client_networks() -> List[str]:
    try:
        p = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        nets = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    except Exception:
        nets = []
    ap_ssid = read_ap_ssid()
    return [n for n in nets if n != ap_ssid]


def connect_client(ssid: str) -> None:
    try:
        subprocess.run(
            ["nmcli", "device", "wifi", "connect", ssid],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception:
        pass
