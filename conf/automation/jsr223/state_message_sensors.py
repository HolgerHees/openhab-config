from shared.helper import rule, itemLastUpdateOlderThen, sendNotificationToAllAdmins, getItemState, postUpdateIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime


@rule("state_message_sensors.py")
class StateMessageSensorsRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Is_Working"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Main_Info")
        ]

    def execute(self, module, input):
        active = []
        group = "Fehler"

        if getItemState("pOutdoor_WeatherStation_Is_Working") == OFF:
            active.append(u"Wetter")
            
        if getItemState("pIndoor_Plant_Sensor_Main_Info").toString() != 'Alles ok':
            active.append(getItemState("pIndoor_Plant_Sensor_Main_Info").toString())

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
            active.append(u"Sensors")

        if len(active) == 0:
            active.append(u"Alles ok")
            group = "Info" 
            
        msg = u", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Sensors", msg):
            sendNotificationToAllAdmins("Sensoren " + group, msg)
 
