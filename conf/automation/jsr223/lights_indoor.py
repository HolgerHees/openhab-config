from custom.helper import rule, getItemState, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger 

@rule("lights_indoor.py")
class AwayEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Outdoorlights", state="ON")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("Light_FF_Floor_Hue_Brightness", 30)
            sendCommand("Light_FF_Livingroom_Hue_Brightness4", 30)


@rule("lights_indoor.py")
class HolidayGoSleepingRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("Light_FF_Floor_Hue_Brightness", OFF)
            sendCommand("Light_FF_Livingroom_Hue_Brightness4", OFF)
            sendCommand("Light_FF_Floor_Ceiling", ON)


@rule("lights_indoor.py")
class HolidayNightRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 30 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("Light_FF_Floor_Ceiling", OFF)
