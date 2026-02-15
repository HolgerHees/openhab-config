from datetime import datetime

from openhab import rule, Registry
from openhab.actions import HTTP
from openhab.triggers import ChannelEventTrigger, ItemStateUpdateTrigger

rule(
    runtime_measurement = False,
    triggers = [
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_air_temperature"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_feels_like_temperature"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_humidity"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_sunshine"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_cloudcover"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_refreshed"),
    ]
)
class WeatherForecastListener:
    def __init__(self):
        self.mapping = {
            "airTemperatureInCelsius": "pOutdoor_WeatherService_Temperature",
            "feelsLikeTemperatureInCelsius": "pOutdoor_WeatherService_Temperature_Perceived",
            "relativeHumidityInPercent": "pOutdoor_WeatherService_Humidity",
            "sunshineDurationInMinutes": "pOutdoor_WeatherService_Sunshine_Duration",
            "effectiveCloudCoverInOcta": "pOutdoor_WeatherService_Cloud_Cover"
        }
        self.count = 0

    def execute(self, module, input):
        if input['event'].getChannel().getId() == "weatherforecast_refreshed":
            self.logger.info("Weather forecast received {} values".format(self.count))
            self.count = 0
        else:
            _, _, _, _, field, data = input['event'].getEvent().split("/")
            timestamp, value = data.split("#")
            date = datetime.fromtimestamp(int(timestamp))
            Registry.getItem(self.mapping[field]).getPersistence("jdbc").persist(date, value)
            self.count += 1
