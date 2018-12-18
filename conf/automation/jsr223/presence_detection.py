from marvin.helper import log, rule, createTimer, itemLastUpdateNewerThen, getNow, getFilteredChildItems, getGroupMember, getItemLastUpdate, getItemState, postUpdate, \
    postUpdateIfChanged, sendCommand, sendNotification
from core.triggers import ItemStateChangeTrigger

awayCheckDuration = 15.0
timerAway = None


def checkMotion(historicDate, itemName, offset):
    # Is still active (motion detected)
    if getItemState(itemName) == OPEN:
        return True

    # If the last update is max 4 seconds after the door CLOSED event
    # 1. was CLOSED => an late triggered OPEN / CLOSED without motion
    # or
    # 2. was OPEN   => a CLOSED event
    # or
    # 3. was OPEN   => point 2 followed by point 1

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
            sendNotification(u"Tür", u"Willkommen")


@rule("presence_detection.py")
class AwayRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Present","OFF")]

    def execute(self, module, input):
        if postUpdateIfChanged("State_Sleeping",OFF):
            self.log.error("Presence Detection: Sleeping state was ON but presence detection was OFF")

        postUpdateIfChanged("State_Notify", ON)


@rule("presence_detection.py")
class MotionCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Motiondetector_FF_Floor","OPEN"),
            ItemStateChangeTrigger("Motiondetector_FF_Livingroom","OPEN"),
            ItemStateChangeTrigger("Motiondetector_SF_Floor","OPEN")
        ]

    def execute(self, module, input):
        if getItemState("State_Present") == ON:
            if getItemState("State_Sleeping") != OFF:
                if getItemState("TV_Online") == ON or getItemState("Lights_FF") == ON or (
                        getItemState("Shutters_FF_Livingroom_Terrace") == PercentType.ZERO and getItemState("Shutters_FF_Livingroom_Couch") == PercentType.ZERO):
                    # self.log.info("MotionCheck", "WAKEUP")
                    postUpdate("State_Sleeping", OFF)
        else:
            sendNotification("Motion", "Unerwartete Bewegung in {}".format(input['event'].getItemName()))
            self.log.error(u"Presence Detection: Motion detected in {} but presence detection was OFF".format(input['event'].getItemName()))
            postUpdate("State_Present", ON)

@rule("presence_detection.py") 
class SleepingCheckRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Lights_Indoor", "OFF")]
        self.timerSleep = None

    def callback(self):
        global timerAway

        # Precence/Away/Motiondetector still active or flapping
        if timerAway is not None or itemLastUpdateNewerThen("Motiondetector_FF_Floor", getNow().minusSeconds(int(awayCheckDuration))):
            self.timerSleep = createTimer(awayCheckDuration, self.callback)
            self.timerSleep.start()
        else:
            self.timerSleep = None
            postUpdateIfChanged("State_Sleeping", ON)

    def execute(self, module, input):
        if self.timerSleep is not None:
            self.timerSleep.cancel()
            self.timerSleep = None

        #self.log.info("test 0 " + str(getItemState("State_Present")) + " " + str(getItemState("State_Sleeping")))
        #self.log.info("test 1 " + str(getItemState("TV_Online")) + " " + str(len(getFilteredChildItems("Shutters", PercentType.ZERO))))

        #if True:
        if getItemState("State_Present") == ON and getItemState("State_Sleeping") != ON:
            # Motiondetector_SF_Floor.lastUpdate.isAfter( Motiondetector_FF_Floor.lastUpdate )
            #if getItemState("TV_Online") == OFF and len(getFilteredChildItems("Shutters", PercentType.ZERO)) == 11:
            if getItemState("TV_Online") == OFF \
               and len(getFilteredChildItems("Shutters_FF", PercentType.ZERO)) == 0 \
               and ( len(getFilteredChildItems("Shutters_SF", PercentType.ZERO)) == 0 or getItemState("State_Outdoorlights") == ON ):
                self.callback()
                    
                    
#sendCommand("State_Sleeping",OFF)
#def test():
#    sendCommand("Light_SF_Floor_Ceiling",ON)
#    sendCommand("Scene4",ON)
#Timer(5, test ).start()

