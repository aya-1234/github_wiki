import platform
import time

import psutil


def get_system():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time

    load_average = psutil.getloadavg()

    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "kernel": platform.release(),
        "architecture": platform.machine(),

        "cpu": psutil.cpu_percent(interval=0.1),
        "cpu_count": psutil.cpu_count(),

        "memory": memory.percent,
        "disk": disk.percent,

        "uptime": round(uptime, 2),
        "boot_time": boot_time,

        "load_average": {
            "1m": load_average[0],
            "5m": load_average[1],
            "15m": load_average[2],
        },
    }
