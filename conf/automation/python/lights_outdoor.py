from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from custom.weather import WeatherHelper
from custom.frigate import FrigateHelper

from datetime import datetime, timedelta
import time
import threading

import scope


LIGHT_SETUP = [
    ["pOutdoor_Streedside_Frontdoor_Light_Powered", "pOutdoor_Streedside_Frontdoor_Automatic_Switch", [ "pOutdoor_Streedside_Frontdoor_Motiondetector_State" ] ],
    ["pOutdoor_Carport_Light_Powered"             , "pOutdoor_Carport_Automatic_Switch"             , [ "pOutdoor_Carport_Motiondetector_State" ] ],
    ["pOutdoor_Terrace_Light_Brightness"          , "pOutdoor_Terrace_Automatic_Switch"             , [ "pOutdoor_Terrace_Motiondetector_State1", "pOutdoor_Terrace_Motiondetector_State2" ] ],
    ["pOutdoor_Streedside_Garage_Light_Powered"   , "pOutdoor_Streedside_Garage_Automatic_Switch"   , [ "pOutdoor_Streedside_Garage_Motiondetector_State" ] ],
    ["pOutdoor_Garden_Garage_Light_Powered"       , "pOutdoor_Garden_Garage_Automatic_Switch"       , [ "pOutdoor_Garden_Garage_Motiondetector_State" ] ],
    ["pOutdoor_Toolshed_Right_Light_Powered"      , "pOutdoor_Toolshed_Right_Automatic_Switch"      , [ "pOutdoor_Toolshed_Right_Motiondetector_State" ] ]
]

TIMER_DURATIONS = 60.0

class LightState:
    timerMappings = {}
    ruleTimeouts = {}

@rule(
    triggers = [
#        ItemStateChangeTrigger("pOutdoor_Streedside_Frontdoor_Motiondetector_State", scope.OPEN),
        ItemStateChangeTrigger("pOutdoor_Toolshed_Right_Motiondetector_State", scope.OPEN)
    ]
)
class FrigateNotification:
    def execute(self, module, input):
        # only during night
        if Registry.getItemState("pOutdoor_Astro_Light_Level").intValue() > 0:
            return

        if input["event"].getItemName() == "pOutdoor_Streedside_Frontdoor_Motiondetector_State":
            FrigateHelper.createEvent("streedside", "motion")
        else:
            FrigateHelper.createEvent("toolshed", "motion")

# Main MotionDetector Switch
@rule(
    triggers = [
        # must be a stateChange trigger to get also events from physical knx buttons
        ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch")
    ]
)
class MotiondetectorSwitch:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        last = LightState.ruleTimeouts.get("Motiondetector_Outdoor_Main_Switch",now - timedelta(hours=1))
        
        # No Motion Detector related events
        if (now - last).total_seconds() > 1:
            itemState = input["event"].getItemState()
            
            self.logger.info("MotiondetectorOutdoorSwitchRule => last: {}, now: {}, state: {}".format(last,now,itemState))

            if itemState == scope.ON:
                LightState.ruleTimeouts["Light_Outdoor"] = now

            for mapping in LIGHT_SETUP:
                Registry.getItem(mapping[0]).sendCommandIfDifferent(scope.OFF if "Powered" in mapping[0] else 0)

            for mapping in LIGHT_SETUP:
                Registry.getItem(mapping[1]).postUpdateIfDifferent(itemState)

# Individual MotionDetector Switchs
@rule()
class MotiondetectorIndividualSwitch:
    def buildTriggers(self):
        triggers = []
        for mapping in LIGHT_SETUP:
            triggers.append(ItemCommandTrigger(mapping[1]))
        return triggers

    def execute(self, module, input):
        now = datetime.now().astimezone()
        
        LightState.ruleTimeouts["Motiondetector_Outdoor_Main_Switch"] = now
        LightState.ruleTimeouts["Light_Outdoor"] = now

        item_name = input['event'].getItemName()
        item_command = input['event'].getItemCommand()
        
        switchState = scope.ON
        for i, entry in enumerate(LIGHT_SETUP):
            if entry[1] == item_name:
                Registry.getItem(entry[0]).sendCommandIfDifferent(scope.OFF)
                if item_command == scope.OFF:
                    switchState = scope.OFF
            else:
                if Registry.getItemState(entry[1]) == scope.OFF:
                    switchState = scope.OFF
                    
        # must be a command to inform physical knx switch
        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(switchState)
        
# Light Control Events
@rule()
class Control:
    def buildTriggers(self):
        triggers = []
        for mapping in LIGHT_SETUP:
            triggers.append(ItemStateChangeTrigger(mapping[0]))
        return triggers

    def execute(self, module, input):
        now = datetime.now().astimezone()
        last = LightState.ruleTimeouts.get("Light_Outdoor",now - timedelta(hours=1))

        # No Motion Detector related events
        if (now - last).total_seconds() > 1:
            item_name = input['event'].getItemName()

            self.logger.info("LightOutdoorControlRule => Automatic_Switches => OFF, last: {}, now: {}".format(last,now))

            timer = LightState.timerMappings.get(item_name)
            if timer is not None:
                timer.cancel()
                LightState.timerMappings[item_name] = None

            for i, entry in enumerate(LIGHT_SETUP):
                if entry[0] == item_name:
                    #LightState.ruleTimeouts["Motiondetector_Outdoor_Individual_Switches"] = now

                    # just an update to avoid triggering => MotiondetectorOutdoorIndividualSwitchRule
                    if Registry.getItem(entry[1]).postUpdateIfDifferent(scope.OFF):
                        LightState.ruleTimeouts["Motiondetector_Outdoor_Main_Switch"] = now

                        # must be a command to inform physical knx switch
                        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(scope.OFF)
                    break

# Motion Detector Events
@rule()
class MotionDetector:
    def buildTriggers(self):
        triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(LIGHT_SETUP):
            for motionDetectorItem in entry[2]:
                triggers.append(ItemStateChangeTrigger(motionDetectorItem,state=scope.OPEN))
                self.triggerMappings[motionDetectorItem]=i
        return triggers

    def callback(self,entry):
        if Registry.getItemState(entry[1]) == scope.ON:
            for motionDetectorItem in entry[2]:
                if Registry.getItemState(motionDetectorItem) == scope.OPEN:
                    LightState.timerMappings[entry[0]] = threading.Timer(TIMER_DURATIONS, self.callback, [entry])
                    LightState.timerMappings[entry[0]].start()
                    return

            LightState.ruleTimeouts["Light_Outdoor"] = datetime.now().astimezone()

            self.logger.info("MotionDetector: callback for {} => {}".format(entry[0], LightState.ruleTimeouts["Light_Outdoor"]));

            Registry.getItem(entry[0]).sendCommand(0 if Registry.getItem(entry[0]).getType() == "Dimmer" else scope.OFF )
        LightState.timerMappings[entry[0]] = None

    def execute(self, module, input):
        item_name = input['event'].getItemName()

        entry = LIGHT_SETUP[self.triggerMappings[item_name]]
        if Registry.getItemState("pOther_Automatic_State_Outdoorlights") == scope.ON and Registry.getItemState(entry[1]) == scope.ON:
            timer = LightState.timerMappings.get(item_name)
            if timer is not None:
                timer.cancel()
            LightState.timerMappings[entry[0]] = threading.Timer(TIMER_DURATIONS, self.callback, [entry])
            LightState.timerMappings[entry[0]].start()

            LightState.ruleTimeouts["Light_Outdoor"] = datetime.now().astimezone()

            self.logger.info("MotionDetector: execute for {} => {}".format(entry[0], LightState.ruleTimeouts["Light_Outdoor"]));

            Registry.getItem(entry[0]).sendCommand(100 if Registry.getItem(entry[0]).getType() == "Dimmer" else scope.ON)
