from marvin.helper import log, rule, createTimer, itemLastUpdateNewerThen, getNow, getFilteredChildItems, getGroupMember, getItemLastUpdate, getItemState, postUpdate, postUpdateIfChanged, sendCommand, sendNotification, getItemLastUpdate
from core.triggers import ItemStateChangeTrigger

'''awayCheckDuration = 15.0
timerAway = None


def checkMotion(historicDate, itemName, offset):
    # Is still active (motion detected)
    if getItemState(itemName) == OPEN:
        return True

    return itemLastUpdateNewerThen(itemName, historicDate.plusMillis(offset))

@rule("presence_detection.py")
class LeavingCheckRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Door_FF_Floor")]

    def callback(self):
        global timerAway
        timerAway = None

        if getItemState("Door_FF_Floor") == CLOSED and getItemState("Window_FF_Livingroom_Terrace") == CLOSED:
            doorClosedDate = getItemLastUpdate("Door_FF_Floor")

            isPresent = checkMotion(doorClosedDate, "Motiondetector_FF_Floor", 2800)

            if not isPresent:
                isPresent = checkMotion(doorClosedDate, "Motiondetector_FF_Livingroom", 4000)

                if not isPresent:
                    isPresent = checkMotion(doorClosedDate, "Motiondetector_SF_Floor", 4000)

            msg = ""
            if getItemState("Motiondetector_FF_Floor") == OPEN:
                msg = u"(active)"
            else:
                diff = getItemLastUpdate("Motiondetector_FF_Floor").getMillis() - doorClosedDate.getMillis()
                seconds = (float(diff) / 1000.0)
                msg = u"({} sec.)".format('{:04.2f}'.format(seconds))

            # motion is still present or was after door closed
            if isPresent:
                # self.log.info("State_Present", "ON")
                # should be already ON
                if postUpdateIfChanged("State_Present",ON):
                    sendNotification(u"Tür", u"Willkommen {} ???".format(msg))
                # just to know why we are still detected
                else:
                    sendNotification(u"Tür", u"Willkommen {} INFO".format(msg))
            else:
                # self.log.info("State_Present", "OFF")
                if postUpdateIfChanged("State_Present",OFF):
                    sendNotification(u"Tür", u"Auf Wiedersehen {}".format(msg))
                # OFF means somthing wrong
                else:
                    sendNotification(u"Tür", u"Auf Wiedersehen {} ???".format(msg))

    def execute(self, module, input):
        global timerAway
        if timerAway is not None:
            timerAway.cancel()
            timerAway = None
        
        if getItemState("Door_FF_Floor") == CLOSED and getItemState("Window_FF_Livingroom_Terrace") == CLOSED:
            timerAway = createTimer(awayCheckDuration, self.callback)
            timerAway.start()
        elif postUpdateIfChanged("State_Present",ON):
            sendNotification(u"Tür", u"Willkommen")'''

@rule("presence_detection.py")
class PresenceCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("State_Holger_Presence"),
            ItemStateChangeTrigger("State_Sandra_Presence")
        ]
        
    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()
        
        sendNotification(u"{}".format(itemName), u"{}".format(itemState))
        
        holgerPhone = itemState if itemName == "State_Holger_Presence" else getItemState("State_Holger_Presence")
        sandraPhone = itemState if itemName == "State_Sandra_Presence" else getItemState("State_Sandra_Presence")
        
        if holgerPhone == ON or sandraPhone == ON:
            if getItemState("State_Presence").intValue() == 0:
                postUpdate("State_Presence",1)
                sendNotification(u"Tür", u"Willkommen")
        else:
            if getItemState("State_Presence").intValue() != 0:
                postUpdate("State_Presence",0)
                lightMsg = u"- LICHT an" if getItemState("Lights_Indoor") != OFF else u""
                windowMsg = u"- FENSTER offen" if getItemState("Openingcontacts") != CLOSED else u""

                sendNotification(u"Tür", u"Auf Wiedersehen{}{}".format(lightMsg,windowMsg))

#@rule("presence_detection.py")
#class UnexpectedMotionRule:
#    def __init__(self):
#        self.triggers = [
#            ItemStateChangeTrigger("Motiondetector_FF_Floor","OPEN"),
#            ItemStateChangeTrigger("Motiondetector_FF_Livingroom","OPEN"),
#            ItemStateChangeTrigger("Motiondetector_SF_Floor","OPEN")
#        ]

#    def execute(self, module, input):
#        if getItemState("State_Presence").intValue() == 0:
#            sendNotification(u"Unexpected Motion", u"{}".format(input['event'].getItemName()))

@rule("presence_detection.py")
class WakeupRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_FF_Floor","OPEN"),
            ItemStateChangeTrigger("Motiondetector_FF_Livingroom","OPEN"),
            ItemStateChangeTrigger("Motiondetector_SF_Floor","OPEN"),
            ItemStateChangeTrigger("Lights_FF","ON"),
            ItemStateChangeTrigger("Shutters_FF","0")
        ]

    def execute(self, module, input):
        if getItemState("State_Presence").intValue() == 2:
            if getItemState("TV_Online") == ON or getItemState("Lights_FF") == ON or getItemState("Shutters_FF") == PercentType.ZERO:
                postUpdate("State_Presence", 1)

@rule("presence_detection.py") 
class SleepingRule:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("Scene4","ON") ]

    def execute(self, module, input):
        if getItemState("State_Presence").intValue() == 1:
            postUpdate("State_Presence", 2)
            
        postUpdate("Scene4", OFF)
