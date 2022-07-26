from shared.helper import rule, sendNotification, getItemState, postUpdateIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule("roboter_messages.py")
class RoboterMessagesRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 * * * ?"),
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

        if getItemState("pOutdoor_Mower_Status") != NULL and ( getItemState("pOutdoor_Mower_Status").intValue() == 7 or getItemState("pOutdoor_Mower_Status").intValue() == 8 or getItemState("pOutdoor_Mower_Status").intValue() == 98 ):
            active.append("Mower")
            #url = "https://smartmarvin.de/cameraAutomowerImage"

        if len(active) == 0:
            active.append("Alles ok")
            group = "Info"

        msg = ", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Robot", msg):
            sendNotification("Roboter " + group, msg)

