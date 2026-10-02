import psutil


def get_processes():
    processes = []

    for process in psutil.process_iter(
        [
            "pid",
            "ppid",
            "name",
            "username",
            "cpu_percent",
            "memory_percent",
        ]
    ):
        try:
            info = process.info

            if info["pid"] == 0:
                continue

            memory = info["memory_percent"]

            if memory is not None:
                memory = round(memory, 2)

            processes.append(
                {
                    "pid": info["pid"],
                    "ppid": info["ppid"],
                    "name": info["name"],
                    "username": info["username"],
                    "cpu": info["cpu_percent"],
                    "memory": memory,
                }
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes

def get_process(pid: int):
    try:
        process = psutil.Process(pid)

        try:
            username = process.username()
        except psutil.AccessDenied:
            username = None

        try:
            status = process.status()
        except psutil.AccessDenied:
            status = None

        try:
            cpu = process.cpu_percent(interval=0.1)
        except psutil.AccessDenied:
            cpu = None

        try:
            memory = round(process.memory_percent(), 2)
        except psutil.AccessDenied:
            memory = None

        try:
            threads = process.num_threads()
        except psutil.AccessDenied:
            threads = None

        try:
            cwd = process.cwd()
        except psutil.AccessDenied:
            cwd = None

        try:
            exe = process.exe()
        except psutil.AccessDenied:
            exe = None

        try:
            command = " ".join(process.cmdline())
        except psutil.AccessDenied:
            command = None

        return {
            "pid": process.pid,
            "ppid": process.ppid(),
            "name": process.name(),
            "username": username,
            "status": status,
            "cpu": cpu,
            "memory": memory,
            "threads": threads,
            "cwd": cwd,
            "exe": exe,
            "create_time": process.create_time(),
            "command": command,
        }

    except psutil.NoSuchProcess:
        return None

    except psutil.AccessDenied:
        return None

def get_process_children(pid: int):
    try:
        process = psutil.Process(pid)

        children = []

        for child in process.children(recursive=False):
            try:
                children.append(
                    {
                        "pid": child.pid,
                        "name": child.name(),
                        "username": child.username(),
                        "status": child.status(),
                        "cpu": child.cpu_percent(interval=0.1),
                        "memory": round(child.memory_percent(), 2),
                    }
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return children

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_process_tree():
    processes = get_processes()

    process_map = {
        process["pid"]: {
            **process,
            "children": [],
        }
        for process in processes
    }

    roots = []

    for process in process_map.values():
        ppid = process["ppid"]

        if ppid is None or ppid == 0 or ppid not in process_map:
            roots.append(process)
        else:
            process_map[ppid]["children"].append(process)

    return roots

def terminate_process(pid: int):
    try:
        process = psutil.Process(pid)

        process.terminate()

        return {
            "pid": pid,
            "action": "terminate",
            "status": "sent",
        }

    except psutil.NoSuchProcess:
        return None

    except psutil.AccessDenied:
        raise PermissionError(f"Access denied: process {pid}")
