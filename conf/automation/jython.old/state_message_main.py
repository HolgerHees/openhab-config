from shared.helper import rule, getItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger


@rule()
class StateMessageMain:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_State_Message"),
            ItemStateChangeTrigger("pGF_Corridor_Lock_State_Device_Info")
        ]

    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        active = []
        group = "Fehler"

        ventilation_state = getItemState("pGF_Utilityroom_Ventilation_State_Message").toString()
        if ventilation_state != "Alles ok":
            active.append(u"Lüftungsanlage {}".format( ventilation_state ))

        maindoor_state = getItemState("pGF_Corridor_Lock_State_Device_Info").toString()
        if maindoor_state != "Alles ok":
            active.append(u"Haustür (Nuki) {}".format( maindoor_state ))

        if len(active) == 0:
            active.append(u"Alles ok")
            group = "Info" 
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = u", ".join(active)

        if msg == "Filter":
            group = "Info"
            priority = NotificationHelper.PRIORITY_NOTICE

        if postUpdateIfChanged("pOther_State_Message_Main", msg):
            NotificationHelper.sendNotification(priority, "Haustechnik " + group, msg)
