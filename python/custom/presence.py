from shared.helper import getItemState
from org.openhab.core.library.types import OnOffType

from configuration import userConfigs

class PresenceHelper:
    STATE_AWAY = 0
    STATE_MAYBE_PRESENT = 1
    STATE_PRESENT = 2
    STATE_MAYBE_SLEEPING = 3
    STATE_SLEEPING = 4
