import math

from marvin.helper import rule, createTimer, getNow, getGroupMember, getItemState, postUpdate, sendCommand
from core.triggers import ItemCommandTrigger

@rule("scenes_wathering.py")
class ScenesWatheringRule:
    def __init__(self):
        self.triggers = [ItemCommandTrigger("Watering_Program_Start")]

        self.progressTimer = None
        self.currentProgressMsg = ""
        self.nextStepTime = None

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
        self.nextStepTime = None

    def callbackStep(self):
        duration = getItemState("Watering_Program_Duration").intValue()

        # Finish
        if getItemState("Watering_Streetside_Lawn") == ON:
            # self.log.info("1" )
            self.nextStepTime = None
            self.disableAllCircuits()
            postUpdate("Watering_Program_Start", OFF)
            return -1
        # Step 3
        elif getItemState("Watering_Gardenside_Lawn_right") == ON:
            # self.log.info("2" )
            duration = duration / 3 * 2
            sendCommand("Watering_Streetside_Lawn", ON)
            sendCommand("Watering_Gardenside_Lawn_right", OFF)
        # Step 2
        elif getItemState("Watering_Gardenside_Lawn_left") == ON:
            # self.log.info("3" )
            sendCommand("Watering_Gardenside_Lawn_right", ON)
            sendCommand("Watering_Gardenside_Lawn_left", OFF)
        # Step 1
        else:
            # self.log.info("4" )
            sendCommand("Watering_Streetside_Beds", ON)
            sendCommand("Watering_Gardenside_Beds_front", ON)
            sendCommand("Watering_Gardenside_Lawn_left", ON)

        self.nextStepTime = getNow().plusMinutes(duration)

        return duration

    def callbackProgress(self):
        if self.progressTimer is None:
            self.nextStepTime = getNow()
        elif self.currentProgressMsg != getItemState("Watering_Program_State").toString():
            self.log.info("Cancel Watering Progress Zombie Timer")
            self.cleanProgressTimer()
            return

        nextStepInSeconds = (self.nextStepTime.getMillis() - getNow().getMillis()) / 1000.0

        if nextStepInSeconds <= 0:
            nextStepInMinutes = self.callbackStep()

            if nextStepInMinutes == -1:
                self.cleanProgressTimer()
                return
        else:
            nextStepInMinutes = int(math.floor(nextStepInSeconds / 60.0))

        msg = u""

        if getItemState("Watering_Gardenside_Lawn_left") == ON:
            msg = u"Garten links "
        elif getItemState("Watering_Gardenside_Lawn_right") == ON:
            msg = u"Garten rechts "
        elif getItemState("Watering_Streetside_Lawn") == ON:
            msg = u"Strasse "

        if nextStepInMinutes > 0:
            msg = u"{}noch {} min".format(msg,nextStepInMinutes)
        else:
            msg = u"{}gleich fertig".format(msg)

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

