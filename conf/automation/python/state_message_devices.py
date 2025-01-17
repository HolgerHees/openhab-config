from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger, SystemStartlevelTrigger

from shared.notification import NotificationHelper


@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pOutdoor_Mower_State_Message"),
        ItemStateChangeTrigger("pGF_Livingroom_Humidifier_State_Message"),
        ItemStateChangeTrigger("pFF_Bedroom_Humidifier_State_Message")
    ]
)
class Main:
    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        active = []

        mower_state = Registry.getItemState("pOutdoor_Mower_State_Message").toString()
        if mower_state != "Alles ok":
            active.append("Rasenmähroboter {}".format( mower_state ))

        eg_humidifier_state = Registry.getItemState("pGF_Livingroom_Humidifier_State_Message").toString()
        if eg_humidifier_state != "Alles ok":
            active.append("Luftbefeuchter EG {}".format( eg_humidifier_state ))

        og_humidifier_state = Registry.getItemState("pFF_Bedroom_Humidifier_State_Message").toString()
        if og_humidifier_state != "Alles ok":
            active.append("Luftbefeuchter OG {}".format( og_humidifier_state ))

        if len(active) == 0:
            active.append("Alles ok")
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = ", ".join(active)

        if Registry.getItem("pOther_State_Message_Devices").postUpdateIfDifferent(msg):
            NotificationHelper.sendNotification(priority, "Geräte", msg)

