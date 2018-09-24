from marvin.helper import rule, getFilteredChildItems, getItemState, sendCommand
from openhab.triggers import CronTrigger, ItemStateChangeTrigger


@rule("lights_indoor_auto.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sleeping", "OFF")]

    def execute(self, module, input):
        if (getItemState("Lights_FF") == OFF or (
                        len(getFilteredChildItems("Lights_FF", ON)) == 1 and getItemState("Light_FF_Floor_Ceiling") == ON)) and getItemState(
            "Shutters_FF") == DOWN:
            sendCommand("Light_FF_Livingroom_Diningtable", 100)


@rule("lights_indoor_auto.py")
class HolidayEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Outdoorlights", "ON")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Present") == OFF:
            sendCommand("Light_FF_Floor_Hue_Brightness", 30)
            sendCommand("Light_FF_Livingroom_Hue_Brightness4", 30)


@rule("lights_indoor_auto.py")
class HolidayGoSleepingRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Present") == OFF:
            sendCommand("Light_FF_Floor_Hue_Brightness", OFF)
            sendCommand("Light_FF_Livingroom_Hue_Brightness4", OFF)
            sendCommand("Light_FF_Floor_Ceiling", ON)


@rule("lights_indoor_auto.py")
class HolidayNightRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 30 22 * * ?")]

    def execute(self, module, input):
        if getItemState("Auto_Lighting") == ON and getItemState("State_Present") == OFF:
            sendCommand("Light_FF_Floor_Ceiling", OFF)
