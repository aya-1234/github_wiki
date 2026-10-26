import getpass
import os
import platform
import pwd


def get_users():
    users = []

    for entry in pwd.getpwall():
        users.append(
            {
                "username": entry.pw_name,
                "uid": entry.pw_uid,
                "gid": entry.pw_gid,
                "home": entry.pw_dir,
                "shell": entry.pw_shell,
            }
        )

    return {
        "os": platform.system(),
        "current_user": getpass.getuser(),
        "uid": os.getuid(),
        "users": users,
    }

def get_user(username: str):
    try:
        entry = pwd.getpwnam(username)

        return {
            "username": entry.pw_name,
            "uid": entry.pw_uid,
            "gid": entry.pw_gid,
            "home": entry.pw_dir,
            "shell": entry.pw_shell,
        }

    except KeyError:
        return None
