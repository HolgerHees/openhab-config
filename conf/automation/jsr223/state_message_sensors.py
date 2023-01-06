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
        priority = NotificationHelper.PRIORITY_ERROR
        states = []
        details = []
        group = "Fehler"

        if getItemState("pOutdoor_WeatherStation_Is_Working") == OFF:
            states.append(u"Wetter")
            
        if getItemState("pIndoor_Plant_Sensor_Main_Info").toString() != 'Alles ok':
            states.append(getItemState("pIndoor_Plant_Sensor_Main_Info").toString())

        refDate = ZonedDateTime.now().minusMinutes(60)  # last 1 hour
        for sensorItem in co2SensorItems:
            if getItemState(sensorItem).intValue() > 1500:
                states.append(u"CO2 Wert")
                details.append(sensorItem)
                priority = NotificationHelper.PRIORITY_ALERT
                break

            if itemLastUpdateOlderThen(sensorItem, refDate):
                states.append(u"CO2 Update")
                details.append(sensorItem)
                break

        refDate = ZonedDateTime.now().minusMinutes(1440)  # last 24 hours
        for sensorItem in sensorItems:
            if itemLastUpdateOlderThen(sensorItem, refDate):
                states.append(u"T/F Sensor")
                details.append(sensorItem)
                break

        if len(states) == 0:
            states.append(u"Alles ok")
            group = "Info" 
            priority = NotificationHelper.PRIORITY_NOTICE
            
        msg = u", ".join(list(set(states)))

        if postUpdateIfChanged("pOther_State_Message_Sensors", msg):
            NotificationHelper.sendNotificationToAllAdmins(priority, "Sensoren " + group, msg)
 
        postUpdateIfChanged("pOther_State_Details_Sensors", u", ".join(list(set(details))))
