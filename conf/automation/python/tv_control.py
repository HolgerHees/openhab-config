from openhab import rule, Registry
from openhab.triggers import ItemCommandTrigger, ItemStateChangeTrigger


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Livingroom_Television_Key_POWER")
    ]
)
class LivingroomPowerState:
    def execute(self, module, input):
        if input["event"].getItemState() == ON:
            Registry.getItem("pGF_Livingroom_Television_POWER").postUpdate(ON)
        else:
            Registry.getItem("pGF_Livingroom_Television_POWER").postUpdate(OFF)

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Livingroom_Television_POWER")
    ]
)
class LivingroomControl:
    def execute(self, module, input):
        if input["event"].getItemCommand() == ON:
            Registry.getItem("pGF_Livingroom_SkyQ_Key_POWER").sendCommand(ON)
            Registry.getItem("pGF_Livingroom_Television_Key_POWER").sendCommand(ON)
        else:
            Registry.getItem("pGF_Livingroom_SkyQ_Key_POWER").sendCommand(OFF)
            Registry.getItem("pGF_Livingroom_Television_Key_POWER").sendCommand(OFF)
