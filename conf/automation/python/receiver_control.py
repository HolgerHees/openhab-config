from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Livingroom_Receiver_State")
    ]
)
class Main:
    def execute(self, module, input):
        Registry.getItem("pGF_Livingroom_Socket_Bassbox_Powered").sendCommand(scope.ON if input["newState"] == scope.OPEN else scope.OFF)
