import math

from marvin.helper import rule, createTimer, getNow, getGroupMember, getItemState, postUpdate, sendCommand, getItemLastUpdate
from core.triggers import ItemCommandTrigger

circuits = [
    [
        ['Watering_Streetside_Lawn', u"Strasse", 2.0 / 3.0],
        ['Watering_Gardenside_Lawn_right', u"Garten rechts", 1.00],
        ['Watering_Gardenside_Lawn_left', u"Garten links", 1.00]
    ], [
        ['Watering_Streetside_Beds']
    ], [
        ['Watering_Gardenside_Beds_front']
    ]
]

@rule("scenes_wathering.py")
class ScenesWatheringRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Watering_Program_Start")]

        self.progressTimer = None
        self.currentProgressMsg = ""

    def disableAllCircuits(self):
        for child in getGroupMember("Watering_Circuits"):
            sendCommand(child, OFF)
        postUpdate("Watering_Program_State", u"läuft nicht")

    def cancelProgressTimer(self):
        if self.progressTimer is not None:
            self.progressTimer.cancel()
        self.cleanProgressTimer()

    def cleanProgressTimer(self):
        self.progressTimer = None
        self.currentProgressMsg = ""
        
    def findStep(self):
        duration = getItemState("Watering_Program_Duration").intValue() * 60.0 * 1000.0
        
        remaining = 0
        activeStep = None

        if getItemState("Watering_Circuits") == OFF:
            for loop in circuits:
                #self.log.info("start " + loop[0][0])
                sendCommand(loop[0][0], ON)
            activeStep = circuits[0][0]
            remaining = ( duration * activeStep[2] )
        else:
            activeIndex = -1
            for i in range(len(circuits[0])):
                step = circuits[0][i]
                if getItemState(step[0]) == ON:
                    activeIndex = i
                    activeStep = step
                    break
            
            if activeStep != None:
                runtime = getNow().getMillis() - getItemLastUpdate(activeStep[0]).getMillis()
                
                remaining = ( duration * activeStep[2] ) - runtime
                
                if remaining <= 0:
                    activeIndex += 1
                    if activeIndex < len(circuits[0]):
                        #self.log.info("next " + circuits[0][activeIndex][0])
                        sendCommand(circuits[0][activeIndex][0], ON)
                        sendCommand(activeStep[0], OFF)
                        activeStep = circuits[0][activeIndex]
                        remaining = ( duration * activeStep[2] )
                    else:
                        activeStep = None
                        #self.log.info("finish")
                        self.disableAllCircuits()
                        postUpdate("Watering_Program_Start", OFF)
            
        return [ activeStep[1] if activeStep != None else u"", remaining ]

    def callbackProgress(self):
        if self.progressTimer is not None and self.currentProgressMsg != getItemState("Watering_Program_State").toString():
            self.log.info("Cancel Watering Progress Zombie Timer")
            self.cleanProgressTimer()
            return
        
        msg, remaining = self.findStep()
        
        if remaining <= 0:
            self.cleanProgressTimer()
            return
        
        remainingInMinutes = int( math.floor( round( remaining / 1000.0 ) / 60.0 ) )

        if remainingInMinutes > 0:
            msg = u"{} noch {} min".format(msg, remainingInMinutes )
        else:
            msg = u"{} gleich fertig".format(msg)

        self.currentProgressMsg = msg
        postUpdate("Watering_Program_State", self.currentProgressMsg)

        self.progressTimer = createTimer(60.0, self.callbackProgress)
        self.progressTimer.start()

    def execute(self, module, input):
        self.cancelProgressTimer()

        if input["command"] == OFF:
            self.disableAllCircuits()
        else:
            self.callbackProgress()

