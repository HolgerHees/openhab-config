import math
from java.time import ZonedDateTime

from shared.helper import rule, createTimer, getGroupMember, getItemState, postUpdate, sendCommand, getItemLastChange
from core.triggers import ItemCommandTrigger, ItemStateChangeTrigger

circuits = [
    [
      2.0 / 3.0,
      u"Strasse",
      [
        'pOutdoor_Streetside_Lawn_Watering'
      ]
    ],[
      1.0,
      u"Beete",
      [
        'pOutdoor_Streetside_Beds_Watering',
        'pOutdoor_Terrace_Watering',
        'pOutdoor_Garden_Back_Watering'
      ]
    ],[
      1.0,
      u"Garten rechts",
      [
        'pOutdoor_Garden_Right_Watering'
      ]
    ],[
      1.0,
      u"Garten links",
      [
        'pOutdoor_Garden_Left_Watering'
      ]
    ]
]
      
#circuits = [
#    [
#        ['pOutdoor_Streetside_Lawn_Watering_Powered', u"Strasse", 2.0 / 3.0 ],
#        ['pOutdoor_Garden_Right_Watering_Powered', u"Garten rechts", 1.0 ],
#        ['pOutdoor_Garden_Left_Watering_Powered', u"Garten links", 1.0 ]
#    ], [
#        ['pOutdoor_Streetside_Beds_Watering_Powered', u"Beete", 1.0 ]
#    ], [
#        ['pOutdoor_Terrace_Watering_Powered', u"Beete", 1.0 ]
#    ], [
#        ['pOutdoor_Garden_Back_Watering_Powered', u"Beete", 1.0 ]
#    ]
#]
    
@rule("scenes_wathering.py")
class ScenesWatheringRule():
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_Duration") ]
        
        for group in circuits:
            for circuit in group[2]:
                self.triggers.append(ItemStateChangeTrigger(circuit+"_Auto"))

    def execute(self, module, input):
        reference_duration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

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
        self.triggers = [ItemCommandTrigger("pOutdoor_Watering_Logic_Program_Start")]

        self.progressTimer = None
        self.currentProgressMsg = ""

    def disableAllCircuits(self):
        for child in getGroupMember("gOutdoor_Watering_Circuits"):
            sendCommand(child, OFF)
        postUpdate("pOutdoor_Watering_Logic_Program_State", u"läuft nicht")

    def cancelProgressTimer(self):
        if self.progressTimer is not None:
            self.progressTimer.cancel()
        self.cleanProgressTimer()

    def cleanProgressTimer(self):
        self.progressTimer = None
        self.currentProgressMsg = ""
        
    def findStep(self):
        duration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue() * 60.0 * 1000.0
        
        remaining = 0
        info = u""

        # detect current active index
        activeIndex = -1
        for i in range(len(circuits)):
            group = circuits[i]
            if getItemState(group[2][0] + "_Powered") == ON:
                activeIndex = i
                runtime = ZonedDateTime.now().toInstant().toEpochMilli() - getItemLastChange(group[2][0] + "_Powered").toInstant().toEpochMilli()
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
                postUpdate("pOutdoor_Watering_Logic_Program_Start", OFF)
            else:
                for circuit in circuits[nextIndex][2]:
                    if getItemState(circuit + "_Auto") == ON:
                        sendCommand(circuit + "_Powered", ON)
                
                nextGroup = circuits[nextIndex]

                remaining = ( duration * nextGroup[0] )
                info = nextGroup[1]

                # deactivate current index
                if activeIndex != -1:
                    for circuit in circuits[activeIndex][2]:
                        sendCommand(circuit + "_Powered", OFF)
        else:
            info = circuits[activeIndex][1]
        
        return [ info, remaining ]

    def callbackProgress(self):
        if self.progressTimer is not None and self.currentProgressMsg != getItemState("pOutdoor_Watering_Logic_Program_State").toString():
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
        postUpdate("pOutdoor_Watering_Logic_Program_State", self.currentProgressMsg)

        self.progressTimer = createTimer(self.log, 60.0, self.callbackProgress)
        self.progressTimer.start()

    def execute(self, module, input):
        self.cancelProgressTimer()

        if input["command"] == OFF:
            self.disableAllCircuits()
        else:
            self.callbackProgress()

