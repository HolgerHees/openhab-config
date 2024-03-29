from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import ItemStateChangeTrigger


@rule()
class StateMessageDevices:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_State_Message_Robot")
        ]
        self.check()
        
    def check(self):
        priority = NotificationHelper.PRIORITY_ERROR
        active = []
        
        if getItemState("pOther_State_Message_Robot").toString() != "Alles ok":
            active.append("Roboter")

        if len(active) == 0:
            active.append("Alles ok")
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = ", ".join(active)
        
        oldMsg = getItemState("pOther_State_Message_Devices").toString()

        if postUpdateIfChanged("pOther_State_Message_Devices", msg):
            # don't notify robots, because they are already notified seperatly
            if msg not in ["Roboter","Alles ok"] or oldMsg not in ["Roboter","Alles ok"]:
                NotificationHelper.sendNotificationToAllAdmins(priority, u"Geräte", msg)

    def execute(self, module, input):
        self.check()

