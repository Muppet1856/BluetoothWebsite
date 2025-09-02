import os
import subprocess
from typing import List, Tuple

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


def list_client_networks() -> Tuple[List[str], bool]:
    """Return available client SSIDs and whether a Wi-Fi interface exists."""
    try:
        p = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        has_iface = "No Wi-Fi device" not in (p.stderr or "")
        nets = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    except Exception:
        has_iface = False
        nets = []
    ap_ssid = read_ap_ssid()
    return [n for n in nets if n != ap_ssid], has_iface


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


def get_client_ip_info() -> dict:
    """Return IP address, subnet mask and gateway for the Wi-Fi interface."""
    info = {"ip": None, "mask": None, "gateway": None}
    try:
        p = subprocess.run(
            ["ip", "-4", "addr", "show", AP_INTERFACE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        for line in p.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                addr = line.split()[1]  # e.g. 192.168.1.5/24
                ip, prefix = addr.split("/")
                info["ip"] = ip
                try:
                    import ipaddress

                    info["mask"] = str(
                        ipaddress.IPv4Network("0.0.0.0/" + prefix).netmask
                    )
                except Exception:
                    info["mask"] = None
                break
    except Exception:
        pass

    try:
        p = subprocess.run(
            ["ip", "route", "show", "default", "dev", AP_INTERFACE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        for line in p.stdout.splitlines():
            parts = line.strip().split()
            if parts and parts[0] == "default" and "via" in parts:
                info["gateway"] = parts[parts.index("via") + 1]
                break
    except Exception:
        pass

    return info
