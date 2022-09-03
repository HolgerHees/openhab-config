from shared.helper import getItemState
from org.openhab.core.library.types import OnOffType

from configuration import userConfigs

class PresenceHelper:
    STATE_AWAY = 0
    STATE_MAYBE_PRESENT = 1
    STATE_PRESENT = 2
    STATE_MAYBE_SLEEPING = 3
    STATE_SLEEPING = 4

    @staticmethod
    def getPresentRecipients():
        recipients = []
        for userName in userConfigs:
            if not userConfigs[userName]["state_item"] or getItemState(userConfigs[userName]["state_item"]) != OnOffType.ON:
                continue
            recipients.append(userName)
        return recipients

    @staticmethod
    def getRecipientByStateItem(stateItem):
        for userName in userConfigs:
            if userConfigs[userName]["state_item"] != stateItem:
                continue
            return userName
