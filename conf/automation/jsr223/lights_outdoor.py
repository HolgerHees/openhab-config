import time

from custom.helper import rule, createTimer, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getNow
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger

manualMappings = [
    ["Light_Outdoor_Frontdoor", "Motiondetector_Outdoor_Frontdoor_Switch","Motiondetector_Outdoor_Frontdoor"],
    ["Light_Outdoor_Carport", "Motiondetector_Outdoor_Carport_Switch","Motiondetector_Outdoor_Carport"],
    ["Light_Outdoor_Terrace", "Motiondetector_Outdoor_Terrace_Switch",None],
    ["Light_Outdoor_Garage_Streedside", "Motiondetector_Outdoor_Garage_Streetside_Switch","Motiondetector_Outdoor_Garage_Streetside"],
    ["Light_Outdoor_Garage_Gardenside", "Motiondetector_Outdoor_Garage_Gardenside_Switch","Motiondetector_Outdoor_Garage_Gardenside"]
]

timerDuration = 60.0
timerMappings = {}
ruleTimeouts = {}

# Main MotionDetector Switch
@rule("lights_outdoor.py")
class MotiondetectorOutdoorSwitchRule:
    def __init__(self):
        # must be a stateChange trigger to get also events from physical knx buttons
        self.triggers = [ItemStateChangeTrigger("Motiondetector_Outdoor_Switch")]

    def execute(self, module, input):
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Motiondetector_Outdoor_Main_Switch",0)
        
        if now - last > 1000:
            itemState = input["event"].getItemState()
            
            if itemState == ON:
                ruleTimeouts["Light_Outdoor"] = now

                sendCommandIfChanged("Light_Outdoor_Garage_Streedside",OFF)
                sendCommandIfChanged("Light_Outdoor_Frontdoor",OFF)
                sendCommandIfChanged("Light_Outdoor_Carport",OFF)
                sendCommandIfChanged("Light_Outdoor_Terrace",0)
                sendCommandIfChanged("Light_Outdoor_Garage_Gardenside",OFF)

            #ruleTimeouts["Motiondetector_Outdoor_Individual_Switches"] = now
            postUpdateIfChanged("Motiondetector_Outdoor_Garage_Streetside_Switch",itemState)
            postUpdateIfChanged("Motiondetector_Outdoor_Frontdoor_Switch",itemState)
            postUpdateIfChanged("Motiondetector_Outdoor_Carport_Switch",itemState)
            postUpdateIfChanged("Motiondetector_Outdoor_Terrace_Switch",itemState)
            postUpdateIfChanged("Motiondetector_Outdoor_Garage_Gardenside_Switch",itemState)


# Individual MotionDetector Switchs
@rule("lights_outdoor.py")
class MotiondetectorOutdoorIndividualSwitchRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Motiondetector_Outdoor_Garage_Streetside_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Frontdoor_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Carport_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Terrace_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Garage_Gardenside_Switch")
        ]

    def execute(self, module, input):
        global ruleTimeouts
        now = getNow().getMillis()
        
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
        sendCommandIfChanged("Motiondetector_Outdoor_Switch",switchState)

        #self.log.info(u"{} {} {} {} {} ".format(gs,f,c,t,gg))
        
# Light Control Events
@rule("lights_outdoor.py")
class LightOutdoorControlRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Light_Outdoor_Garage_Streedside"),
            ItemStateChangeTrigger("Light_Outdoor_Frontdoor"),
            ItemStateChangeTrigger("Light_Outdoor_Carport"),
            ItemStateChangeTrigger("Light_Outdoor_Terrace"),
            ItemStateChangeTrigger("Light_Outdoor_Garage_Gardenside")
        ]

    def execute(self, module, input):
        #self.log.info(u"{}".format(input))
        
        global ruleTimeouts
        now = getNow().getMillis()
        last = ruleTimeouts.get("Light_Outdoor",0)
        
        # No Motion Detector related events
        if now - last > 1000:
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
                        sendCommandIfChanged("Motiondetector_Outdoor_Switch",OFF)
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
                timerMappings[entry[0]] = createTimer(self.log, timerDuration, self.callback,[entry])
                timerMappings[entry[0]].start()
            else:
                global ruleTimeouts
                ruleTimeouts["Light_Outdoor"] = getNow().getMillis()

                sendCommand(entry[0],OFF)
                timerMappings[entry[0]] = None
        else:
            timerMappings[entry[0]] = None

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        entry = manualMappings[self.triggerMappings[itemName]]
        if getItemState("State_Outdoorlights") == ON and getItemState(entry[1]) == ON:
            if timerMappings.get(entry[0]) is not None:
                timerMappings[entry[0]].cancel()
            timerMappings[entry[0]] = createTimer(self.log, timerDuration, self.callback, [entry] )
            timerMappings[entry[0]].start()

            global ruleTimeouts
            ruleTimeouts["Light_Outdoor"] = getNow().getMillis()

            sendCommand(entry[0],ON)


# Terasse Motion Detector Events
@rule("lights_outdoor.py")
class TerasseMotionDetectorRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace1",state="OPEN"),
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace2",state="OPEN")
        ]

    def callback(self):
        global timerMappings
        if getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON:
            if getItemState("Motiondetector_Outdoor_Terrace1") == OPEN or getItemState("Motiondetector_Outdoor_Terrace2") == OPEN:
                timerMappings["Light_Outdoor_Terrace"] = createTimer(self.log, timerDuration, self.callback)
                timerMappings["Light_Outdoor_Terrace"].start()
            else:
                global ruleTimeouts
                ruleTimeouts["Light_Outdoor"] = getNow().getMillis()

                sendCommand("Light_Outdoor_Terrace",0)
                timerMappings["Light_Outdoor_Terrace"] = None
        else:
            timerMappings["Light_Outdoor_Terrace"] = None

    def execute(self, module, input):
        if getItemState("State_Outdoorlights") == ON and getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON:
            global timerMappings
            if timerMappings.get("Light_Outdoor_Terrace") is not None:
                timerMappings["Light_Outdoor_Terrace"].cancel()
            timerMappings["Light_Outdoor_Terrace"] = createTimer(self.log, timerDuration, self.callback )
            timerMappings["Light_Outdoor_Terrace"].start()

            global ruleTimeouts
            ruleTimeouts["Light_Outdoor"] = getNow().getMillis()

            sendCommand("Light_Outdoor_Terrace",100)
        
