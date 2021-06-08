from shared.helper import getItemState
from org.openhab.core.library.types import OnOffType

class PresenceHelper:
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
