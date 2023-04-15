from shared.helper import rule, getItemState, sendCommand, postUpdate, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger, ThingEventTrigger


@rule("tv_control.py")
class TvLivingroomStatusRule:
    def __init__(self):
        self.triggers = [ ThingEventTrigger("samsungtv:tv:livingroom", "ThingStatusInfoChangedEvent") ]

    def execute(self, module, input):
        postUpdate("pGF_Livingroom_Television_Key_POWER", ON if input["event"].getStatusInfo().getStatus().toString() == "ONLINE" else OFF )

@rule("tv_control.py")
class TvLivingroomControlRule:
    def __init__(self):
        self.triggers = [ ItemCommandTrigger("pGF_Livingroom_Television_Key_POWER") ]

    def execute(self, module, input):
        if input["event"].getItemCommand() == ON:
            sendCommand("pGF_Livingroom_Television_KeyPOWER_ON",ON)
        else:
            pass
        #postUpdate("pGF_Livingroom_Television_Key_POWER", ON if input["event"].getStatusInfo() == ONLINE else OFF )
