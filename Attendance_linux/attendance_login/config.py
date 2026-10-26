"""環境変数からの設定読込。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from urllib.parse import urlparse

from .errors import ConfigurationError


DOTENV_PATH_ENV = "DOTENV_PATH"


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    """.env の1行をパースして (キー, 値) を返す。

    - 空行・`#` 始まりのコメント行は None を返す
    - `export ` プレフィックスを無視する
    - 値の前後の空白を除去する
    - シングル/ダブルクォートで囲まれた値はクォートを除去する
    - クォートされていない値の末尾インラインコメント（` # ...`）を除去する
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export "):].lstrip()
    if "=" not in stripped:
        return None
    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None

    value = raw_value.strip()
    if not value:
        return (key, "")
    if value[0] == value[-1] and value[0] in ("'", '"'):
        # クォートで囲まれた値：内部のインラインコメントは値の一部とみなす
        return (key, value[1:-1])
    # クォートされていない値：末尾の ` # ...` をインラインコメントとして除去
    value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
    return (key, value)


def _find_dotenv_path() -> Path | None:
    """.env の探索パスを返す。存在しなければ None。

    探索順:
    1. 環境変数 DOTENV_PATH が指定されていればそれ
    2. プロジェクトルート（config.py の親の親）
    3. 現在の作業ディレクトリ
    """
    candidates: list[Path] = []
    dotenv_path_env = os.getenv(DOTENV_PATH_ENV, "").strip()
    if dotenv_path_env:
        candidates.append(Path(dotenv_path_env).expanduser())
    candidates.append(Path(__file__).resolve().parent.parent / ".env")
    candidates.append(Path.cwd() / ".env")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _load_dotenv() -> None:
    """.env ファイルを自動読込する。

    - ファイルが存在しなければ何もしない
    - 既に os.environ に存在するキーは上書きしない
    """
    dotenv_path = _find_dotenv_path()
    if dotenv_path is None:
        return
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        parsed = _parse_dotenv_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if key not in os.environ:
            os.environ[key] = value


DEFAULT_TOP_URL = (
    "https://meitecgroup.my.salesforce.com/?ec=302&"
    "startURL=%2Fvisualforce%2Fsession%3Furl%3D"
    "https%253A%252F%252Fmeitecgroup.lightning.force.com"
    "%252Flightning%252Fn%252Ftex__TimeAttendance"
)


def _boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} は true または false で指定してください")


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} は整数で指定してください") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(
            f"{name} は {minimum}～{maximum} の範囲で指定してください"
        )
    return value


def _https_url(name: str, value: str, *, allow_empty: bool = False) -> str:
    if allow_empty and not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConfigurationError(f"{name} は有効なHTTPS URLで指定してください")
    return value


def _time(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    match = re.fullmatch(r"(\d{2}):(\d{2})", value)
    if not match:
        raise ConfigurationError(f"{name} は HH:MM 形式で指定してください")
    hour, minute = (int(part) for part in match.groups())
    if hour > 23 or minute > 59:
        raise ConfigurationError(f"{name} は有効な時刻で指定してください")
    return value


def _text(name: str, default: str, *, maximum: int | None = None) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ConfigurationError(f"{name} は空文字にできません")
    if any(character in value for character in "\r\n"):
        raise ConfigurationError(f"{name} に改行は使用できません")
    if maximum is not None and len(value) > maximum:
        raise ConfigurationError(
            f"{name} は {maximum} 文字以内で指定してください"
        )
    return value


@dataclass(frozen=True)
class Config:
    top_url: str
    user_data_dir: Path
    profile_directory: str | None
    target_account: str
    webhook_url: str
    login_timeout: int
    page_load_timeout: int
    webhook_timeout: int
    headless: bool
    keep_browser_open_on_error: bool
    log_level: str
    log_file: Path | None
    log_retention_days: int
    work_start_time: str
    work_end_time: str
    work_place: str
    business_content: str
    work_input_timeout: int
    server_request_delay_seconds: int = 5
    workload_enabled: bool = False
    workload_file: Path | None = None
    workload_allow_overwrite: bool = False
    application_enabled: bool = False
    application_confirm_only: bool = True
    application_auto_submit: bool = False
    workload_tolerance_minutes: int = 0
    daily_request_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        # 既存の環境変数を優先しつつ、.env ファイルを自動読込する
        _load_dotenv()
        user_data_raw = os.getenv("CHROME_USER_DATA_DIR", "").strip()
        if not user_data_raw:
            raise ConfigurationError("CHROME_USER_DATA_DIR は必須です")

        target_account = os.getenv("TARGET_ACCOUNT", "").strip()
        if not target_account:
            raise ConfigurationError("TARGET_ACCOUNT は必須です")
        if any(character in target_account for character in "\r\n"):
            raise ConfigurationError("TARGET_ACCOUNT に改行は使用できません")

        profile = os.getenv("CHROME_PROFILE_DIRECTORY", "").strip() or None
        webhook_url = _https_url(
            "WEBHOOK_URL",
            os.getenv("WEBHOOK_URL", "").strip(),
            allow_empty=True,
        )
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("LOG_LEVEL が不正です")

        workload_file_raw = os.getenv("WORKLOAD_FILE", "").strip()
        workload_enabled = _boolean("WORKLOAD_ENABLED")
        application_enabled = _boolean("APPLICATION_ENABLED")
        application_confirm_only = _boolean(
            "APPLICATION_CONFIRM_ONLY", default=True
        )
        application_auto_submit = _boolean("APPLICATION_AUTO_SUBMIT")
        if workload_enabled and not workload_file_raw:
            raise ConfigurationError(
                "WORKLOAD_ENABLED=true の場合は WORKLOAD_FILE が必須です"
            )
        if application_auto_submit and not application_enabled:
            raise ConfigurationError(
                "APPLICATION_AUTO_SUBMIT=true の場合は "
                "APPLICATION_ENABLED=true が必要です"
            )
        if application_auto_submit and application_confirm_only:
            raise ConfigurationError(
                "自動申請時は APPLICATION_CONFIRM_ONLY=false が必要です"
            )

        return cls(
            top_url=_https_url(
                "ATTENDANCE_TOP_URL",
                os.getenv("ATTENDANCE_TOP_URL", DEFAULT_TOP_URL).strip(),
            ),
            user_data_dir=Path(user_data_raw).expanduser(),
            profile_directory=profile,
            target_account=target_account,
            webhook_url=webhook_url,
            login_timeout=_integer("LOGIN_TIMEOUT_SECONDS", 60, 1, 300),
            page_load_timeout=_integer(
                "PAGE_LOAD_TIMEOUT_SECONDS", 30, 1, 300
            ),
            webhook_timeout=_integer("WEBHOOK_TIMEOUT_SECONDS", 5, 1, 60),
            headless=_boolean("HEADLESS"),
            keep_browser_open_on_error=_boolean(
                "KEEP_BROWSER_OPEN_ON_ERROR"
            ),
            log_level=log_level,
            log_file=(
                Path(os.environ["LOG_FILE"]).expanduser()
                if os.getenv("LOG_FILE", "").strip()
                else None
            ),
            log_retention_days=_integer(
                "LOG_RETENTION_DAYS", 30, 1, 365
            ),
            work_start_time=_time("WORK_START_TIME", "09:00"),
            work_end_time=_time("WORK_END_TIME", "17:45"),
            work_place=_text("WORK_PLACE", "出社"),
            business_content=_text(
                "BUSINESS_CONTENT", "開発業務", maximum=255
            ),
            work_input_timeout=_integer(
                "WORK_INPUT_TIMEOUT_SECONDS", 10, 1, 120
            ),
            server_request_delay_seconds=_integer(
                "SERVER_REQUEST_DELAY_SECONDS", 5, 0, 300
            ),
            workload_enabled=workload_enabled,
            workload_file=(
                Path(workload_file_raw).expanduser()
                if workload_file_raw
                else None
            ),
            workload_allow_overwrite=_boolean(
                "WORKLOAD_ALLOW_OVERWRITE"
            ),
            application_enabled=application_enabled,
            application_confirm_only=application_confirm_only,
            application_auto_submit=application_auto_submit,
            workload_tolerance_minutes=_integer(
                "WORKLOAD_TOLERANCE_MINUTES", 0, 0, 60
            ),
            daily_request_enabled=_boolean("DAILY_REQUEST_ENABLED"),
        )

    def validate_runtime_paths(self) -> None:
        if not self.user_data_dir.exists():
            raise ConfigurationError(
                f"CHROME_USER_DATA_DIR が存在しません: {self.user_data_dir}"
            )
        if not self.user_data_dir.is_dir():
            raise ConfigurationError(
                "CHROME_USER_DATA_DIR はディレクトリを指定してください"
            )
        if self.workload_enabled:
            if self.workload_file is None or not self.workload_file.is_file():
                raise ConfigurationError(
                    "WORKLOAD_FILE に存在するファイルを指定してください"
                )
