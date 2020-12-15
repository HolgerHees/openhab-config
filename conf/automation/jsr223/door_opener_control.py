from shared.helper import rule, createTimer, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("door_opener_control.py")
class DoorOpenerControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOutdoor_Streedside_Gardendoor_Opener_Timer")]
        self.timer = None

    def callback(self):
        self.timer = None
        postUpdate("pOutdoor_Streedside_Gardendoor_Opener_Timer", OFF)

    def execute(self, module, input):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        if input["newState"] == OPEN:
            postUpdate("pOutdoor_Streedside_Gardendoor_Opener_Powered", ON)
            self.timer = createTimer(self.log, 3.0, self.callback)
            self.timer.start()

        else:
            postUpdateIfChanged("pOutdoor_Streedside_Gardendoor_Opener_Powered", OFF)
