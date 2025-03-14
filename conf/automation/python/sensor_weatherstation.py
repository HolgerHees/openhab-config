from openhab import rule, Registry, Timer
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper

from datetime import datetime, timedelta
import math

import scope


DELAYED_UPDATE_TIMEOUT = 3

@rule(
    triggers = [
        GenericCronTrigger("0 * * * * ?")
    ]
)
class LastUpdate:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        
        newest_update = None
        oldest_update = None
        items = Registry.getItem("gWeatherstationInputValues").getAllMembers()
        states = {}
        
        for item in items:
            _update = ToolboxHelper.getLastUpdate(item)
            if _update.year == 1970:
                continue

            if newest_update is None or _update > newest_update:
                newest_update = _update

            if oldest_update is None or _update < oldest_update:
                oldest_update = _update
                
            last_update = ToolboxHelper.getLastUpdate(item)
            minutes = (last_update - now).total_seconds()
            states[item.getName()] = [minutes,"{:.0f} min: {} ({})".format(minutes,item.getName(),ToolboxHelper.getLastUpdate(item))]
        
        if newest_update is None or oldest_update is None:
            self.logger.error("Update time calculation has a problem")
            return
                
        newest_update_in_minutes = int((newest_update - now).total_seconds() / 60)
        newest_update_in_minutes_msg = "{:.0f}".format(newest_update_in_minutes) if newest_update_in_minutes >= 1 else "<1"
        
        oldest_update_in_minutes = int((oldest_update - now).total_seconds() / 60)
        oldest_update_in_minutes_msg = "{:.0f}".format(oldest_update_in_minutes) if oldest_update_in_minutes >= 1 else "<1"
        
        if newest_update_in_minutes_msg != oldest_update_in_minutes_msg:
            msg = "{} bis {} min.".format(newest_update_in_minutes_msg,oldest_update_in_minutes_msg)
        else:
            msg = "{} min.".format(newest_update_in_minutes_msg)
            
        Registry.getItem("pOutdoor_WeatherStation_Update_Message").postUpdateIfDifferent(msg)

        is_working = oldest_update_in_minutes <= 60
        Registry.getItem("pOutdoor_WeatherStation_Is_Working").postUpdateIfDifferent(scope.ON if is_working else scope.OFF)
        Registry.getItem("eOther_Error_WeatherStation_Message").postUpdateIfDifferent("" if is_working else "Keine Updates seit mehr als 60 Minuten")

        if oldest_update_in_minutes > 10:
            for state in states:
                self.logger.debug(states[state][1])
        #        
        #    if not self.notified:
        #        self.logger.error("Weatherstation has problems")
        #        self.notified = True
        #elif self.notified:
        #    self.logger.error("Weatherstation is working")
        #    self.notified = False


@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Daily"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Rate")
    ]
)
class Rain:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        rain_rate = Registry.getItemState("pOutdoor_WeatherStation_Rain_Rate",scope.DecimalType(0.0)).doubleValue()
        today_rain = Registry.getItemState("pOutdoor_WeatherStation_Rain_Daily",scope.DecimalType(0.0)).doubleValue()
        rain_level = Registry.getItemState("pOutdoor_WeatherStation_Rain_State").intValue()

        if rain_level == 0:
            rain_state = "Trocken"
        elif rain_level < 3:
            rain_state = "Leicht"
        elif rain_level < 6:
            rain_state = "Mittel"
        elif rain_level < 8:
            rain_state = "Stark"
        else:
            rain_state = "Extrem"
            
        Registry.getItem("pOutdoor_WeatherStation_Rain_State_Message").postUpdateIfDifferent("{} ({})".format(rain_state,rain_level))
      
        if today_rain > 0:
            msg = "{} {} ({}) mm".format(rain_state, rain_rate,today_rain)
        else:
            msg = "{}".format(rain_state)

        Registry.getItem("pOutdoor_WeatherStation_Rain_Message").postUpdateIfDifferent(msg)
        
    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Daily":
            amount_new = Registry.getItemState("pOutdoor_WeatherStation_Rain_Daily",scope.DecimalType(0.0)).doubleValue()
            amount_old = ToolboxHelper.getPersistedState("pOutdoor_WeatherStation_Rain_Daily", datetime.now().astimezone() - timedelta(hours=1)).doubleValue()
            Registry.getItem("pOutdoor_WeatherStation_Rain_Hourly").postUpdateIfDifferent(amount_new - amount_old)
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Rate":
            rate = input['event'].getItemState().doubleValue()

            if rate > 100:
                rain_level = 10
            elif rate > 50:     # > 50.0 violent
                rain_level = 9
            elif rate > 25.6:   # max 50.0 heavy
                rain_level = 8
            elif rate > 12.8:
                rain_level = 7
            elif rate > 6.4:    # max 7.5 moderate
                rain_level = 6
            elif rate > 3.2:
                rain_level = 5
            elif rate > 1.6:    # max 2.5 light
                rain_level = 4
            elif rate > 0.8:
                rain_level = 3
            elif rate > 0.4:
                rain_level = 2
            elif rate > 0:
                rain_level = 1
            else:
                rain_level = 0

            Registry.getItem("pOutdoor_WeatherStation_Rain_State").postUpdateIfDifferent(rain_level)

        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Speed"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Direction")
    ]
)
class Wind:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        direction = Registry.getItemState("pOutdoor_WeatherStation_Wind_Direction").intValue()

        if direction >= 338 or direction < 23: 
            direction_long = "Nord"
            direction_short = "N"
        elif direction < 68: 
            direction_long = "Nordost"
            direction_short = "NO"
        elif direction < 113: 
            direction_long = "Ost"
            direction_short = "O"
        elif direction < 158: 
            direction_long = "Südost"
            direction_short = "SO"
        elif direction < 203: 
            direction_long = "Süd"
            direction_short = "S"
        elif direction < 248: 
            direction_long = "Südwest"
            direction_short = "SW"
        elif direction < 293: 
            direction_long = "West"
            direction_short = "W"
        elif direction < 338: 
            direction_long = "Nordwest"
            direction_short = "NW"
        else:
            direction_long = ""
            direction_short = ""
        
        Registry.getItem("pOutdoor_WeatherStation_Wind_Direction_Long").postUpdateIfDifferent(direction_long)
        Registry.getItem("pOutdoor_WeatherStation_Wind_Direction_Short").postUpdateIfDifferent(direction_short)
        
        if Registry.getItemState("pOutdoor_WeatherStation_Wind_Speed").doubleValue() == 0:
            msg = "Ruhig"
        else:
            msg = "{} km/h, {}".format(Registry.getItemState("pOutdoor_WeatherStation_Wind_Speed").format("%.1f"),direction_long)

        Registry.getItem("pOutdoor_WeatherStation_Wind_Message").postUpdateIfDifferent(msg)

        self.update_timer = None
        
    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        GenericCronTrigger("0 */5 * * * ?")
    ]
)
class UpdateWind:
    def execute(self, module, input):
        now = datetime.now().astimezone()

        value = ToolboxHelper.getMaximumSince("pOutdoor_WeatherStation_Wind_Gust", now - timedelta(minutes=15)).doubleValue()
        Registry.getItem("pOutdoor_WeatherStation_Wind_Gust_15Min").postUpdateIfDifferent(value)

        value = ToolboxHelper.getMaximumSince("pOutdoor_WeatherStation_Wind_Gust", now - timedelta(minutes=60)).doubleValue()
        Registry.getItem("pOutdoor_WeatherStation_Wind_Gust_1h").postUpdateIfDifferent(value)

        value = ToolboxHelper.getMaximumSince("pOutdoor_WeatherStation_Wind_Speed", now - timedelta(minutes=15)).doubleValue()
        Registry.getItem("pOutdoor_WeatherStation_Wind_Speed_15Min").postUpdateIfDifferent(value)

        value = ToolboxHelper.getMaximumSince("pOutdoor_WeatherStation_Wind_Speed", now - timedelta(minutes=60)).doubleValue()
        Registry.getItem("pOutdoor_WeatherStation_Wind_Speed_1h").postUpdateIfDifferent(value)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity")
    ]
)
class Air:
    def __init__(self):
        self.update_timer = None

    def calculateDewpoint(self,temperature,humidity):
        # https://rechneronline.de/barometer/taupunkt.php
        if temperature>0:
            k2=17.62
            k3=243.12
        else:
            k2=22.46
            k3=272.62
            
        #var erg=k3*((k2*t)/(k3+t)+Math.log(l/100))/((k2*k3)/(k3+t)-Math.log(l/100));
        dewpoint=k3*((k2*temperature)/(k3+temperature)+math.log(humidity/100.0))/((k2*k3)/(k3+temperature)-math.log(humidity/100.0))

        # https://www.corak.ch/service/taupunkt-rechner.html
        #ai=7.45;
        #bi=235;
        #z1=(ai*temperature)/(bi+temperature)
        #es=6.1*math.exp(z1*2.3025851)
        #e=es*humidity/100
        #z2=e/6.1
        #z3=0.434292289*math.log(z2)
        #dewpoint=(235*z3)/(7.45-z3)*100
        #dewpoint=math.floor(dewpoint)/100

        Registry.getItem("pOutdoor_WeatherStation_Dewpoint").postUpdateIfDifferent(round(dewpoint,1))
        
    def delayUpdate(self):
        temperature = round(Registry.getItemState("pOutdoor_WeatherStation_Temperature").doubleValue(),1)
        temperature_perceived = round(Registry.getItemState("pOutdoor_WeatherStation_Temperature_Perceived").doubleValue(),1)
        humidity = Registry.getItemState("pOutdoor_WeatherStation_Humidity").intValue()
        
        self.calculateDewpoint(temperature,humidity)
              
        msg = "";
        msg = "{}{} ({}) °C, ".format(msg,temperature, temperature_perceived)
        msg = "{}{} %".format(msg,humidity)

        Registry.getItem("pOutdoor_WeatherStation_Air_Message").postUpdateIfDifferent(msg)
        
        self.update_timer = None
        self.solarUpdate = None
        self.temperatureUpdate = None

    def execute(self, module, input):
        # delay to take care of the latest pOutdoor_WeatherStation_Solar_Power_Raw update
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Light_Level")
    ]
)
class CloudCover:
    def execute(self, module, input):
        max_lux = Registry.getItemState("pOutdoor_Astro_Light_Level").doubleValue()

        octa = Registry.getItemState("pOutdoor_Weather_Current_Cloud_Cover").doubleValue()
        if max_lux > 10000:
            lux = ToolboxHelper.getStableState("pOutdoor_WeatherStation_Light_Level", 10).doubleValue()
            if lux < max_lux:
                ratio = lux * 6.0 / max_lux
                _octa = 6.0 - ratio
            else:
                _octa = 0.0

            if _octa > octa:
                octa = _octa

        Registry.getItem("pOutdoor_WeatherStation_Cloud_Cover").postUpdateIfDifferent(octa)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Speed_15Min"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_Solar_Power")
    ]
)
class PerceivedTemperature:
    def getWindchill(self, temp, speed):
        # https://de.wikipedia.org/wiki/Windchill

        #return 33 + ( 0.478 + 0.237 * math.sqrt(speed) - 0.0124 * speed ) * ( temp - 33 )
        return 13.12 + 0.6215 * temp + ( 0.3965 * temp - 11.37 ) * speed**0.16

    def getHeatindex(self, temp, humidity):
        # https://de.wikipedia.org/wiki/Hitzeindex
        return -8.784695 + 1.61139411 * temp + 2.338549 * humidity - 0.14611605 * temp * humidity - 0.012308094 * temp**2 - 0.016424828 * humidity**2 + 0.002211732 * temp**2 * humidity + 0.00072546 * temp * humidity**2 - 0.000003582 * temp**2 * humidity**2

    def execute(self, module, input):
        item_name = input['event'].getItemName()
        item_value = input['event'].getItemState().doubleValue()

        temp = item_value if item_name == "pOutdoor_WeatherStation_Temperature" else Registry.getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
        speed = item_value if item_name == "pOutdoor_WeatherStation_Wind_Speed_15Min" else Registry.getItemState("pOutdoor_WeatherStation_Wind_Speed_15Min").doubleValue()
        #humidity = item_value if item_name == "pOutdoor_Weather_Current_Humidity" else Registry.getItemState("pOutdoor_Weather_Current_Humidity").doubleValue()
        humidity = item_value if item_name == "pOutdoor_WeatherStation_Humidity" else Registry.getItemState("pOutdoor_WeatherStation_Humidity").doubleValue()
        solar = item_value if item_name == "pOutdoor_WeatherStation_Solar_Power" else Registry.getItemState("pOutdoor_WeatherStation_Solar_Power").doubleValue()
        provider = Registry.getItemState("pOutdoor_Weather_Current_Temperature_Perceived").doubleValue()

        wind_chill_temp = self.getWindchill(temp, speed) if temp <= 10 and speed >= 5 else temp
        head_index_temp = self.getHeatindex(temp, humidity) if temp >= 22 else temp


        wind_chill_diff = wind_chill_temp - temp
        head_index_diff = head_index_temp - temp
        radiation_factor = 1.2 if solar > 800 else 1.0 + ( solar * 0.2 / 800 )

        old_calculated = ( temp + wind_chill_diff + head_index_diff ) * radiation_factor
        #self.logger.info("Current: {}, Provider: {}, Calculated: {}, Windchill: {}, Heatindex: {}, Factor: {}".format(temp, provider, calculated, wind_chill_diff, head_index_diff, radiation_factor))
        #postUpdateIfDifferent("pOutdoor_WeatherStation_Temperature_Perceived", calculated)
        #self.logger.info("=>: {}".format(calculated))


        # https://de.planetcalc.com/2089/

        Ta = temp
        e = ( humidity / 100 ) * 6.105 * math.exp( ( 17.27 * temp ) / ( 237.7 + temp ) )
        ws = (speed * 1000) / (60 * 60)
        Q = solar
        calculated = Ta + (0.348 * e) - (0.7 * ws) + ( 0.7 * ( Q / ( ws + 10 ) )) - 4.25
        _calculated = Ta + (0.348 * e) - (0.7 * ws) - 4.25

        self.logger.info("TEMP: {}°C, HUMIDITY: {}%, SPEED: {}m/s, Solar: {}w/m², CALCULATED 1: {}°C, CALCULATED 2: {}°C, PROVIDER: {}°C, OLD_CALCULATED: {}°C".format(temp, humidity, ws, solar, calculated, _calculated, provider, old_calculated))
        Registry.getItem("pOutdoor_WeatherStation_Temperature_Perceived").postUpdateIfDifferent(calculated)

@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_WeatherStation_MainSensor_Battery_Low"),
        ItemStateChangeTrigger("pOutdoor_WeatherStation_TemperatureSensor_Battery_Low")
    ]
)
class BatteryDetail:
    def execute(self, module, input):
        if input['event'].getItemState() == scope.ON:
            Registry.getItem("pOutdoor_WeatherStation_State_Device_Info").postUpdateIfDifferent("Batterie")
        else:
            Registry.getItem("pOutdoor_WeatherStation_State_Device_Info").postUpdateIfDifferent("Alles ok")
