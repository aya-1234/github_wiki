import platform
import subprocess


def get_services():
    os_name = platform.system()

    if os_name != "Linux":
        return {
            "os": os_name,
            "supported": False,
            "message": "systemd is not available on this operating system",
            "services": [],
        }

    try:
        result = subprocess.run(
            [
                "systemctl",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--no-legend",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        services = []

        for line in result.stdout.splitlines():
            parts = line.split(None, 4)

            if len(parts) < 4:
                continue

            services.append(
                {
                    "name": parts[0],
                    "load_state": parts[1],
                    "active_state": parts[2],
                    "sub_state": parts[3],
                }
            )

        return {
            "os": os_name,
            "supported": True,
            "services": services,
        }

    except FileNotFoundError:
        return {
            "os": os_name,
            "supported": False,
            "message": "systemctl is not available",
            "services": [],
        }

    except subprocess.CalledProcessError as error:
        return {
            "os": os_name,
            "supported": False,
            "message": error.stderr.strip(),
            "services": [],
        }

def get_service(name: str):
    os_name = platform.system()

    if os_name != "Linux":
        return {
            "name": name,
            "os": os_name,
            "supported": False,
            "message": "systemd is not available on this operating system",
        }

    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                name,
                "--no-pager",
                "--property=Id",
                "--property=Description",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=SubState",
                "--property=UnitFileState",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = {}

        for line in result.stdout.splitlines():
            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            data[key] = value

        if data.get("LoadState") == "not-found":
            return None

        return {
            "name": data.get("Id", name),
            "description": data.get("Description", ""),
            "load_state": data.get("LoadState"),
            "active_state": data.get("ActiveState"),
            "sub_state": data.get("SubState"),
            "unit_file_state": data.get("UnitFileState"),
        }

    except FileNotFoundError:
        return {
            "name": name,
            "os": os_name,
            "supported": False,
            "message": "systemctl is not available",
        }

    except subprocess.CalledProcessError:
        return None
