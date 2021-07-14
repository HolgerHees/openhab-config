from shared.helper import rule, sendNotification, getItemState, postUpdateIfChanged, sendNotificationToAllAdmins
from core.triggers import CronTrigger, ItemStateChangeTrigger

@rule("state_message_devices.py")
class StateMessageDevicesRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0 0 * * * ?"),
            ItemStateChangeTrigger("pOther_State_Message_Robot"),
            ItemStateChangeTrigger("pOther_State_Message_Homeconnect")
        ]

    def execute(self, module, input):
        active = []
        
        if getItemState("pOther_State_Message_Robot").toString() != "Alles ok":
            active.append("Roboter")

        if getItemState("pOther_State_Message_Homeconnect").toString() != "Alles ok":
            active.append("Homeconnect")

        if len(active) == 0:
            active.append("Alles ok")

        msg = ", ".join(active)
        
        oldMsg = getItemState("pOther_State_Message_Devices").toString()

        if postUpdateIfChanged("pOther_State_Message_Devices", msg):
            # don't notify robots, because they are already notified seperatly
            if msg not in ["Roboter","Alles ok"] or oldMsg not in ["Roboter","Alles ok"]:
                sendNotificationToAllAdmins("Geräte", msg)

