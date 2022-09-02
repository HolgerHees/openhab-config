from shared.helper import rule, getItemState, getPreviousItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule("roboter_messages.py")
class RoboterMessagesRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("*/15 * * * * ?"),
            #CronTrigger("0 0 * * * ?"),
            ItemStateChangeTrigger("pIndoor_Roomba_status"),
            ItemStateChangeTrigger("pIndoor_Roomba_full"),
            ItemStateChangeTrigger("pOutdoor_Mower_Status")
        ]

    def execute(self, module, input):
        group = "Fehler"
        active = []
        #url = None
        
        if getItemState("pIndoor_Roomba_status") != NULL and ( getItemState("pIndoor_Roomba_status").toString() == "Stuck" or getItemState("pIndoor_Roomba_full") == ON ):
            active.append("Roomba")

        mowerState = getItemState("pOutdoor_Mower_Status")
        if mowerState != NULL and ( mowerState.intValue() == 7 or mowerState.intValue() == 8 or mowerState.intValue() == 98 ):
            isDeepSleep = False
            if mowerState.intValue() == 98:
                previousState = getPreviousItemState("pOutdoor_Mower_Status")
                if previousState != NULL and previousState.intValue() == 17:
                    isDeepSleep = True
            if not isDeepSleep:
                active.append("Mower")
            #url = "https://smartmarvin.de/cameraAutomowerImage"

        if len(active) == 0:
            active.append("Alles ok")
            group = "Info"

        msg = ", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Robot", msg):
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ERROR, "Roboter " + group, msg)

