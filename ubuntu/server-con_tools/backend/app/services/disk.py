import platform

import psutil


def get_disks():
    filesystems = []

    partitions = psutil.disk_partitions(all=False)

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            filesystems.append(
                {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )

        except (PermissionError, OSError):
            continue

    return {
        "os": platform.system(),
        "filesystems": filesystems,
    }
