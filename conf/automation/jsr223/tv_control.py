from custom.helper import rule, getItemState, sendCommand, postUpdate, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger, ItemCommandTrigger, ThingEventTrigger

@rule("tv_control.py")
class TvLivingroomStatusRule:
    def __init__(self):
        self.triggers = [ ThingEventTrigger("samsungtv:tv:livingroom", "ThingStatusInfoChangedEvent") ]

    def execute(self, module, input):
        postUpdate("TV_KEY_POWER", ON if input["event"].getStatusInfo().getStatus().toString() == "ONLINE" else OFF )

@rule("tv_control.py")
class TvLivingroomControlRule:
    def __init__(self):
        self.triggers = [ ItemCommandTrigger("TV_KEY_POWER") ]

    def execute(self, module, input):
        if input["event"].getItemCommand() == ON:
            sendCommand("TV_KEY_POWER_ON",ON)
        else:
            pass
        #postUpdate("TV_KEY_POWER", ON if input["event"].getStatusInfo() == ONLINE else OFF )
