from shared.helper import rule, getItemState, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger 

@rule("lights_indoor.py")
class AwayEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Outdoorlights", state="ON")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Hue_Brightness", 30)
            sendCommand("pGF_Livingroom_Light_Hue4_Brightness", 30)


@rule("lights_indoor.py")
class HolidayGoSleepingRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Hue_Brightness", OFF)
            sendCommand("pGF_Livingroom_Light_Hue4_Brightness", OFF)
            sendCommand("pGF_Corridor_Light_Ceiling_Powered", ON)


@rule("lights_indoor.py")
class HolidayNightRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 30 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Presence").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Ceiling_Powered", OFF)
