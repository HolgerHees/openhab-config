from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper
from shared.notification import NotificationHelper

from custom.watering import WateringHelper

from datetime import datetime, timedelta


@rule(
    triggers = [
        GenericCronTrigger("0 */5 * * * ?"),
        ItemStateChangeTrigger("pOther_Plant_Sensor_State_Watering_Info"),
        ItemStateChangeTrigger("pOther_Plant_Sensor_State_Device_Info"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_State_Device_Info")
    ]
)
class Sensors:
    def execute(self, module, input):
        priority = NotificationHelper.PRIORITY_ERROR
        states = []
        details = []
        group = "Fehler"

        watering_state = Registry.getItemState("pOther_Plant_Sensor_State_Watering_Info").intValue()
        if watering_state not in [WateringHelper.STATE_WATERING_INACTIVE, WateringHelper.STATE_WATERING_WET, WateringHelper.STATE_WATERING_OPTIMAL]:
            states.append(WateringHelper.getStateInfo(watering_state))

        if Registry.getItemState("pOther_Plant_Sensor_State_Device_Info").toString() != "Alles ok":
            states.append("Pflanzensensor: " + Registry.getItemState("pOther_Plant_Sensor_State_Device_Info").toString())

        if Registry.getItemState("pOutdoor_WeatherStation_State_Device_Info").toString() != "Alles ok":
            states.append("Wetterstation: " + Registry.getItemState("pOutdoor_WeatherStation_State_Device_Info").toString())

        for sensor_item in Registry.getItem("gRoom_CO2_Sensors").getAllMembers():
            sensor_item_name = sensor_item.getName()
            if Registry.getItemState(sensor_item_name).intValue() > 2000:
                states.append("CO2 Wert")
                details.append(sensor_item_name)
                priority = NotificationHelper.PRIORITY_ALERT
                break

        if len(states) == 0:
            states.append("Alles ok")
            group = "Info"
            priority = NotificationHelper.PRIORITY_NOTICE

        msg = ", ".join(list(set(states)))

        if Registry.getItem("pOther_State_Message_Sensors").postUpdateIfDifferent(msg):
            NotificationHelper.sendNotificationToAllAdmins(priority, "Sensoren " + group, msg)

        Registry.getItem("pOther_State_Details_Sensors").postUpdateIfDifferent(", ".join(list(set(details))))

        # Verbindungs Fehler
        co2_error_states = []
        tf_error_states = []

        last_hour = datetime.now().astimezone() - timedelta(minutes=60)  # last 1 hour

        for sensor_item in Registry.getItem("gRoom_CO2_Sensors").getAllMembers():
            sensor_item_name = sensor_item.getName()
            if ToolboxHelper.getLastUpdate(sensor_item_name) < last_hour:
                self.logger.info("CO2 Sensor: {}, lastUpdate: {}".format(sensor_item_name, ToolboxHelper.getLastUpdate(sensor_item_name)))
                #co2_error_states.append("CO2 Update")
                co2_error_states.append(sensor_item_name)

        for sensor_item in Registry.getItem("gRoom_Temperatur_Sensors").getAllMembers():
            sensor_item_name = sensor_item.getName()
            if ToolboxHelper.getLastUpdate(sensor_item_name) < last_hour:
                self.logger.info("T/F Sensor: {}, lastUpdate: {}".format(sensor_item_name, ToolboxHelper.getLastUpdate(sensor_item_name)))
                #tf_error_states.append("T/F Sensor")
                tf_error_states.append(sensor_item_name)

            #self.logger.info("SENSOR: {} {}".format(sensor_item_name,ToolboxHelper.getLastUpdate(sensor_item_name)))

        if len(co2_error_states) > 0:
            Registry.getItem("eOther_Error_CO2_Sensor_Message").postUpdateIfDifferent("Keine Updates mehr seit mehr als 60 Minuten: {}".format(", ".join(co2_error_states)))
        else:
            Registry.getItem("eOther_Error_CO2_Sensor_Message").postUpdateIfDifferent("")

        if len(tf_error_states) > 0:
            Registry.getItem("eOther_Error_Temperatur_Sensor_Message").postUpdateIfDifferent("Keine Updates mehr seit mehr als 60 Minuten: {}".format(", ".join(tf_error_states)))
        else:
            Registry.getItem("eOther_Error_Temperatur_Sensor_Message").postUpdateIfDifferent("")
