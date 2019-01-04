from marvin.helper import rule, getFilteredChildItems, getItemState, sendCommand
from core.triggers import CronTrigger, ItemStateChangeTrigger 

arrivingFlag = False

@rule("lights_indoor.py")
class Arriving1Rule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence")]

    def execute(self, module, input):
        global arrivingFlag
        arrivingFlag = input["event"].getItemState().intValue() == 1 and input["oldState"].intValue() == 0


@rule("lights_indoor.py")
class Arriving2Rule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Door_FF_Floor","OPEN")]

    def execute(self, module, input):
        global arrivingFlag

        # should happen only once
        if arrivingFlag == True:
            if getItemState("State_Outdoorlights") == ON:
                sendCommand("Light_FF_Floor_Ceiling",ON)
            arrivingFlag = False

        
@rule("lights_indoor.py")
class SleepingRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Presence", "2" )]

    def execute(self, module, input):
        sendCommandIfChanged("Lights_Indoor", OFF)


@rule("lights_indoor.py")
class AwayEveningRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Outdoorlights", "ON")]

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
