from datetime import datetime

from openhab import rule, Registry
from openhab.actions import HTTP
from openhab.triggers import ChannelEventTrigger


@rule(
    runtime_measurement = False,
    triggers = [
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_temperature"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_cloudcover"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_sunshine"),
      ChannelEventTrigger("mqtt:broker:cloud:weatherforecast_refreshed")
    ]
)
class WeatherForecastListener:
    def __init__(self):
        self.mapping = {
            "airTemperatureInCelsius": "pOutdoor_Weather_Forecast_Temperature",
            "effectiveCloudCoverInOcta": "pOutdoor_Weather_Forecast_Cloud_Cover",
            "sunshineDurationInMinutes": "pOutdoor_Weather_Forecast_Sunshine_Duration"
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

#state = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getState()
#print(state)

#state = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getPersistence("jdbc").persistedState(datetime.now())
#print(state)
