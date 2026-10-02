import subprocess


def get_connections():
    result = subprocess.run(
        [
            "lsof",
            "-nP",
            "-iTCP",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    connections = []

    for line in result.stdout.splitlines()[1:]:
        parts = line.split()

        if len(parts) < 10:
            continue

        command = parts[0]

        try:
            pid = int(parts[1])
        except ValueError:
            continue

        # lsofでは NAME が9番目以降
        name_start = line.find("TCP ")

        if name_start == -1:
            continue

        name = line[name_start + 4:].strip()

        status = None

        for candidate in (
            "LISTEN",
            "ESTABLISHED",
            "CLOSE_WAIT",
            "TIME_WAIT",
            "SYN_SENT",
            "SYN_RECEIVED",
            "FIN_WAIT_1",
            "FIN_WAIT_2",
            "LAST_ACK",
            "CLOSING",
        ):
            suffix = f" ({candidate})"

            if name.endswith(suffix):
                status = candidate
                name = name[:-len(suffix)]
                break

        local_address = None
        local_port = None
        remote_address = None
        remote_port = None

        if "->" in name:
            local, remote = name.split("->", 1)
        else:
            local = name
            remote = None

        # IPv6
        if local.startswith("[") and "]:" in local:
            local_address, local_port = local.rsplit("]:", 1)
            local_address = local_address[1:]

        # IPv4 / *
        elif ":" in local:
            local_address, local_port = local.rsplit(":", 1)

        if remote:
            if remote.startswith("[") and "]:" in remote:
                remote_address, remote_port = remote.rsplit("]:", 1)
                remote_address = remote_address[1:]

            elif ":" in remote:
                remote_address, remote_port = remote.rsplit(":", 1)

        try:
            if local_port is not None:
                local_port = int(local_port)
        except ValueError:
            local_port = None

        try:
            if remote_port is not None:
                remote_port = int(remote_port)
        except ValueError:
            remote_port = None

        connections.append({
            "pid": pid,
            "process": command,
            "protocol": "tcp",
            "local_address": local_address,
            "local_port": local_port,
            "remote_address": remote_address,
            "remote_port": remote_port,
            "status": status,
        })

    return connections
