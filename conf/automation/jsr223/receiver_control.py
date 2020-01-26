from custom.helper import rule, sendCommand
from core.triggers import ItemStateChangeTrigger

@rule("receiver_control.py")
class ReceiverControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Receiver_State")]

    def execute(self, module, input):
        if input["newState"] == OPEN:
            sendCommand("Socket_Livingroom_Bassbox", ON)
        else:
            sendCommand("Socket_Livingroom_Bassbox", OFF)
