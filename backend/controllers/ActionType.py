from enum import Enum


class ActionType(str, Enum):
    AUTO = "AUTO"
    CLARIFICATION = "CLARIFICATION"
    AGENT = "AGENT"
