import time

from marvin.helper import rule, createTimer, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendCommandIfChanged
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger

manualMappings = [
    ["Light_Outdoor_Frontdoor_Manual","Light_Outdoor_Frontdoor", "Motiondetector_Outdoor_Frontdoor_Switch","Motiondetector_Outdoor_Frontdoor"],
    ["Light_Outdoor_Carport_Manual","Light_Outdoor_Carport", "Motiondetector_Outdoor_Carport_Switch","Motiondetector_Outdoor_Carport"],
    ["Light_Outdoor_Terrace_Manual","Light_Outdoor_Terrace", "Motiondetector_Outdoor_Terrace_Switch",None],
    ["Light_Outdoor_Garage_Streedside_Manual","Light_Outdoor_Garage_Streedside", "Motiondetector_Outdoor_Garage_Streetside_Switch","Motiondetector_Outdoor_Garage_Streetside"],
    ["Light_Outdoor_Garage_Gardenside_Manual","Light_Outdoor_Garage_Gardenside", "Motiondetector_Outdoor_Garage_Gardenside_Switch","Motiondetector_Outdoor_Garage_Gardenside"]
]

timerDuration = 60.0
timerMappings = {}

@rule("lights_outdoor_control.py")
class MotiondetectorOutdoorSwitchRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Motiondetector_Outdoor_Switch")]

    def execute(self, module, input):
        if input["command"] == ON:
            # Switch OFF Manual lights and maybe trigger a MotioncontrollSwitch update
            sendCommand("Light_Outdoor_Garage_Streedside_Manual",OFF)
            sendCommand("Light_Outdoor_Frontdoor_Manual",OFF)
            sendCommand("Light_Outdoor_Carport_Manual",OFF)
            sendCommand("Light_Outdoor_Terrace_Manual",0)
            sendCommand("Light_Outdoor_Garage_Gardenside_Manual",OFF)

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


@rule("lights_outdoor_control.py")
class MotiondetectorOutdoorDetailSwitchRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Motiondetector_Outdoor_Garage_Streetside_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Frontdoor_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Carport_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Terrace_Switch"),
            ItemCommandTrigger("Motiondetector_Outdoor_Garage_Gardenside_Switch")
        ]

    def execute(self, module, input):
        # Wait until received command has updatet item state
        time.sleep(1)

        #self.logInfo("test","B "+receivedCommand)
        if getItemState("Motiondetector_Outdoor_Garage_Streetside_Switch") == OFF \
           or \
           getItemState("Motiondetector_Outdoor_Frontdoor_Switch") == OFF \
           or \
           getItemState("Motiondetector_Outdoor_Carport_Switch") == OFF \
           or \
           getItemState("Motiondetector_Outdoor_Terrace_Switch") == OFF \
           or \
           getItemState("Motiondetector_Outdoor_Garage_Gardenside_Switch") == OFF:
            postUpdateIfChanged("Motiondetector_Outdoor_Switch",OFF)
        else:
            postUpdateIfChanged("Motiondetector_Outdoor_Switch",ON)


@rule("lights_outdoor_control.py")
class ManualRule:
    def __init__(self):
        global timerMappings
        self.triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manualMappings):
            timerMappings[entry[0]] = None
            self.triggers.append(ItemCommandTrigger(entry[0]))
            self.triggerMappings[entry[0]]=i

    def forwardManualLightControl( self, timer, rawLight, motionDetectorSwitch, receivedCommand ):
        if timer is not None:
            timer.cancel()

        #self.log.info("forwardManualLightControl " + str(receivedCommand) )
        #self.log.info("rawLight " + str(rawLight) )

        sendCommand(rawLight,receivedCommand)

        # Wait until received command has updatet item state
        time.sleep(1)

        #self.log.info("1 "+receivedCommand)
        #self.log.info("2 "+motionDetectorSwitch.state)
        #self.log.info("3 " + (receivedCommand == OFF))
        #self.log.info("4 " + (motionDetectorSwitch.state == OFF))

        if receivedCommand == OFF or receivedCommand == PercentType.ZERO:
            #self.log.info("A0 " + (motionDetectorSwitch.state == OFF))

            # don't enable motion detector autmatically if we switch off a outdoor light manually
            #sendCommandIfChanged(motionDetectorSwitch,ON)
            pass
        else:
            #self.log.info("B0 " + (motionDetectorSwitch.state == OFF))
            sendCommandIfChanged(motionDetectorSwitch,OFF)

        return None

    def execute(self, module, input):
        global timerMappings
        itemName = input['event'].getItemName()
        entry = manualMappings[self.triggerMappings[itemName]]
        timerMappings[entry[0]] = self.forwardManualLightControl( timerMappings[entry[0]], entry[1], entry[2], input["command"] )


@rule("lights_outdoor_control.py")
class AutoRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manualMappings):
            self.triggers.append(ItemCommandTrigger(entry[2]))
            self.triggerMappings[entry[2]]=i

    def forwardEnableMotionLightControl( self, manualControlSwitch, receivedCommand):

        #self.log.info("test","forwardEnableMotionLightControl "+manualControlSwitch.state)

        # Wait until received command has updatet item state
        time.sleep(1)

        if receivedCommand == ON:
            sendCommandIfChanged(manualControlSwitch,OFF)

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        entry = manualMappings[self.triggerMappings[itemName]]
        self.forwardEnableMotionLightControl( entry[0], input["command"] )


@rule("lights_outdoor_control.py")
class MotionDetectorRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        for i, entry in enumerate(manualMappings):
            if entry[3] is not None:
                self.triggers.append(ItemStateChangeTrigger(entry[3],"OPEN"))
                self.triggerMappings[entry[3]]=i

    def callback(self,entry):
        global timerMappings
        if getItemState(entry[2]) == ON and getItemState(entry[0]) == OFF:
            if getItemState(entry[3]) == OPEN:
                timerMappings[entry[0]] = createTimer(timerDuration, self.callback,[entry])
                timerMappings[entry[0]].start()
            else:
                sendCommand(entry[1],OFF)
                timerMappings[entry[0]] = None
        else:
            timerMappings[entry[0]] = None

    def execute(self, module, input):
        itemName = input['event'].getItemName()
        
        entry = manualMappings[self.triggerMappings[itemName]]
        if getItemState(entry[2]) == ON and getItemState(entry[0]) == OFF:
        #if getItemState("State_Outdoorlights") == ON and getItemState(entry[2]) == ON and getItemState(entry[0]) == OFF:
            if timerMappings[entry[0]] is not None:
                timerMappings[entry[0]].cancel()
            timerMappings[entry[0]] = createTimer(timerDuration, self.callback, [entry] )
            timerMappings[entry[0]].start()
            sendCommand(entry[1],ON)


@rule("lights_outdoor_control.py")
class TerraceManualKnxRule:
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("Light_Outdoor_Terrace","ON"),
            ItemCommandTrigger("Light_Outdoor_Terrace","OFF")
        ]

    def execute(self, module, input):
        #self.log.info("test","Light_Outdoor_Terrace " + receivedCommand )

        if timerMappings["Light_Outdoor_Terrace_Manual"] is not None:
            timerMappings["Light_Outdoor_Terrace_Manual"].cancel()

        # Wait until received command has updatet item state
        time.sleep(1)

        if input["command"] == OFF:
            if getItemState("Light_Outdoor_Terrace_Manual") != 0 or getItemState("Light_Outdoor_Terrace_Manual") != OFF:
                postUpdate("Light_Outdoor_Terrace_Manual", OFF )

            # don't enable motion detector autmatically if we switch off a outdoor light manually
            #sendCommandIfChanged("Motiondetector_Outdoor_Terrace_Switch",ON)
        else:
            if getItemState("Light_Outdoor_Terrace_Manual") == PercentType.ZERO or getItemState("Light_Outdoor_Terrace_Manual") == OFF:
                postUpdate("Light_Outdoor_Terrace_Manual", ON )

            sendCommandIfChanged("Motiondetector_Outdoor_Terrace_Switch",OFF)


@rule("lights_outdoor_control.py")
class TerasseMotionDetectorRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace1","OPEN"),
            ItemStateChangeTrigger("Motiondetector_Outdoor_Terrace2","OPEN")
        ]

    def callback(self):
        global timerMappings
        if getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON and ( getItemState("Light_Outdoor_Terrace_Manual") == OFF or getItemState("Light_Outdoor_Terrace_Manual") == PercentType.ZERO ):
            if getItemState("Motiondetector_Outdoor_Terrace1") == OPEN or getItemState("Motiondetector_Outdoor_Terrace2") == OPEN:
                timerMappings["Light_Outdoor_Terrace_Manual"] = createTimer(timerDuration, self.callback)
                timerMappings["Light_Outdoor_Terrace_Manual"].start()
            else:
                sendCommand("Light_Outdoor_Terrace",0)
                timerMappings["Light_Outdoor_Terrace_Manual"] = None
        else:
            timerMappings["Light_Outdoor_Terrace_Manual"] = None

    def execute(self, module, input):
        if getItemState("State_Outdoorlights") == ON and getItemState("Motiondetector_Outdoor_Terrace_Switch") == ON and ( getItemState("Light_Outdoor_Terrace_Manual") == OFF or getItemState("Light_Outdoor_Terrace_Manual") == PercentType.ZERO ):
            global timerMappings
            if timerMappings["Light_Outdoor_Terrace_Manual"] is not None:
                timerMappings["Light_Outdoor_Terrace_Manual"].cancel()
            timerMappings["Light_Outdoor_Terrace_Manual"] = createTimer(timerDuration, self.callback )
            timerMappings["Light_Outdoor_Terrace_Manual"].start()
            sendCommand("Light_Outdoor_Terrace",100)
