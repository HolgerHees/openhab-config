from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger, ItemStateCondition

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

    @staticmethod
    #2026-01-11 18:56:27.788 [INFO ] [openhab.event.ItemStateChangedEvent ] - Item 'pOutdoor_Light_Automatic_Main_Switch' changed from OFF to ON (source: org.openhab.core.thing$knx:device:bridge:motion_outdoor:main)

    #2026-01-11 18:56:55.345 [INFO ] [openhab.event.ItemCommandEvent      ] - Item 'pOutdoor_Light_Automatic_Main_Switch' received command OFF (source: org.openhab.ui.basic$haus:0100=>org.openhab.core.io.rest)
    #IGNORE: 2026-01-11 18:56:55.347 [INFO ] [openhab.event.ItemStateChangedEvent ] - Item 'pOutdoor_Light_Automatic_Main_Switch' changed from ON to OFF (source: org.openhab.core.autoupdate.optimistic)

    #IGNORE: 2026-01-11 18:57:49.612 [INFO ] [openhab.event.ItemCommandEvent      ] - Item 'pOutdoor_Light_Automatic_Main_Switch' received command ON (source: org.openhab.core.automation.module.script)
    #IGNORE: 2026-01-11 18:57:49.612 [INFO ] [openhab.event.ItemStateChangedEvent ] - Item 'pOutdoor_Light_Automatic_Main_Switch' changed from OFF to ON (source: org.openhab.core.autoupdate.optimistic)
    def isUnrelatedEventSource(event):
        return event.getSource() in ["org.openhab.core.autoupdate.optimistic", "org.openhab.core.automation.module.script"]

    @staticmethod
    def getItemStateOrCommand(event):
        return event.getItemState() if event.getType() == "ItemStateChangedEvent" else event.getItemCommand()

@rule(
    triggers = [
#        ItemStateChangeTrigger("pOutdoor_Streedside_Frontdoor_Motiondetector_State", scope.OPEN),
        ItemStateChangeTrigger("pOutdoor_Toolshed_Right_Motiondetector_State", scope.OPEN)
    ],
    conditions = [
        ItemStateCondition("pOutdoor_Astro_Light_Level", operator="<=", state="0 lx" ) # only during night
    ]
)
class FrigateNotification:
    def execute(self, module, input):
        if input["event"].getItemName() == "pOutdoor_Streedside_Frontdoor_Motiondetector_State":
            FrigateHelper.createEvent("streedside", "motion")
        else:
            FrigateHelper.createEvent("toolshed", "motion")

# Reactivation of automatic lights if terrace window is closed
@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Livingroom_Openingcontact_Window_Terrace_State")
    ]
)
class AutomaticMainControl:
    def __init__(self):
        self.timer = None

    def callback(self):
        if Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(scope.ON):
            for mapping in LIGHT_SETUP:
                Registry.getItem(mapping[0]).sendCommandIfDifferent(scope.OFF if "Powered" in mapping[0] else 0)
                Registry.getItem(mapping[1]).sendCommandIfDifferent(scope.ON)

    def execute(self, module, input):
        self.logger.info(">>> AutomaticMainControl: {} {}".format(input['event'].getSource(),input['event'].getType()))

        if Registry.getItemState("pOutdoor_Light_Automatic_Main_Switch") == scope.ON:
            return

        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

        if input['event'].getItemState() == scope.CLOSED:
            self.timer = threading.Timer(5, self.callback)
            self.timer.start()

@rule(
    triggers = [
        ItemCommandTrigger("pOutdoor_Light_Automatic_Main_Switch"),
        ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch") # must be a stateChange trigger to get also events from physical knx buttons
    ]
)
class AutomaticMainSwitch:
    def execute(self, module, input):
        self.logger.info(">>> AutomaticMainSwitch: {} {}".format(input['event'].getSource(),input['event'].getType()))

        if LightState.isUnrelatedEventSource(input['event']):
            return

        item_state = LightState.getItemStateOrCommand(input['event'])
        for mapping in LIGHT_SETUP:
            Registry.getItem(mapping[0]).sendCommandIfDifferent(scope.OFF if "Powered" in mapping[0] else 0)
            Registry.getItem(mapping[1]).sendCommandIfDifferent(item_state)

@rule()
class AutomaticIndividualSwitch:
    def buildTriggers(self):
        triggers = []
        for mapping in LIGHT_SETUP:
            triggers.append(ItemCommandTrigger(mapping[1]))
            triggers.append(ItemStateChangeTrigger(mapping[1]))
        return triggers

    def execute(self, module, input):
        self.logger.info(">>> AutomaticIndividualSwitch: {} {}".format(input['event'].getSource(),input['event'].getType()))

        if LightState.isUnrelatedEventSource(input['event']):
            return

        item_state = LightState.getItemStateOrCommand(input['event'])

        item_name = input['event'].getItemName()
        switch_state = scope.ON
        for i, entry in enumerate(LIGHT_SETUP):
            if entry[1] == item_name:
                Registry.getItem(entry[0]).sendCommandIfDifferent(scope.OFF)
                if item_state == scope.OFF:
                    switch_state = scope.OFF
            else:
                if Registry.getItemState(entry[1]) == scope.OFF:
                    switch_state = scope.OFF

        # must be a command to inform physical knx switch
        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(switch_state)
        
@rule()
class LightControl:
    def buildTriggers(self):
        triggers = []
        for mapping in LIGHT_SETUP:
            triggers.append(ItemCommandTrigger(mapping[0]))
            triggers.append(ItemStateChangeTrigger(mapping[0]))
        return triggers

    def execute(self, module, input):
        self.logger.info(">>> LightControl: {} {}".format(input['event'].getSource(),input['event'].getType()))

        if LightState.isUnrelatedEventSource(input['event']):
            return

        item_name = input['event'].getItemName()

        timer = LightState.timerMappings.get(item_name)
        if timer is not None:
            timer.cancel()
            LightState.timerMappings[item_name] = None

        for i, entry in enumerate(LIGHT_SETUP):
            if entry[0] == item_name:
                # just an update to avoid triggering => MotiondetectorOutdoorIndividualSwitchRule
                if Registry.getItem(entry[1]).postUpdateIfDifferent(scope.OFF):
                    # must be a command to inform physical knx switch
                    Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(scope.OFF)
                break

@rule(
    conditions = [
        ItemStateCondition("pOther_Automatic_State_Outdoorlights", operator="=", state=scope.ON )
    ]
)
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

            Registry.getItem(entry[0]).sendCommand(0 if Registry.getItem(entry[0]).getType() == "Dimmer" else scope.OFF )
        LightState.timerMappings[entry[0]] = None

    def execute(self, module, input):
        self.logger.info(">>> MotionDetector: {}".format(input['event'].getSource()))

        item_name = input['event'].getItemName()

        entry = LIGHT_SETUP[self.triggerMappings[item_name]]
        if Registry.getItemState(entry[1]) == scope.ON:
            timer = LightState.timerMappings.get(item_name)
            if timer is not None:
                timer.cancel()
            LightState.timerMappings[entry[0]] = threading.Timer(TIMER_DURATIONS, self.callback, [entry])
            LightState.timerMappings[entry[0]].start()

            Registry.getItem(entry[0]).sendCommand(100 if Registry.getItem(entry[0]).getType() == "Dimmer" else scope.ON)
