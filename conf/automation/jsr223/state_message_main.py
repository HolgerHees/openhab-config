from shared.helper import rule, itemLastUpdateOlderThen, sendNotificationToAllAdmins, getItemState, postUpdateIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime


@rule("state_message_main.py")
class StateMessageMainRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_State_Message"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_State_Message"),
            ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Is_Working"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Is_Working"),
            ItemStateChangeTrigger("State_Server")
        ]

    def execute(self, module, input):
        active = []
        group = "Fehler"

        if getItemState("pGF_Utilityroom_Ventilation_State_Message").toString() != "Alles ok":
            if getItemState("pGF_Utilityroom_Ventilation_State_Message") == "Filter:":
                active.append(u"Filter")
            else:
                active.append(u"Lüftung")

        if getItemState("pGF_Utilityroom_Heating_State_Message").toString() != "Alles ok":
            active.append(u"Heizung")

        if getItemState("pGF_Garage_Solar_Inverter_Is_Working") == OFF:
            active.append(u"Solar")

        if getItemState("State_Server").intValue() > 1:
            active.append(u"Server")

        if len(active) == 0:
            active.append(u"Alles ok")
            group = "Info" 

        msg = u", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Main", msg):
            sendNotificationToAllAdmins("Main " + group, msg)
