from shared.helper import rule, itemLastUpdateOlderThen, sendNotificationToAllAdmins, getItemState, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime

@rule("values_error_messages.py")
class ValuesErrorMessagesRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error"),
            ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Error_Message"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Common_Fault"),
            ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Is_Working"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Is_Working"),
            ItemStateChangeTrigger("State_Server")
        ]

    def execute(self, module, input):
        group = u"Fehler"
        active = []

        if getItemState("pGF_Utilityroom_Ventilation_Filter_Error") == ON or getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            active.append(u"Lüftung")

        if getItemState("pGF_Utilityroom_Heating_Common_Fault").intValue() > 0:
            active.append(u"Heizung Fehler")

        if itemLastUpdateOlderThen("pGF_Utilityroom_Heating_Common_Fault", ZonedDateTime.now().minusMinutes(10)):
            active.append(u"Heizung ⟳")
            
        if getItemState("pGF_Garage_Solar_Inverter_Is_Working") == OFF:
            active.append(u"Solar ⟳")

        if getItemState("pOutdoor_WeatherStation_Is_Working") == OFF:
            active.append(u"Wetter ⟳")
            
        if getItemState("State_Server").intValue() > 1:
            active.append(u"Server")

        refDate = ZonedDateTime.now().minusMinutes(1440)  # last 24 hours

        if itemLastUpdateOlderThen("pGF_Livingroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Boxroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Guestroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Guesttoilet_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Corridor_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Utilityroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pGF_Garage_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Bedroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Dressingroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Child1_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Child2_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Bathroom_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Corridor_Air_Sensor_Temperature_Value", refDate) \
                or itemLastUpdateOlderThen("pFF_Attic_Air_Sensor_Temperature_Value", refDate):
            active.append(u"Sensors ⟳")

        if len(active) == 0:
            active.append(u"Alles normal")
            group = u"Info"

        msg = u", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Main", msg):
            sendNotificationToAllAdmins(group, msg)
