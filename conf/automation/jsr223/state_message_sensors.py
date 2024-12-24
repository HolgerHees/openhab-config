from shared.helper import rule, itemLastUpdateOlderThen, getItemLastUpdate, getItemState, postUpdateIfChanged, NotificationHelper, getGroupMember
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime
from custom.watering import WateringHelper


@rule()
class StateMessageSensors:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pOther_Plant_Sensor_State_Watering_Info"),
            ItemStateChangeTrigger("pOther_Plant_Sensor_State_Device_Info"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_State_Device_Info")
        ]

    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        states = []
        details = []
        group = "Fehler"

        watering_state = getItemState("pOther_Plant_Sensor_State_Watering_Info").intValue()
        if watering_state not in [WateringHelper.STATE_WATERING_INACTIVE, WateringHelper.STATE_WATERING_WET, WateringHelper.STATE_WATERING_OPTIMAL]:
            states.append(WateringHelper.getStateInfo(watering_state))

        if getItemState("pOther_Plant_Sensor_State_Device_Info").toString() != "Alles ok":
            states.append("Pflanzensensor: " + getItemState("pOther_Plant_Sensor_State_Device_Info").toString())

        if getItemState("pOutdoor_WeatherStation_State_Device_Info").toString() != "Alles ok":
            states.append("Wetterstation: " + getItemState("pOutdoor_WeatherStation_State_Device_Info").toString())

        for sensorItem in getGroupMember("gRoom_CO2_Sensors"):
            if getItemState(sensorItem).intValue() > 2000:
                states.append(u"CO2 Wert")
                details.append(sensorItem.getName())
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

        for sensorItem in getGroupMember("gRoom_CO2_Sensors"):
            if itemLastUpdateOlderThen(sensorItem, refDate):
                self.log.info("CO2 Sensor: {}, lastUpdate: {}".format(sensorItem.getName(), getItemLastUpdate(sensorItem)))
                #co2_error_states.append(u"CO2 Update")
                co2_error_states.append(sensorItem.getName())

        for sensorItem in getGroupMember("gRoom_Temperatur_Sensors"):
            if itemLastUpdateOlderThen(sensorItem, refDate):
                self.log.info("T/F Sensor: {}, lastUpdate: {}".format(sensorItem.getName(), getItemLastUpdate(sensorItem)))
                #tf_error_states.append(u"T/F Sensor")
                tf_error_states.append(sensorItem.getName())

            #self.log.info("SENSOR: {} {}".format(sensorItem.getName(),getItemLastUpdate(sensorItem)))

        if len(co2_error_states) > 0:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", u"Keine Updates mehr seit mehr als 60 Minuten: {}".format(u", ".join(co2_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", "")

        if len(tf_error_states) > 0:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", u"Keine Updates mehr seit mehr als 60 Minuten: {}".format(u", ".join(tf_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", "")
