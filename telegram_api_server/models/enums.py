from enum import Enum


class AccountType(str, Enum):
    USER = "user"
    BOT = "bot"


class AccountStatus(str, Enum):
    CREATING = "creating"
    WAITING_CODE = "waiting_code"
    WAITING_2FA = "waiting_2fa"
    READY = "ready"
    ERROR = "error"
    STOPPED = "stopped"
