from marvin.helper import log, rule, createTimer, itemLastUpdateNewerThen, getNow, getFilteredChildItems, getGroupMember, getItemLastUpdate, getItemState, postUpdate, \
    postUpdateIfChanged, sendCommand, sendNotification, getItemLastUpdate
from core.triggers import ItemStateChangeTrigger

awayCheckDuration = 15.0
timerAway = None


'''

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
            ItemStateChangeTrigger("State_Holger_Present"),
            ItemStateChangeTrigger("State_Sandra_Present")
        ]
        
    def execute(self, module, input):
        itemName = input['event'].getItemName()
        itemState = input['event'].getItemState()
        
        sendNotification(u"{}".format(itemName), u"{}".format(itemState))
        
        holgerPhone = itemState if itemName == "State_Holger_Present" else getItemState("State_Holger_Present")
        sandraPhone = itemState if itemName == "State_Sandra_Present" else getItemState("State_Sandra_Present")
        
        if holgerPhone == ON or sandraPhone == ON:
            if postUpdateIfChanged("State_Present",ON):
                sendNotification(u"Tür", u"Willkommen")
        else:
            if postUpdateIfChanged("State_Present",OFF):
                sendNotification(u"Tür", u"Auf Wiedersehen")

@rule("presence_detection.py")
class LeavingRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Present","OFF")]

    def execute(self, module, input):
        if postUpdateIfChanged("State_Sleeping",OFF):
            self.log.error("Presence Detection: Sleeping state was ON but presence detection was OFF")

        postUpdateIfChanged("State_Notify", ON)


@rule("presence_detection.py")
class UnexpectedMotionRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_FF_Floor","OPEN"),
            ItemStateChangeTrigger("Motiondetector_FF_Livingroom","OPEN"),
            ItemStateChangeTrigger("Motiondetector_SF_Floor","OPEN")
        ]

    def execute(self, module, input):
        if getItemState("State_Present") == OFF:
            sendNotification(u"Unexpected Motion", u"{}".format(input['event'].getItemName()))

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
        if getItemState("State_Present") == ON and getItemState("State_Sleeping") ==  ON:
            if getItemState("TV_Online") == ON or getItemState("Lights_FF") == ON or getItemState("Shutters_FF") == PercentType.ZERO:
                postUpdate("State_Sleeping", OFF)

@rule("presence_detection.py") 
class SleepingRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Lights_Indoor", "OFF")]
        self.timerSleep = None

    '''def callback(self):
        global timerAway

        # Precence/Away/Motiondetector still active or flapping
        if timerAway is not None or itemLastUpdateNewerThen("Motiondetector_FF_Floor", getNow().minusSeconds(int(awayCheckDuration))):
            self.timerSleep = createTimer(awayCheckDuration, self.callback)
            self.timerSleep.start()
        else:
            self.timerSleep = None
            postUpdateIfChanged("State_Sleeping", ON)'''

    def execute(self, module, input):
        #if self.timerSleep is not None:
        #    self.timerSleep.cancel()
        #    self.timerSleep = None

        #self.log.info("test 0 " + str(getItemState("State_Present")) + " " + str(getItemState("State_Sleeping")))
        #self.log.info("test 1 " + str(getItemState("TV_Online")) + " " + str(len(getFilteredChildItems("Shutters", PercentType.ZERO))))

        if getItemState("State_Present") == ON and getItemState("State_Sleeping") == OFF:
            if getItemState("TV_Online") == OFF and getItemState("Shutters_FF") != PercentType.ZERO:

                # last motion was in upper floor
                diff = getItemLastUpdate("Motiondetector_FF_Floor").getMillis() - getItemLastUpdate("Motiondetector_SF_Floor").getMillis()
                if diff > 100:
                    postUpdateIfChanged("State_Sleeping", ON)
                
                # Motiondetector_SF_Floor.lastUpdate.isAfter( Motiondetector_FF_Floor.lastUpdate )
                #if getItemState("TV_Online") == OFF and len(getFilteredChildItems("Shutters", PercentType.ZERO)) == 11:
                #if getItemState("TV_Online") == OFF \
                #   and len(getFilteredChildItems("Shutters_FF", PercentType.ZERO)) == 0 \
                #   and ( len(getFilteredChildItems("Shutters_SF", PercentType.ZERO)) == 0 or getItemState("State_Outdoorlights") == ON ):
                #    self.callback()
                    
                    
#sendCommand("State_Sleeping",OFF)
#def test():
#    sendCommand("Light_SF_Floor_Ceiling",ON)
#    sendCommand("Scene4",ON)
#Timer(5, test ).start()

