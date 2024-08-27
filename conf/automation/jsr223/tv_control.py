from shared.helper import rule, sendCommand, postUpdate
from shared.triggers import ItemCommandTrigger, ItemStateChangeTrigger, ThingEventTrigger


@rule()
class TvControlLivingroomPowerState:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Livingroom_Television_Key_POWER")
        ]

    def execute(self, module, input):
        if input["event"].getItemState() == ON:
            postUpdate("pGF_Livingroom_Television_POWER",ON)
        else:
            postUpdate("pGF_Livingroom_Television_POWER",OFF)

@rule()
class TvControlLivingroomControl:
    def __init__(self):
        self.triggers = [ ItemCommandTrigger("pGF_Livingroom_Television_POWER") ]

    def execute(self, module, input):
        if input["event"].getItemCommand() == ON:
            sendCommand("pGF_Livingroom_SkyQ_Key_POWER",ON)
            sendCommand("pGF_Livingroom_Television_Key_POWER",ON)
        else:
            sendCommand("pGF_Livingroom_SkyQ_Key_POWER",OFF)
            sendCommand("pGF_Livingroom_Television_Key_POWER",OFF)
