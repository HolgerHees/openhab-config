from shared.helper import rule, getGroupMemberChangeTrigger, getGroupMember
from shared.triggers import CronTrigger

map = {
    "pOutdoor_WeatherStation_Cloud_Cover": "cloudCoverInOcta",
    "pOutdoor_WeatherStation_Rain_Current": "rainCurrentInMillimeter",
    "pOutdoor_WeatherStation_Rain_Current_15Min": "rainCurrent15MinInMillimeter",
    "pOutdoor_WeatherStation_Rain_Daily": "rainDailyInMillimeter",
    "pOutdoor_WeatherStation_Rain_State": "rainCurrentLevel",
    "pOutdoor_WeatherStation_Wind_Speed": "windSpeedInKilometerPerHour",
    "pOutdoor_WeatherStation_Wind_Gust": "windGustInKilometerPerHour",
    "pOutdoor_WeatherStation_Wind_Direction": "windDirectionInDegree",
    "pOutdoor_WeatherStation_Dewpoint": "dewpointInCelsius",
    "pOutdoor_WeatherStation_Temperature": "airTemperatureInCelsius",
    "pOutdoor_WeatherStation_Temperature_Perceived": "perceivedTemperatureInCelsius",
    "pOutdoor_WeatherStation_Humidity": "airHumidityInPercent",
    "pOutdoor_WeatherStation_Pressure": "pressureInHectopascals",
    "pOutdoor_WeatherStation_Solar_Power": "solarPowerInWatt",
    "pOutdoor_WeatherStation_Light_Level": "lightLevelInLux",
    "pOutdoor_WeatherStation_UV_Index": "uvIndex"
}

@rule()
class CloudMqttPublish:
    def __init__(self):
        self.triggers = [CronTrigger("1 0 0 * * ?")]
        self.triggers += getGroupMemberChangeTrigger("gPersistance_Mqtt")
     
    def publish(self, mqttActions, name, state):
        if name in map:
            mqttActions.publishMQTT("hhees/weather/station/{}".format(map[name]),u"{}".format(state))
        else:
            self.log.error("Unknown mapping for item {}".format(name))

    def execute(self, module, input):
        mqttActions = actions.get("mqtt","mqtt:broker:cloud")

        if input['event'].getType() == "TimerEvent":
            for item in getGroupMember("gPersistance_Mqtt"):
                self.publish(mqttActions, item.getName(), item.getState())
        else:
            #self.log.info(u"{}".format(input['event'].getItemName(),input['event'].getItemState()))
            #mqttActions = actions.get("mqtt","mqtt:broker:mosquitto")
            #mqttActions.publishMQTT("mysensors-sub-1/1/4/1/0/2",u"{}".format(1 if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON else 0))

            self.publish(mqttActions, input['event'].getItemName(), input['event'].getItemState())

 
