import time

from marvin.helper import rule, createTimer, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged, getNow
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
controlTimestamps = {}

# Main MotionDetector Switch
@rule("lights_outdoor_control.py")
class MotiondetectorOutdoorSwitchRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Motiondetector_Outdoor_Switch")]

    def execute(self, module, input):
        if input["command"] == ON:
            global controlTimestamps
            now = getNow().getMillis()

            # Switch OFF Manual lights and maybe trigger a MotioncontrollSwitch update
            sendCommand("Light_Outdoor_Garage_Streedside",OFF)
            controlTimestamps["Light_Outdoor_Garage_Streedside"] = now

            sendCommand("Light_Outdoor_Frontdoor",OFF)
            controlTimestamps["Light_Outdoor_Frontdoor"] = now

            sendCommand("Light_Outdoor_Carport",OFF)
            controlTimestamps["Light_Outdoor_Carport"] = now

            sendCommand("Light_Outdoor_Terrace",0)
            controlTimestamps["Light_Outdoor_Terrace"] = now

            sendCommand("Light_Outdoor_Garage_Gardenside",OFF)
            controlTimestamps["Light_Outdoor_Garage_Gardenside"] = now

            postUpdate("Motiondetector_Outdoor_Garage_Streetside_Switch",ON)
            postUpdate("Motiondetector_Outdoor_Frontdoor_Switch",ON)
            postUpdate("Motiondetector_Outdoor_Carport_Switch",ON)
            postUpdate("Motiondetector_Outdoor_Terrace_Switch",ON)
            postUpdate("Motiondetector_Outdoor_Garage_Gardenside_Switch",ON)
        else:
            postUpdate("Motiondetector_Outdoor_Garage_Streetside_Switch",OFF)
            postUpdate("Motiondetector_Outdoor_Frontdoor_Switch",OFF)
            postUpdate("Motiondetector_Outdoor_Carport_Switch",OFF)
            postUpdate("Motiondetector_Outdoor_Terrace_Switch",OFF)
            postUpdate("Motiondetector_Outdoor_Garage_Gardenside_Switch",OFF)


# Individual MotionDetector Switchs
@rule("lights_outdoor_control.py")
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
        global controlTimestamps
        now = getNow().getMillis()
        
        itemName = input['event'].getItemName()
        itemCommand = input['event'].getItemCommand()
        
        if itemName == "Motiondetector_Outdoor_Garage_Streetside_Switch":
            gs = itemCommand
            sendCommand("Light_Outdoor_Garage_Streedside",OFF)
            controlTimestamps["Light_Outdoor_Garage_Streedside"] = now
        else:
            gs = getItemState("Motiondetector_Outdoor_Garage_Streetside_Switch")
            
        if itemName == "Motiondetector_Outdoor_Frontdoor_Switch":
            f = itemCommand
            sendCommand("Light_Outdoor_Frontdoor",OFF)
            controlTimestamps["Light_Outdoor_Frontdoor"] = now
        else:
            f = getItemState("Motiondetector_Outdoor_Frontdoor_Switch")

        if itemName == "Motiondetector_Outdoor_Carport_Switch":
            c = itemCommand
            sendCommand("Light_Outdoor_Carport",OFF)
            controlTimestamps["Light_Outdoor_Carport"] = now
        else:
            c = getItemState("Motiondetector_Outdoor_Carport_Switch")

        if itemName == "Motiondetector_Outdoor_Terrace_Switch":
            t = itemCommand
            sendCommand("Light_Outdoor_Terrace",0)
            controlTimestamps["Light_Outdoor_Terrace"] = now
        else:
            t = getItemState("Motiondetector_Outdoor_Terrace_Switch")

        if itemName == "Motiondetector_Outdoor_Garage_Gardenside_Switch":
            gg = itemCommand
            sendCommand("Light_Outdoor_Garage_Gardenside",OFF)
            controlTimestamps["Light_Outdoor_Garage_Gardenside"] = now
        else:
            gg = getItemState("Motiondetector_Outdoor_Garage_Gardenside_Switch")
        
        #self.logInfo("test","B "+receivedCommand)
        if gs == OFF or f == OFF or c == OFF or t == OFF or gg == OFF:
            postUpdateIfChanged("Motiondetector_Outdoor_Switch",OFF)
        else:
            postUpdateIfChanged("Motiondetector_Outdoor_Switch",ON)

# Motion Detector Events
@rule("lights_outdoor_control.py")
class MotionDetectorRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manualMappings):
            if entry[2] is not None:
                self.triggers.append(ItemStateChangeTrigger(entry[2],"OPEN"))
                self.triggerMappings[entry[2]]=i

    def callback(self,entry):
        global timerMappings
        if getItemState(entry[1]) == ON:
            if getItemState(entry[2]) == OPEN:
                timerMappings[entry[0]] = createTimer(timerDuration, self.callback,[entry])
                timerMappings[entry[0]].start()
            else:
                sendCommand(entry[0],OFF)
                timerMappings[entry[0]] = None

                global controlTimestamps
                now = getNow().getMillis()
                controlTimestamps[entry[0]] = now
        else:
            timerMappings[entry[0]] = None

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        entry = manualMappings[self.triggerMappings[itemName]]
        if getItemState("State_Outdoorlights") == ON and getItemState(entry[1]) == ON:
            if timerMappings.get(entry[0]) is not None:
                timerMappings[entry[0]].cancel()
            timerMappings[entry[0]] = createTimer(timerDuration, self.callback, [entry] )
            timerMappings[entry[0]].start()

            sendCommand(entry[0],ON)

            global controlTimestamps
            now = getNow().getMillis()
            controlTimestamps[entry[0]] = now


# Terasse Motion Detector Events
@rule("lights_outdoor_control.py")
class TerasseMotionDetectorRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace1","OPEN"),
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace2","OPEN")
        ]

    def callback(self):
        global timerMappings
        if getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON:
            if getItemState("Motiondetector_Outdoor_Terrace1") == OPEN or getItemState("Motiondetector_Outdoor_Terrace2") == OPEN:
                timerMappings["Light_Outdoor_Terrace"] = createTimer(timerDuration, self.callback)
                timerMappings["Light_Outdoor_Terrace"].start()
            else:
                sendCommand("Light_Outdoor_Terrace",0)
                timerMappings["Light_Outdoor_Terrace"] = None

                global controlTimestamps
                now = getNow().getMillis()
                controlTimestamps["Light_Outdoor_Terrace"] = now
        else:
            timerMappings["Light_Outdoor_Terrace"] = None

    def execute(self, module, input):
        if getItemState("State_Outdoorlights") == ON and getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON:
            global timerMappings
            if timerMappings.get("Light_Outdoor_Terrace") is not None:
                timerMappings["Light_Outdoor_Terrace"].cancel()
            timerMappings["Light_Outdoor_Terrace"] = createTimer(timerDuration, self.callback )
            timerMappings["Light_Outdoor_Terrace"].start()

            sendCommand("Light_Outdoor_Terrace",100)
            global controlTimestamps
            now = getNow().getMillis()
            controlTimestamps["Light_Outdoor_Terrace"] = now

# Light Control Events
@rule("lights_outdoor_control.py")
class LightOutdoorControlRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Light_Outdoor_Garage_Streedside"),
            ItemCommandTrigger("Light_Outdoor_Frontdoor"),
            ItemCommandTrigger("Light_Outdoor_Carport"),
            ItemCommandTrigger("Light_Outdoor_Terrace"),
            ItemCommandTrigger("Light_Outdoor_Garage_Gardenside")
        ]

    def execute(self, module, input):
        #self.log.info(u"{}".format(input))
        
        itemName = input['event'].getItemName()
        
        global controlTimestamps
        now = getNow().getMillis()
        last = controlTimestamps.get(itemName,0)
        
        # No Motion Detector related events
        if now - last > 1000:
            global timerMappings
            timer = timerMappings.get(itemName)
            if timer is not None:
                timer.cancel()
            
            for i, entry in enumerate(manualMappings):
                if entry[0] == itemName:
                    postUpdateIfChanged("Motiondetector_Outdoor_Switch",OFF)
                    postUpdateIfChanged(entry[1],OFF)
                    #self.log.info(u"{} {}".format(itemName,now-last))
                    break
        
