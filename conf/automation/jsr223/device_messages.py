from shared.helper import rule, sendNotification, getItemState, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger

@rule("roboter_messages.py")
class RoboterMessagesRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0 0 * * * ?"),
            ItemStateChangeTrigger("pOther_State_Message_Robot"),
            ItemStateChangeTrigger("pOther_State_Message_Homeconnect")
        ]

    def execute(self, module, input):
        active = []
        
        if getItemState("pOther_State_Message_Robot") != NULL and getItemState("pOther_State_Message_Robot").toString() != "Alles normal":
            active.append("Roboter")

        if getItemState("pOther_State_Message_Homeconnect") != NULL and getItemState("pOther_State_Message_Homeconnect").toString() != "Alles normal":
            active.append("Homeconnect")

        if len(active) == 0:
            active.append("Alles normal")

        msg = ", ".join(active)

        postUpdateIfChanged("pOther_State_Message_Devices", msg)
 
