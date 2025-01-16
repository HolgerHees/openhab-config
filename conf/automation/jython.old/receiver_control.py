from shared.helper import rule, sendCommand
from shared.triggers import ItemStateChangeTrigger


@rule()
class ReceiverControl:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pGF_Livingroom_Receiver_State")]

    def execute(self, module, input):
        if input["newState"] == OPEN:
            sendCommand("pGF_Livingroom_Socket_Bassbox_Powered", ON)
        else:
            sendCommand("pGF_Livingroom_Socket_Bassbox_Powered", OFF)
