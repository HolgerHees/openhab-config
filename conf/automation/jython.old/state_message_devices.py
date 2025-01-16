from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import ItemStateChangeTrigger


@rule()
class StateMessageDevices:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Mower_State_Message"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_State_Message"),
            ItemStateChangeTrigger("pFF_Bedroom_Humidifier_State_Message")
        ]
        self.check()
        
    def check(self):
        priority = NotificationHelper.PRIORITY_ERROR
        active = []
        
        mower_state = getItemState("pOutdoor_Mower_State_Message").toString()
        if mower_state != "Alles ok":
            active.append(u"Rasenmähroboter {}".format( robot_state ))

        eg_humidifier_state = getItemState("pGF_Livingroom_Humidifier_State_Message").toString()
        if eg_humidifier_state != "Alles ok":
            active.append(u"Luftbefeuchter EG {}".format( eg_humidifier_state ))

        og_humidifier_state = getItemState("pFF_Bedroom_Humidifier_State_Message").toString()
        if og_humidifier_state != "Alles ok":
            active.append(u"Luftbefeuchter OG {}".format( og_humidifier_state ))

        if len(active) == 0:
            active.append("Alles ok")
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = ", ".join(active)
        
        if postUpdateIfChanged("pOther_State_Message_Devices", msg):
            NotificationHelper.sendNotification(priority, u"Geräte", msg)

    def execute(self, module, input):
        self.check()

