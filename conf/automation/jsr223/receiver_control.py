from shared.helper import rule, sendCommand
from core.triggers import ItemStateChangeTrigger

@rule("receiver_control.py")
class ReceiverControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Receiver_State")]

    def execute(self, module, input):
        if input["newState"] == OPEN:
            sendCommand("pGF_Livingroom_Socket_Bassbox_Powered", ON)
        else:
            sendCommand("pGF_Livingroom_Socket_Bassbox_Powered", OFF)
