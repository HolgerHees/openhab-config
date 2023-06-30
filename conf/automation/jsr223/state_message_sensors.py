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


@rule()
class StateMessageSensors:
    def __init__(self):
        self.triggers = [
            CronTrigger("*/15 * * * * ?"),
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pIndoor_Plant_Sensor_Main_Info")
        ]

    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        states = []
        details = []
        group = "Fehler"

        if getItemState("pIndoor_Plant_Sensor_Main_Info").toString() != 'Alles ok':
            states.append(getItemState("pIndoor_Plant_Sensor_Main_Info").toString())

        for sensorItem in co2SensorItems:
            if getItemState(sensorItem).intValue() > 1500:
                states.append(u"CO2 Wert")
                details.append(sensorItem)
                priority = NotificationHelper.PRIORITY_ALERT
                break

        if len(states) == 0:
            states.append(u"Alles ok")
            group = "Info"
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = u", ".join(list(set(states)))

        if postUpdateIfChanged("pOther_State_Message_Sensors", msg):
            NotificationHelper.sendNotificationToAllAdmins(priority, "Sensoren " + group, msg)

        postUpdateIfChanged("pOther_State_Details_Sensors", u", ".join(list(set(details))))

        # Verbindungs Fehler
        co2_error_states = []
        tf_error_states = []

        refDate = ZonedDateTime.now().minusMinutes(60)  # last 1 hour
        for sensorItem in co2SensorItems:
            if itemLastUpdateOlderThen(sensorItem, refDate):
                #co2_error_states.append(u"CO2 Update")
                co2_error_states.append(sensorItem)

        refDate = ZonedDateTime.now().minusMinutes(1440)  # last 24 hours
        for sensorItem in sensorItems:
            if itemLastUpdateOlderThen(sensorItem, refDate):
                #tf_error_states.append(u"T/F Sensor")
                tf_error_states.append(sensorItem)

        if len(co2_error_states) > 0:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", u"Keine Updates mehr seit mehr als 60 Minuten: {}".format(u", ".join(co2_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", "")

        if len(tf_error_states) > 0:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", u"Keine Updates mehr seit mehr als 24 Stunden: {}".format(u", ".join(tf_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", "")

