from shared.helper import rule, getItemState, sendCommand
from shared.triggers import CronTrigger, ItemStateChangeTrigger 


@rule("lights_indoor.py")
class AwayEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Outdoorlights", state="ON")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Lighting") == ON and getItemState("pOther_Presence_State").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Hue_Color", 30)
            sendCommand("pGF_Livingroom_Light_Hue4_Color", 30)


@rule("lights_indoor.py")
class HolidayGoSleepingRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 22 * * ?")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Lighting") == ON and getItemState("pOther_Presence_State").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Hue_Color", OFF)
            sendCommand("pGF_Livingroom_Light_Hue4_Color", OFF)
            sendCommand("pGF_Corridor_Light_Ceiling_Powered", ON)


@rule("lights_indoor.py")
class HolidayNightRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 30 22 * * ?")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Lighting") == ON and getItemState("pOther_Presence_State").intValue() == 0:
            sendCommand("pGF_Corridor_Light_Ceiling_Powered", OFF)
