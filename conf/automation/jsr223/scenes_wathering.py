import math

from custom.helper import rule, createTimer, getNow, getGroupMember, getItemState, postUpdate, sendCommand, getItemLastChange
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger

circuits = [
    [
      2.0 / 3.0,
      u"Strasse",
      [
        'Watering_Streetside_Lawn'
      ]
    ],[
      1.0,
      u"Beete",
      [
        'Watering_Streetside_Beds',
        'Watering_Gardenside_Beds_front',
        'Watering_Gardenside_Beds_back'
      ]
    ],[
      1.0,
      u"Garten rechts",
      [
        'Watering_Gardenside_Lawn_right'
      ]
    ],[
      1.0,
      u"Garten links",
      [
        'Watering_Gardenside_Lawn_left'
      ]
    ]
]
      
#circuits = [
#    [
#        ['Watering_Streetside_Lawn', u"Strasse", 2.0 / 3.0 ],
#        ['Watering_Gardenside_Lawn_right', u"Garten rechts", 1.0 ],
#        ['Watering_Gardenside_Lawn_left', u"Garten links", 1.0 ]
#    ], [
#        ['Watering_Streetside_Beds', u"Beete", 1.0 ]
#    ], [
#        ['Watering_Gardenside_Beds_front', u"Beete", 1.0 ]
#    ], [
#        ['Watering_Gardenside_Beds_back', u"Beete", 1.0 ]
#    ]
#]
    
@rule("scenes_wathering.py")
class ScenesWatheringRule():
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("Watering_Program_Duration") ]
        
        for group in circuits:
            for circuit in group[2]:
                self.triggers.append(ItemStateChangeTrigger(circuit+"_Auto"))

    def execute(self, module, input):
        reference_duration = getItemState("Watering_Program_Duration").intValue()

        for i in range(len(circuits)):
            for circuit in circuits[i][2]:
                if getItemState(circuit + "_Auto") == ON:
                    duration = ( circuits[i][0] * reference_duration )
                    duration = int( math.floor( duration ) )

                    postUpdate(circuit + "_Info", u"{} min.".format(duration))
                else:
                    postUpdate(circuit + "_Info", u"inaktiv")

class WatheringHelper:
    def getReferenceGroup(self):
        referenceGroup = -1
        for i in range(len(circuits)):
            for circuit in circuits[i][1]:
                if getItemState(circuit[0] + "_Auto") == ON:
                    referenceGroup = i
                    break
                  
            if referenceGroup != -1:
                break
        return referenceGroup

class WatheringHelperOld:
    def getReferenceGroup(self):
        referenceGroup = -1
        for i in range(len(circuits)):
            for circuit in circuits[i]:
                if getItemState(circuit[0] + "_Auto") == ON:
                    referenceGroup = i
                    break
                  
            if referenceGroup != -1:
                break
        return referenceGroup

@rule("scenes_wathering.py")
class ScenesWatheringRule(WatheringHelperOld):
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

        # detect current active index
        activeIndex = -1
        for i in range(len(circuits)):
            group = circuits[i]
            if getItemState(group[2][0]) == ON:
                activeIndex = i
                runtime = getNow().getMillis() - getItemLastChange(group[2][0]).getMillis()
                remaining = ( duration * group[0] ) - runtime
                break

        if remaining <= 0:
            nextIndex = -1

            # detect next index
            for i in range(len(circuits)):
                if activeIndex != -1 and i <= activeIndex:
                    continue;
                group = circuits[i]
                for circuit in group[2]:
                    if getItemState(circuit + "_Auto") == ON:
                        nextIndex = i;
                        break
                if nextIndex != -1:
                    break
        
            if nextIndex == -1:
                self.disableAllCircuits()
                postUpdate("Watering_Program_Start", OFF)
            else:
                for circuit in circuits[nextIndex][2]:
                    if getItemState(circuit + "_Auto") == ON:
                        sendCommand(circuit, ON)
                
                nextGroup = circuits[nextIndex]

                remaining = ( duration * nextGroup[0] )
                info = nextGroup[1]

                # deactivate current index
                if activeIndex != -1:
                    for circuit in circuits[activeIndex][2]:
                        sendCommand(circuit, OFF)
        else:
            info = circuits[activeIndex][1]
        
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

        self.progressTimer = createTimer(self.log, 60.0, self.callbackProgress)
        self.progressTimer.start()

    def execute(self, module, input):
        self.cancelProgressTimer()

        if input["command"] == OFF:
            self.disableAllCircuits()
        else:
            self.callbackProgress()

