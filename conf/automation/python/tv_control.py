from openhab import rule, Registry
from openhab.triggers import ItemCommandTrigger, ItemStateChangeTrigger

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Livingroom_Television_Key_POWER")
    ]
)
class LivingroomPowerState:
    def execute(self, module, input):
        if input["event"].getItemState() == scope.ON:
            Registry.getItem("pGF_Livingroom_Television_POWER").postUpdate(scope.ON)
        else:
            Registry.getItem("pGF_Livingroom_Television_POWER").postUpdate(scope.OFF)

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Livingroom_Television_POWER")
    ]
)
class LivingroomControl:
    def execute(self, module, input):
        if input["event"].getItemCommand() == scope.ON:
            Registry.getItem("pGF_Livingroom_SkyQ_Key_POWER").sendCommand(scope.ON)
            Registry.getItem("pGF_Livingroom_Television_Key_POWER").sendCommand(scope.ON)
        else:
            Registry.getItem("pGF_Livingroom_SkyQ_Key_POWER").sendCommand(scope.OFF)
            Registry.getItem("pGF_Livingroom_Television_Key_POWER").sendCommand(scope.OFF)
