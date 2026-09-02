"""
telemetry.py - coleta de telemetria de dispositivo.

Em Android usa plyer (bateria) + pyjnius (Wi-Fi, storage, modelo, apps).
Fora do Android (ex: rodando no PC pra testar) retorna dados parciais/mock
sem quebrar, pra permitir desenvolvimento e teste do resto do fluxo.

Somente dados tecnicos. Nada de conteudo pessoal.
"""

import platform as _platform

try:
    from kivy.utils import platform as _kivy_platform
    IS_ANDROID = _kivy_platform == "android"
except Exception:
    IS_ANDROID = False


def _android_battery():
    try:
        from plyer import battery
        s = battery.status
        return {
            "percentage": s.get("percentage"),
            "charging": bool(s.get("isCharging")),
            "temperature": None,
        }
    except Exception:
        return {"percentage": None, "charging": False, "temperature": None}


def _android_wifi(activity):
    try:
        from jnius import autoclass
        Context = autoclass("android.content.Context")
        wifi = activity.getSystemService(Context.WIFI_SERVICE)
        info = wifi.getConnectionInfo()
        ssid = info.getSSID()
        if ssid:
            ssid = ssid.strip('"')
            if ssid in ("<unknown ssid>", "0x", ""):
                ssid = None
        ip_int = info.getIpAddress() & 0xFFFFFFFF
        ip = ".".join(str((ip_int >> (8 * i)) & 0xFF) for i in range(4))
        if ip == "0.0.0.0":
            ip = None
        rssi = info.getRssi()
        return {"ssid": ssid, "ip": ip, "rssi": rssi}
    except Exception:
        return {"ssid": None, "ip": None, "rssi": None}


def _android_storage():
    try:
        from jnius import autoclass
        StatFs = autoclass("android.os.StatFs")
        Environment = autoclass("android.os.Environment")
        path = Environment.getDataDirectory().getPath()
        stat = StatFs(path)
        free = stat.getAvailableBytes()
        total = stat.getTotalBytes()
        return {"free_mb": int(free / 1048576), "total_mb": int(total / 1048576)}
    except Exception:
        return {"free_mb": None, "total_mb": None}


def _android_device():
    try:
        from jnius import autoclass
        Build = autoclass("android.os.Build")
        VERSION = autoclass("android.os.Build$VERSION")
        SystemClock = autoclass("android.os.SystemClock")
        uptime = int(SystemClock.elapsedRealtime() / 1000)
        return {
            "model": Build.MODEL,
            "manufacturer": Build.MANUFACTURER,
            "android": VERSION.RELEASE,
            "uptime_s": uptime,
        }
    except Exception:
        return {"model": None, "manufacturer": None, "android": None, "uptime_s": None}


def _android_app_count(activity):
    try:
        pm = activity.getPackageManager()
        apps = pm.getInstalledApplications(0)
        return apps.size()
    except Exception:
        return None


def _get_activity():
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity


def collect(device_id, device_name):
    """Retorna dict de telemetria pronto pra enviar ao servidor."""
    if IS_ANDROID:
        activity = _get_activity()
        battery = _android_battery()
        wifi = _android_wifi(activity)
        storage = _android_storage()
        device = _android_device()
        app_count = _android_app_count(activity)
    else:
        # fallback desktop: coleta o que da em Python puro, resto None
        import shutil
        try:
            du = shutil.disk_usage("/")
            storage = {"free_mb": int(du.free / 1048576),
                       "total_mb": int(du.total / 1048576)}
        except Exception:
            storage = {"free_mb": None, "total_mb": None}
        battery = {"percentage": None, "charging": False, "temperature": None}
        wifi = {"ssid": None, "ip": None, "rssi": None}
        device = {"model": _platform.node() or "desktop",
                  "manufacturer": _platform.system(),
                  "android": None,
                  "uptime_s": None}
        app_count = None

    return {
        "device_id": device_id,
        "name": device_name,
        "battery": battery,
        "wifi": wifi,
        "storage": storage,
        "device": device,
        "apps": list(range(app_count)) if app_count else [],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(collect("test-device", "Teste"), indent=2))
