from shared.helper import rule, itemLastUpdateOlderThen, getItemState, postUpdateIfChanged, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime

sensorItems = [
    "pGF_Livingroom_Air_Sensor_Temperature_Value",
    "pGF_Boxroom_Air_Sensor_Temperature_Value",
    "pGF_Workroom_Air_Sensor_Temperature_Value",
    "pGF_Guesttoilet_Air_Sensor_Temperature_Value",
    "pGF_Corridor_Air_Sensor_Temperature_Value",
    "pGF_Utilityroom_Air_Sensor_Temperature_Value",
    "pGF_Garage_Air_Sensor_Temperature_Value",
    "pFF_Bedroom_Air_Sensor_Temperature_Value",
    "pFF_Dressingroom_Air_Sensor_Temperature_Value",
    "pFF_Fitnessroom_Air_Sensor_Temperature_Value",
    "pFF_Makeuproom_Air_Sensor_Temperature_Value",
    "pFF_Bathroom_Air_Sensor_Temperature_Value",
    "pFF_Corridor_Air_Sensor_Temperature_Value",
    "pFF_Attic_Air_Sensor_Temperature_Value"
]

co2SensorItems = [
    "pGF_Boxroom_Air_Sensor_CO2_Value",
    "pGF_Dressingroom_Air_Sensor_CO2_Value"
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

        refDate = ZonedDateTime.now().minusMinutes(15)  # last 24 hours
        for co2SensorItem in co2SensorItems:
            if getItemState(co2SensorItem).intValue() > 1500:
                active.append(u"CO2 Wert")
                self.log.warn(u"CO2 Sensor: '{}', Value: '{}'".format(co2SensorItem,getItemState(co2SensorItem).intValue()))
                break

            if itemLastUpdateOlderThen(co2SensorItem, refDate):
                active.append(u"CO2 Sensor")
                self.log.warn(u"CO2 Sensor: '{}' was not updated for 15 minutes".format(co2SensorItem))
                break

        refDate = ZonedDateTime.now().minusMinutes(1440)  # last 24 hours
        for sensorItem in sensorItems:
            if itemLastUpdateOlderThen(sensorItem, refDate):
                active.append(u"T/F Sensor")
                self.log.warn(u"Room Sensor: '{}' was not updated for more then 24 hours".format(co2SensorItem))
                break

        if len(active) == 0:
            active.append(u"Alles ok")
            group = "Info" 
            
        msg = u", ".join(active)

        if postUpdateIfChanged("pOther_State_Message_Sensors", msg):
            NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_ERROR, "Sensoren " + group, msg)
 
