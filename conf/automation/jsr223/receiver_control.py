from marvin.helper import rule, postUpdate
from openhab.triggers import ItemStateChangeTrigger

@rule("receiver_control.py")
class ReceiverControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Receiver_State")]

    def execute(self, module, input):
        if input["newState"] == OPEN:
            postUpdate("Socket_Bassbox", ON)
        else:
            postUpdate("Socket_Bassbox", OFF)
