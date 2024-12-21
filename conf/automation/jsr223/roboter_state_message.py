from shared.helper import rule, getItemState, getPreviousItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule()
class RoboterStateMessages:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?"),
            #CronTrigger("0 0 * * * ?"),
            ItemStateChangeTrigger("pOutdoor_Mower_Status"),
            ItemStateChangeTrigger("pOutdoor_Mower_Winter_Mode")
        ]

    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        group = "Fehler"
        active = []
        
        if getItemState("pOutdoor_Mower_Winter_Mode") == OFF:
            mowerState = getItemState("pOutdoor_Mower_Status")
            if mowerState != NULL and ( mowerState.intValue() == 7 or mowerState.intValue() == 8 or mowerState.intValue() == 98 ):
                isDeepSleep = False
                if mowerState.intValue() == 98:
                    previousState = getPreviousItemState("pOutdoor_Mower_Status")
                    if previousState != NULL and previousState.intValue() == 17:
                        isDeepSleep = True
                if not isDeepSleep:
                    active.append("Mower")

        if len(active) == 0:
            priority = NotificationHelper.PRIORITY_NOTICE
            active.append("Alles ok")
            group = "Info"

        msg = ", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Robot", msg):
            NotificationHelper.sendNotification(priority, "Roboter " + group, msg)

