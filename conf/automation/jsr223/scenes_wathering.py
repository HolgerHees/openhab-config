import math

from custom.helper import rule, createTimer, getNow, getGroupMember, getItemState, postUpdate, sendCommand, getItemLastUpdate
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
            
        if getItemState("Watering_Circuits") == OFF:
            for group in circuits:
                #self.log.info("start " + loop[0][0])
                isActive = False
                for circuit in group[2]:
                    if getItemState(circuit + "_Auto") == ON:
                        sendCommand(circuit, ON)
                        isActive = True
                if isActive:
                    remaining = ( duration * group[0] )
                    info = group[1]
                    break
                      
        else:
          activeIndex = -1
          activeGroup = None
          for i in range(len(circuits)):
              group = circuits[i]
              
              if getItemState(group[2][0]) == ON:
                  activeIndex = i
                  activeGroup = group
                  break

          if activeGroup != None:
              runtime = getNow().getMillis() - getItemLastUpdate(activeGroup[2][0]).getMillis()
              
              remaining = ( duration * activeGroup[0] ) - runtime
              if remaining <= 0:
                  activeIndex += 1
                  if activeIndex < len(circuits):
                      for circuit in circuits[activeIndex][2]:
                          sendCommand(circuit, ON)
                      for circuit in activeGroup[2]:
                          sendCommand(circuit, OFF)

                      activeGroup = circuits[activeIndex]

                      remaining = ( duration * activeGroup[0] )
                      info = activeStep[1]
                  else:
                      self.disableAllCircuits()
                      postUpdate("Watering_Program_Start", OFF)
              else:
                  info = activeGroup[1]

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

