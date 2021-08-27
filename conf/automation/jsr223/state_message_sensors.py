from shared.helper import rule, itemLastUpdateOlderThen, sendNotificationToAllAdmins, getItemState, postUpdateIfChanged
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime

sensorItems = [
    "pGF_Livingroom_Air_Sensor_Temperature_Value",
    "pGF_Boxroom_Air_Sensor_Temperature_Value",
    "pGF_Guestroom_Air_Sensor_Temperature_Value",
    "pGF_Guesttoilet_Air_Sensor_Temperature_Value",
    "pGF_Corridor_Air_Sensor_Temperature_Value",
    "pGF_Utilityroom_Air_Sensor_Temperature_Value",
    "pGF_Garage_Air_Sensor_Temperature_Value",
    "pFF_Bedroom_Air_Sensor_Temperature_Value",
    "pFF_Dressingroom_Air_Sensor_Temperature_Value",
    "pFF_Child1_Air_Sensor_Temperature_Value",
    "pFF_Child2_Air_Sensor_Temperature_Value",
    "pFF_Bathroom_Air_Sensor_Temperature_Value",
    "pFF_Corridor_Air_Sensor_Temperature_Value",
    "pFF_Attic_Air_Sensor_Temperature_Value"
]


@rule("state_message_sensors.py")
class StateMessageSensorsRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("*/15 * * * * ?"),
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
        for sensorItem in sensorItems:
            if itemLastUpdateOlderThen(sensorItem, refDate):
                active.append(u"Sensors")
                break
            #self.log.info(u"{} {}".format(sensorItem,getItemLastUpdate(sensorItem)))

        if len(active) == 0:
            active.append(u"Alles ok")
            group = "Info" 
            
        msg = u", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Sensors", msg):
            sendNotificationToAllAdmins("Sensoren " + group, msg)
 
