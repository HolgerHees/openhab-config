from openhab import rule, Registry, Timer
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger

from datetime import datetime, timedelta
import time


manual_mappings = [
    ["pOutdoor_Streedside_Frontdoor_Light_Powered", "pOutdoor_Streedside_Frontdoor_Automatic_Switch", [ "pOutdoor_Streedside_Frontdoor_Motiondetector_State" ] ],
    ["pOutdoor_Carport_Light_Powered"             , "pOutdoor_Carport_Automatic_Switch"             , [ "pOutdoor_Carport_Motiondetector_State" ] ],
    ["pOutdoor_Terrace_Light_Brightness"          , "pOutdoor_Terrace_Automatic_Switch"             , [ "pOutdoor_Terrace_Motiondetector_State1", "pOutdoor_Terrace_Motiondetector_State2" ] ],
    ["pOutdoor_Streedside_Garage_Light_Powered"   , "pOutdoor_Streedside_Garage_Automatic_Switch"   , [ "pOutdoor_Streedside_Garage_Motiondetector_State" ] ],
    ["pOutdoor_Garden_Garage_Light_Powered"       , "pOutdoor_Garden_Garage_Automatic_Switch"       , [ "pOutdoor_Garden_Garage_Motiondetector_State" ] ],
    ["pOutdoor_Toolshed_Right_Light_Powered"      , "pOutdoor_Toolshed_Right_Automatic_Switch"      , [ "pOutdoor_Toolshed_Right_Motiondetector_State" ] ]
]

timer_durations = 60.0
timer_mappings = {}
rule_timeouts = {}

# Main MotionDetector Switch
@rule(
    triggers = [
        # must be a stateChange trigger to get also events from physical knx buttons
        ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch")
    ]
)
class MotiondetectorSwitch:
    def execute(self, module, input):
        global rule_timeouts
        now = datetime.now().astimezone()
        last = rule_timeouts.get("Motiondetector_Outdoor_Main_Switch",now - timedelta(hours=1))
        
        if (now - last).total_seconds() > 1:
            itemState = input["event"].getItemState()
            
            self.logger.info("MotiondetectorOutdoorSwitchRule => last: {}, now: {}, state: {}".format(last,now,itemState))

            if itemState == ON:
                rule_timeouts["Light_Outdoor"] = now

            for mapping in manual_mappings:
                Registry.getItem(mapping[0]).sendCommandIfDifferent(OFF if "Powered" in mapping[0] else 0)

            #rule_timeouts["Motiondetector_Outdoor_Individual_Switches"] = now
            for mapping in manual_mappings:
                Registry.getItem(mapping[1]).postUpdateIfDifferent(itemState)

# Individual MotionDetector Switchs
@rule()
class MotiondetectorIndividualSwitch:
    def buildTriggers(self):
        triggers = []
        for mapping in manual_mappings:
            triggers.append(ItemCommandTrigger(mapping[1]))
        return triggers

    def execute(self, module, input):
        global rule_timeouts
        now = datetime.now().astimezone()
        
        #last = rule_timeouts.get("Motiondetector_Outdoor_Individual_Switches",0)
        #if now - last > 1000:
        rule_timeouts["Motiondetector_Outdoor_Main_Switch"] = now
        rule_timeouts["Light_Outdoor"] = now

        item_name = input['event'].getItemName()
        item_command = input['event'].getItemCommand()
        
        switchState = ON
        for i, entry in enumerate(manual_mappings):
            if entry[1] == item_name:
                Registry.getItem(entry[0]).sendCommandIfDifferent(OFF)
                if item_command == OFF:
                    switchState = OFF
            else:
                if Registry.getItemState(entry[1]) == OFF:
                    switchState = OFF
                    
        # must be a command to inform physical knx switch
        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(switchState)

        #self.logger.info("{} {} {} {} {} ".format(gs,f,c,t,gg))
        
# Light Control Events
@rule()
class Control:
    def buildTriggers(self):
        triggers = []
        for mapping in manual_mappings:
            triggers.append(ItemStateChangeTrigger(mapping[0]))
        return triggers

    def execute(self, module, input):
        #self.logger.info("{}".format(input))
        
        global rule_timeouts
        now = datetime.now().astimezone()
        last = rule_timeouts.get("Light_Outdoor",now - timedelta(hours=1))
        
        # No Motion Detector related events
        if (now - last).total_seconds() > 1:
            item_name = input['event'].getItemName()
            
            self.logger.info("LightOutdoorControlRule => Automatic_Switches => OFF, last: {}, now: {}".format(last,now))
        
            global timer_mappings
            timer = timer_mappings.get(item_name)
            if timer is not None:
                timer.cancel()
            
            for i, entry in enumerate(manual_mappings):
                if entry[0] == item_name:
                    #rule_timeouts["Motiondetector_Outdoor_Individual_Switches"] = now

                    # just an update to avoid triggering => MotiondetectorOutdoorIndividualSwitchRule
                    if Registry.getItem(entry[1]).postUpdateIfDifferent(OFF):
                        rule_timeouts["Motiondetector_Outdoor_Main_Switch"] = now
                        
                        # must be a command to inform physical knx switch
                        Registry.getItem("pOutdoor_Light_Automatic_Main_Switch").sendCommandIfDifferent(OFF)
                    #self.logger.info("{} {}".format(item_name,now-last))
                    break

# Motion Detector Events
@rule()
class MotionDetector:
    def buildTriggers(self):
        triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manual_mappings):
            for motionDetectorItem in entry[2]:
                triggers.append(ItemStateChangeTrigger(motionDetectorItem,state="OPEN"))
                self.triggerMappings[motionDetectorItem]=i
        return triggers

    def callback(self,entry):
        global timer_mappings
        if Registry.getItemState(entry[1]) == ON:
            for motionDetectorItem in entry[2]:
                if Registry.getItemState(motionDetectorItem) == OPEN:
                    timer_mappings[entry[0]] = Timer.createTimeout(timer_durations, self.callback,[entry])
                    return

            global rule_timeouts
            rule_timeouts["Light_Outdoor"] = datetime.now().astimezone()

            self.logger.info("MotionDetector: callback for {} => {}".format(entry[0], rule_timeouts["Light_Outdoor"]));

            Registry.getItem(entry[0]).sendCommand(0 if Registry.getItem(entry[0]).getType() == "Dimmer" else OFF )
            timer_mappings[entry[0]] = None
        else:
            timer_mappings[entry[0]] = None

    def execute(self, module, input):
        item_name = input['event'].getItemName()
        
        entry = manual_mappings[self.triggerMappings[item_name]]
        if Registry.getItemState("pOther_Automatic_State_Outdoorlights") == ON and Registry.getItemState(entry[1]) == ON:
            timer_mappings[entry[0]] = Timer.createTimeout(timer_durations, self.callback, [entry], old_timer = timer_mappings.get(entry[0]) )

            global rule_timeouts
            rule_timeouts["Light_Outdoor"] = datetime.now().astimezone()

            self.logger.info("MotionDetector: execute for {} => {}".format(entry[0], rule_timeouts["Light_Outdoor"]));

            Registry.getItem(entry[0]).sendCommand(100 if Registry.getItem(entry[0]).getType() == "Dimmer" else ON)
