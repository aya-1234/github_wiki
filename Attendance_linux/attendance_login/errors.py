"""アプリケーション固有例外。"""


class AttendanceLoginError(Exception):
    """利用者へ分類して通知できる基底例外。"""

    event = "UNEXPECTED_ERROR"
    exit_code = 9


class ConfigurationError(AttendanceLoginError):
    event = "CONFIGURATION_ERROR"
    exit_code = 2


class BrowserStartupError(AttendanceLoginError):
    event = "BROWSER_STARTUP_ERROR"
    exit_code = 3


class AuthenticationTimeoutError(AttendanceLoginError):
    event = "AUTHENTICATION_TIMEOUT"
    exit_code = 4


class SelectorChangedError(AttendanceLoginError):
    event = "SELECTOR_CHANGED"
    exit_code = 5


class ApplicationBlockedError(AttendanceLoginError):
    event = "APPLICATION_BLOCKED"
    exit_code = 5


class NetworkError(AttendanceLoginError):
    event = "NETWORK_ERROR"
    exit_code = 6


class NotificationError(AttendanceLoginError):
    event = "NOTIFICATION_ERROR"
    exit_code = 7
