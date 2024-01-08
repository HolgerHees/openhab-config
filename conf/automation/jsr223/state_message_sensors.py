from shared.helper import rule, itemLastUpdateOlderThen, getItemState, postUpdateIfChanged, NotificationHelper, getGroupMember
from shared.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime


@rule()
class StateMessageSensors:
    def __init__(self):
        self.triggers = [
            #CronTrigger("*/15 * * * * ?"),
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

        for sensorItem in getGroupMember("gRoom_CO2_Sensors"):
            if getItemState(sensorItem).intValue() > 2000:
                states.append(u"CO2 Wert")
                details.append(str(sensorItem))
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
                #co2_error_states.append(u"CO2 Update")
                co2_error_states.append(str(sensorItem))

        for sensorItem in getGroupMember("gRoom_Temperatur_Sensors"):
            if itemLastUpdateOlderThen(sensorItem, refDate):
                #tf_error_states.append(u"T/F Sensor")
                tf_error_states.append(str(sensorItem))

            #self.log.info("SENSOR: {} {}".format(sensorItem.getName(),getItemLastUpdate(sensorItem)))

        if len(co2_error_states) > 0:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", u"Keine Updates mehr seit mehr als 60 Minuten: {}".format(u", ".join(co2_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_CO2_Sensor_Message", "")

        if len(tf_error_states) > 0:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", u"Keine Updates mehr seit mehr als 60 Minuten: {}".format(u", ".join(tf_error_states)))
        else:
            postUpdateIfChanged("eOther_Error_Temperatur_Sensor_Message", "")

