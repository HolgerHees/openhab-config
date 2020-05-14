import math

from custom.helper import rule, createTimer, getNow, getGroupMember, getItemState, postUpdate, sendCommand, getItemLastUpdate
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger

circuits = [
    [
        ['Watering_Streetside_Lawn', u"Strasse", 2.0 / 3.0 ],
        ['Watering_Gardenside_Lawn_right', u"Garten rechts", 1.0 ],
        ['Watering_Gardenside_Lawn_left', u"Garten links", 1.0 ]
    ], [
        ['Watering_Streetside_Beds', u"Beete", 1.0 ]
    ], [
        ['Watering_Gardenside_Beds_front', u"Beete", 1.0 ]
    ]
]

@rule("scenes_wathering.py")
class ScenesWatheringRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Watering_Streetside_Lawn_Auto"),
            ItemStateChangeTrigger("Watering_Gardenside_Lawn_right_Auto"),
            ItemStateChangeTrigger("Watering_Gardenside_Lawn_left_Auto"),
            ItemStateChangeTrigger("Watering_Gardenside_Beds_front_Auto"),
            ItemStateChangeTrigger("Watering_Streetside_Beds_Auto"),
            ItemStateChangeTrigger("Watering_Gardenside_Beds_back_Auto"),
            ItemStateChangeTrigger("Watering_Program_Duration")
        ]

    def execute(self, module, input):
        reference_duration = getItemState("Watering_Program_Duration").intValue()

        total = 0
        for loop in circuits[0]:            
            if getItemState(loop[0] + "_Auto") == ON:
                duration = int( math.floor( loop[2] * reference_duration ) )
                total = total + duration
            
                postUpdate(loop[0] + "_Info", u"{} min.".format(duration))
            else:
                postUpdate(loop[0] + "_Info", u"inaktiv")
                
        if total == 0:
            total = reference_duration
        
        if getItemState("Watering_Gardenside_Beds_front_Auto") == ON:
            postUpdate("Watering_Gardenside_Beds_front_Info", u"{} min.".format(total))
        else:
            postUpdate("Watering_Gardenside_Beds_front_Info", u"inaktiv")
        
        if getItemState("Watering_Streetside_Beds_Auto") == ON:
            postUpdate("Watering_Streetside_Beds_Info", u"{} min.".format(total))
        else:
            postUpdate("Watering_Streetside_Beds_Info", u"inaktiv")

        if getItemState("Watering_Gardenside_Beds_back_Auto") == ON:
            postUpdate("Watering_Gardenside_Beds_back_Info", u"{} min.".format(total))
        else:
            postUpdate("Watering_Gardenside_Beds_back_Info", u"inaktiv")

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
        info = u""
            
        if getItemState("Watering_Circuits") == OFF:
            for group in circuits:
                #self.log.info("start " + loop[0][0])
                for circuit in group:
                    if getItemState(circuit[0] + "_Auto") == ON:
                        sendCommand(circuit[0], ON)

                        if remaining == 0:
                            remaining = ( duration * circuit[2] )
                            info = circuit[1]
                        break
                      
        else:
            referenceGroup = -1
            for i in range(len(circuits)):
                for circuit in circuits[i]:
                    if getItemState(circuit[0] + "_Auto") == ON:
                        referenceGroup = i
                        break
                      
                if referenceGroup != -1:
                    break
                    
            activeIndex = -1
            activeStep = None
            for i in range(len(circuits[referenceGroup])):
                step = circuits[referenceGroup][i]
                
                if getItemState(step[0]) == ON:
                    activeIndex = i
                    activeStep = step
                    break

            if activeStep != None:
                runtime = getNow().getMillis() - getItemLastUpdate(activeStep[0]).getMillis()
                
                remaining = ( duration * activeStep[2] ) - runtime
                if remaining <= 0:
                    activeIndex += 1
                    if activeIndex < len(circuits[referenceGroup]):
                        sendCommand(circuits[referenceGroup][activeIndex][0], ON)
                        sendCommand(activeStep[0], OFF)

                        activeStep = circuits[referenceGroup][activeIndex]

                        remaining = ( duration * activeStep[2] )
                        info = activeStep[1]
                    else:
                        #self.log.info("finish")
                        self.disableAllCircuits()
                        postUpdate("Watering_Program_Start", OFF)

        return [ info, remaining ]

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

