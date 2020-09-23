from custom.helper import rule, createTimer, getItemState, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("door_opener_control.py")
class DoorOpenerControlRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Dooropener_Timer")]
        self.timer = None

    def callback(self):
        self.timer = None
        postUpdate("Dooropener_Timer", OFF)

    def execute(self, module, input):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        if input["newState"] == OPEN:
            postUpdate("Dooropener_FF_Floor", ON)
            self.timer = createTimer(self.log, 3.0, self.callback)
            self.timer.start()

        else:
            postUpdateIfChanged("Dooropener_FF_Floor", OFF)
