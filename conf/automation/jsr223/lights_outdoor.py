import time
from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit

from shared.helper import rule, startTimer, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged
from shared.triggers import ItemCommandTrigger, ItemStateChangeTrigger


manualMappings = [
    ["pOutdoor_Streedside_Frontdoor_Light_Powered", "pOutdoor_Streedside_Frontdoor_Automatic_Switch","pOutdoor_Streedside_Frontdoor_Motiondetector_State"],
    ["pOutdoor_Carport_Light_Powered", "pOutdoor_Carport_Automatic_Switch","pOutdoor_Carport_Motiondetector_State"],
    ["pOutdoor_Terrace_Light_Brightness", "pOutdoor_Terrace_Automatic_Switch",None],
    ["pOutdoor_Streedside_Garage_Light_Powered", "pOutdoor_Streedside_Garage_Automatic_Switch","pOutdoor_Streedside_Garage_Motiondetector_State"],
    ["pOutdoor_Garden_Garage_Light_Powered", "pOutdoor_Garden_Garage_Automatic_Switch","pOutdoor_Garden_Garage_Motiondetector_State"]
]

timerDuration = 60.0
timerMappings = {}
ruleTimeouts = {}

# Main MotionDetector Switch
@rule("lights_outdoor.py")
class MotiondetectorOutdoorSwitchRule:
    def __init__(self):
        # must be a stateChange trigger to get also events from physical knx buttons
        self.triggers = [ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch")]

    def execute(self, module, input):
        global ruleTimeouts
        now = ZonedDateTime.now()
        last = ruleTimeouts.get("Motiondetector_Outdoor_Main_Switch",0)
        
        if ChronoUnit.SECONDS.between(last,now) > 1:
            itemState = input["event"].getItemState()
            
            if itemState == ON:
                ruleTimeouts["Light_Outdoor"] = now

                sendCommandIfChanged("pOutdoor_Streedside_Garage_Light_Powered",OFF)
                sendCommandIfChanged("pOutdoor_Streedside_Frontdoor_Light_Powered",OFF)
                sendCommandIfChanged("pOutdoor_Carport_Light_Powered",OFF)
                sendCommandIfChanged("pOutdoor_Terrace_Light_Brightness",0)
                sendCommandIfChanged("pOutdoor_Garden_Garage_Light_Powered",OFF)

            #ruleTimeouts["Motiondetector_Outdoor_Individual_Switches"] = now
            postUpdateIfChanged("pOutdoor_Streedside_Garage_Automatic_Switch",itemState)
            postUpdateIfChanged("pOutdoor_Streedside_Frontdoor_Automatic_Switch",itemState)
            postUpdateIfChanged("pOutdoor_Carport_Automatic_Switch",itemState)
            postUpdateIfChanged("pOutdoor_Terrace_Automatic_Switch",itemState)
            postUpdateIfChanged("pOutdoor_Garden_Garage_Automatic_Switch",itemState)


# Individual MotionDetector Switchs
@rule("lights_outdoor.py")
class MotiondetectorOutdoorIndividualSwitchRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pOutdoor_Streedside_Garage_Automatic_Switch"),
            ItemCommandTrigger("pOutdoor_Streedside_Frontdoor_Automatic_Switch"),
            ItemCommandTrigger("pOutdoor_Carport_Automatic_Switch"),
            ItemCommandTrigger("pOutdoor_Terrace_Automatic_Switch"),
            ItemCommandTrigger("pOutdoor_Garden_Garage_Automatic_Switch")
        ]

    def execute(self, module, input):
        global ruleTimeouts
        now = ZonedDateTime.now()
        
        #last = ruleTimeouts.get("Motiondetector_Outdoor_Individual_Switches",0)
        #if now - last > 1000:
        ruleTimeouts["Motiondetector_Outdoor_Main_Switch"] = now
        ruleTimeouts["Light_Outdoor"] = now

        itemName = input['event'].getItemName()
        itemCommand = input['event'].getItemCommand()
        
        switchState = ON
        for i, entry in enumerate(manualMappings):
            if entry[1] == itemName:
                sendCommandIfChanged(entry[0],OFF)
                if itemCommand == OFF:
                    switchState = OFF
            else:
                if getItemState(entry[1]) == OFF:
                    switchState = OFF
                    
        # must be a command to inform physical knx switch
        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch",switchState)

        #self.log.info(u"{} {} {} {} {} ".format(gs,f,c,t,gg))
        
# Light Control Events
@rule("lights_outdoor.py")
class LightOutdoorControlRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Streedside_Garage_Light_Powered"),
            ItemStateChangeTrigger("pOutdoor_Streedside_Frontdoor_Light_Powered"),
            ItemStateChangeTrigger("pOutdoor_Carport_Light_Powered"),
            ItemStateChangeTrigger("pOutdoor_Terrace_Light_Brightness"),
            ItemStateChangeTrigger("pOutdoor_Garden_Garage_Light_Powered")
        ]

    def execute(self, module, input):
        #self.log.info(u"{}".format(input))
        
        global ruleTimeouts
        now = ZonedDateTime.now()
        last = ruleTimeouts.get("Light_Outdoor",0)
        
        # No Motion Detector related events
        if ChronoUnit.SECONDS.between(last,now) > 1:
            itemName = input['event'].getItemName()
        
            global timerMappings
            timer = timerMappings.get(itemName)
            if timer is not None:
                timer.cancel()
            
            for i, entry in enumerate(manualMappings):
                if entry[0] == itemName:
                    #ruleTimeouts["Motiondetector_Outdoor_Individual_Switches"] = now
                    if postUpdateIfChanged(entry[1],OFF):
                        ruleTimeouts["Motiondetector_Outdoor_Main_Switch"] = now
                        
                        # must be a command to inform physical knx switch
                        sendCommandIfChanged("pOutdoor_Light_Automatic_Main_Switch",OFF)
                    #self.log.info(u"{} {}".format(itemName,now-last))
                    break

# Motion Detector Events
@rule("lights_outdoor.py")
class MotionDetectorRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manualMappings):
            if entry[2] is not None:
                self.triggers.append(ItemStateChangeTrigger(entry[2],state="OPEN"))
                self.triggerMappings[entry[2]]=i

    def callback(self,entry):
        global timerMappings
        if getItemState(entry[1]) == ON:
            if getItemState(entry[2]) == OPEN:
                timerMappings[entry[0]] = startTimer(self.log, timerDuration, self.callback,[entry])
            else:
                global ruleTimeouts
                ruleTimeouts["Light_Outdoor"] = ZonedDateTime.now()

                sendCommand(entry[0],OFF)
                timerMappings[entry[0]] = None
        else:
            timerMappings[entry[0]] = None

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        entry = manualMappings[self.triggerMappings[itemName]]
        if getItemState("pOther_Automatic_State_Outdoorlights") == ON and getItemState(entry[1]) == ON:
            timerMappings[entry[0]] = startTimer(self.log, timerDuration, self.callback, [entry], oldTimer = timerMappings.get(entry[0]) )

            global ruleTimeouts
            ruleTimeouts["Light_Outdoor"] = ZonedDateTime.now()

            sendCommand(entry[0],ON)


# Terasse Motion Detector Events
@rule("lights_outdoor.py")
class TerasseMotionDetectorRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Terrace_Motiondetector_State1",state="OPEN"),
            ItemStateChangeTrigger("pOutdoor_Terrace_Motiondetector_State2",state="OPEN")
        ]

    def callback(self):
        global timerMappings
        if getItemState("pOutdoor_Terrace_Automatic_Switch") == ON:
            if getItemState("pOutdoor_Terrace_Motiondetector_State1") == OPEN or getItemState("pOutdoor_Terrace_Motiondetector_State2") == OPEN:
                timerMappings["pOutdoor_Terrace_Light_Brightness"] = startTimer(self.log, timerDuration, self.callback)
            else:
                global ruleTimeouts
                ruleTimeouts["Light_Outdoor"] = ZonedDateTime.now()

                sendCommand("pOutdoor_Terrace_Light_Brightness",0)
                timerMappings["pOutdoor_Terrace_Light_Brightness"] = None
        else:
            timerMappings["pOutdoor_Terrace_Light_Brightness"] = None

    def execute(self, module, input):
        if getItemState("pOther_Automatic_State_Outdoorlights") == ON and getItemState("pOutdoor_Terrace_Automatic_Switch") == ON:
            global timerMappings
            timerMappings["pOutdoor_Terrace_Light_Brightness"] = startTimer(self.log, timerDuration, self.callback, oldTimer = timerMappings.get("pOutdoor_Terrace_Light_Brightness") )

            global ruleTimeouts
            ruleTimeouts["Light_Outdoor"] = ZonedDateTime.now()

            sendCommand("pOutdoor_Terrace_Light_Brightness",100)
        
