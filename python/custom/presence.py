from shared.helper import getItemState
from org.openhab.core.library.types import OnOffType

class PresenceHelper:
    STATE_AWAY = 0
    STATE_MAYBE_PRESENT = 1
    STATE_PRESENT = 2
    STATE_MAYBE_SLEEPING = 3
    STATE_SLEEPING = 4

    @staticmethod
    def getPresentRecipients():
        recipients = []
        if getItemState("pOther_Presence_Holger_State") == OnOffType.ON:
            recipients.append('bot_holger')
        if getItemState("pOther_Presence_Sandra_State") == OnOffType.ON:
            recipients.append('bot_sandra')
        return recipients

    @staticmethod
    def getRecipientByStateItem(item):
        if item == u"pOther_Presence_Holger_State":
            return 'bot_holger'
        elif item == u"pOther_Presence_Sandra_State":
            return 'bot_sandra'
        return None
