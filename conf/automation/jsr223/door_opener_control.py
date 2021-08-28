from shared.helper import rule, startTimer, getItemState, postUpdate, sendCommand, sendCommandIfChanged
from shared.triggers import ItemStateChangeTrigger


@rule("door_opener_control.py")
class DoorOpenerControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Opener_Timer")]
        self.timer = None

    def callback(self):
        self.timer = None
        postUpdate("pOutdoor_Streedside_Gardendoor_Opener_Timer", OFF)
        sendCommandIfChanged("pOutdoor_Streedside_Gardendoor_Opener_Powered", OFF)

    def execute(self, module, input):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
            
        #self.log.info("{}".format(input["newState"]))

        if input["newState"] == ON:
            sendCommand("pOutdoor_Streedside_Gardendoor_Opener_Powered", ON)
            self.timer = startTimer(self.log, 3.0, self.callback)
        else:
            sendCommandIfChanged("pOutdoor_Streedside_Gardendoor_Opener_Powered", OFF)
