from shared.helper import rule, sendCommand, postUpdate
from shared.triggers import ItemCommandTrigger, ThingEventTrigger


@rule()
class TvControlLivingroomStatus:
    def __init__(self):
        self.triggers = [ ThingEventTrigger("samsungtv:tv:livingroom", "ThingStatusInfoChangedEvent") ]

    def execute(self, module, input):
        postUpdate("pGF_Livingroom_Television_Key_POWER", ON if input["event"].getStatusInfo().getStatus().toString() == "ONLINE" else OFF )

@rule()
class TvControlLivingroomControl:
    def __init__(self):
        self.triggers = [ ItemCommandTrigger("pGF_Livingroom_Television_Key_POWER") ]

    def execute(self, module, input):
        if input["event"].getItemCommand() == ON:
            sendCommand("pGF_Livingroom_Television_Key_POWER_ON",ON)
        #else:
        #    sendCommand("pGF_Livingroom_Television_Key_POWER_OFF",ON)
        #postUpdate("pGF_Livingroom_Television_Key_POWER", ON if input["event"].getStatusInfo() == ONLINE else OFF )
