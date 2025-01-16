from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.notification import NotificationHelper


@rule(
    triggers = [
        GenericCronTrigger("0 */5 * * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_State_Message"),
        ItemStateChangeTrigger("pGF_Corridor_Lock_State_Device_Info")
    ]
)
class Main:
    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        active = []
        group = "Fehler"

        ventilation_state = Registry.getItemState("pGF_Utilityroom_Ventilation_State_Message").toString()
        if ventilation_state != "Alles ok":
            active.append("Lüftungsanlage {}".format( ventilation_state ))

        maindoor_state = Registry.getItemState("pGF_Corridor_Lock_State_Device_Info").toString()
        if maindoor_state != "Alles ok":
            active.append("Haustür (Nuki) {}".format( maindoor_state ))

        if len(active) == 0:
            active.append("Alles ok")
            group = "Info" 
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = ", ".join(active)

        if msg == "Filter":
            group = "Info"
            priority = NotificationHelper.PRIORITY_NOTICE

        if Registry.getItem("pOther_State_Message_Main").postUpdateIfDifferent(msg):
            NotificationHelper.sendNotification(priority, "Haustechnik " + group, msg)
