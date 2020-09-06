from custom.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, getItemLastUpdate, getItem
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger
from core.actions import Mqtt

import math

OFFSET_TEMPERATURE  = 1.1
OFFSET_HUMIDITY     = 7.5
OFFSET_WIND_DIRECTION = 0

OFFSET_NTC = -0.1

#http://www.conversion-website.com/power/Celsius-heat-unit-IT-per-minute-to-watt.html
CELSIUS_HEAT_UNIT = 31.6516756

#https://cdn.sparkfun.com/assets/3/9/d/4/1/designingveml6075.pdf
#UVA_RESPONSE_FACTOR = 0.001461
#UVB_RESPONSE_FACTOR = 0.002591
UVA_RESPONSE_FACTOR = 0.001461
UVB_RESPONSE_FACTOR = 0.002591

UVA_CORRECTION_FACTOR = 0.5 # behind glass
UVB_CORRECTION_FACTOR = 0.5 # behind glass

fuelLevel =[
  [ 3270, 0 ],
  [ 3610, 5 ],
  [ 3690, 10 ],
  [ 3710, 15 ],
  [ 3730, 20 ],
  [ 3750, 25 ],
  [ 3770, 30 ],
  [ 3790, 35 ],
  [ 3800, 40 ],
  [ 3820, 45 ],
  [ 3840, 50 ],
  [ 3850, 55 ],
  [ 3870, 60 ],
  [ 3910, 65 ],
  [ 3950, 70 ],
  [ 3980, 75 ],
  [ 4020, 80 ],
  [ 4080, 85 ],
  [ 4110, 90 ],
  [ 4150, 95 ],
  [ 4200, 100 ]
];

@rule("sensor_weatherstation.py")
class WeatherstationLastUpdateRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?")
        ]

    def execute(self, module, input):
      
        lastUpdate = 0
        items = getItem("Weatherstation").getAllMembers()
        for item in items:
            _lastUpdate = getItemLastUpdate(item).getMillis()
            if _lastUpdate > lastUpdate:
                lastUpdate = _lastUpdate

        now = getNow().getMillis()
        
        minutes = math.ceil((now - lastUpdate) / 1000.0 / 60.0)
        
        postUpdateIfChanged("WeatherStation_Last_Update", minutes)
        postUpdateIfChanged("WeatherStation_Is_Working", 1 if minutes <= 17 else 0)
        
@rule("sensor_weatherstation.py")
class WeatherstationBatteryRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Battery_Voltage"),
            ItemStateChangeTrigger("WeatherStation_Battery_Current")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Battery_Voltage":
            level = 0.0
            voltage = input['event'].getItemState().doubleValue()
            if voltage > fuelLevel[0][0]:
                if voltage > fuelLevel[-1][0]:
                    level = 100.0
                else:
                    for i in range(1,len(fuelLevel)):
                        toVoltageLevel = fuelLevel[i][0]

                        if voltage < toVoltageLevel:
                            fromVoltageLevel = fuelLevel[i-1][0]

                            toPercentageLevel = fuelLevel[i][1]
                            fromPercentageLevel = fuelLevel[i-1][1]
                            
                            # toVoltageLevel - fromVoltageLevel => 100%
                            # voltage - fromVoltageLevel => X
                            x = ( (voltage - fromVoltageLevel) * 100 ) / (toVoltageLevel - fromVoltageLevel)
                            
                            # toPercentageLevel - fromPercentageLevel => 100%
                            # ?? => x
                            level = round( ( ( x * (toPercentageLevel - fromPercentageLevel) ) / 100 ) + fromPercentageLevel )
                            break
            postUpdateIfChanged("WeatherStation_Battery_Level", level)
        else:
            level = getItemState("WeatherStation_Battery_Level").intValue()
      
        msg = u"";
        msg = u"{}{:.0f} %, ".format(msg,level)
        msg = u"{}{} mA".format(msg,getItemState("WeatherStation_Battery_Current").format("%.1f"))

        postUpdateIfChanged("WeatherStation_Battery_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateUpdateTrigger("WeatherStation_Rain_Impulse"), # each count update must be used
            ItemStateChangeTrigger("WeatherStation_Rain_Rate"),
            ItemStateChangeTrigger("WeatherStation_Rain_Heater")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Rain_Rate":
            rainRate = input['event'].getItemState().intValue()
            
            if rainRate <= 524:
                rainLevel = 10
            elif rainRate <= 1310:
                rainLevel = 9
            elif rainRate <= 3276:
                rainLevel = 8
            elif rainRate <= 8192:
                rainLevel = 7
            elif rainRate <= 20480:
                rainLevel = 6
            elif rainRate <= 51200:
                rainLevel = 5
            elif rainRate <= 128000:
                rainLevel = 4
            elif rainRate <= 320000:
                rainLevel = 3
            elif rainRate <= 800000:
                rainLevel = 2
            elif rainRate <= 2000000:
                rainLevel = 1
            else:
                rainLevel = 0

            postUpdateIfChanged("WeatherStation_Rain_State", rainLevel)
        else:
            rainLevel = getItemState("WeatherStation_Rain_State").intValue()
            
        if input['event'].getItemName() == "WeatherStation_Rain_Impulse" and input['event'].getItemState().intValue() > 0:
            zaehlerNeu = getItemState("WeatherStation_Rain_Counter").intValue()
            zaehlerNeu += input['event'].getItemState().intValue()
            postUpdateIfChanged("WeatherStation_Rain_Counter", zaehlerNeu)
            
            todayRain = 0
            zaehlerAlt = getHistoricItemState("WeatherStation_Rain_Counter", getNow().withTimeAtStartOfDay()).intValue()
            if zaehlerAlt != zaehlerNeu:
                differenz = zaehlerNeu - zaehlerAlt
                if differenz < 0:
                    differenz = zaehlerNeu

                todayRain = float(differenz) * 295.0 / 1000.0
                todayRain = round(todayRain,1)
            postUpdateIfChanged("WeatherStation_Rain_Daily", todayRain)
        else:
            todayRain = getItemState("WeatherStation_Rain_Daily").intValue()

        if rainLevel == 0:
            rainState = "Trocken"
        elif rainLevel < 3:
            rainState = "Leicht"
        elif rainLevel < 6:
            rainState = "Mittel"
        elif rainLevel < 9:
            rainState = "Stark"
        else:
            rainState = "Extrem"
      
        msg = u"";
        msg = u"{}{}".format(msg,"{} mm, ".format(todayRain) if todayRain > 0 else "" )
        msg = u"{}{} ({}), ".format(msg,rainState,rainLevel)
        msg = u"{}{}".format(msg,"An" if getItemState("WeatherStation_Rain_Heater").intValue() == 1 else "Aus" )

        postUpdateIfChanged("WeatherStation_Rain_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainLastHourRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 * * * ?")]

    def execute(self, module, input):
        zaehlerNeu = getItemState("WeatherStation_Rain_Counter").intValue()
        zaehlerAlt = getHistoricItemState("WeatherStation_Rain_Counter", getNow().minusHours(1)).intValue()
        lastHourRain = 0

        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            lastHourRain = float(differenz) * 295.0 / 1000.0
            #0.2794 mm

        postUpdateIfChanged("WeatherStation_Rain_Current", lastHourRain)
        
@rule("sensor_weatherstation.py")
class WeatherstationRainHeaterRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("WeatherStation_Rain_Heater_Request")
        ]

    def execute(self, module, input):
        Mqtt.publish("mosquitto","mysensors-sub-1/1/4/1/0/2",getItemState("WeatherStation_Rain_Heater").toString());

@rule("sensor_weatherstation.py")
class WeatherstationWindRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Wind_Speed"),
            ItemStateChangeTrigger("WeatherStation_Wind_Direction_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Wind_Direction_Raw":
            direction = input['event'].getItemState().intValue() + OFFSET_WIND_DIRECTION
            if direction > 360:
                direction -= 360
            postUpdate("WeatherStation_Wind_Direction",direction)            
        else:
            direction = getItemState("WeatherStation_Wind_Direction").intValue()

        if direction >= 338 or direction < 23: 
             direction = "Nord"
        elif direction < 68: 
            direction = "Nordost"
        elif direction < 113: 
            direction = "Ost"
        elif direction < 158: 
            direction = "Südost"
        elif direction < 203: 
            direction = "Süd"
        elif direction < 248: 
            direction = "Südwest"
        elif direction < 293: 
            direction = "West"
        elif direction < 338: 
            direction = "Nordwest"
        
        msg = u""
        if getItemState("WeatherStation_Wind_Speed").intValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("WeatherStation_Wind_Speed").format("%.1f"),direction)

        postUpdateIfChanged("WeatherStation_Wind_Message", msg)
  
@rule("sensor_weatherstation.py")
class WeatherstationAirRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature_Raw"),
            ItemStateChangeTrigger("WeatherStation_Humidity_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Temperature_Raw":
            temperature = round(input['event'].getItemState().doubleValue() + OFFSET_TEMPERATURE, 1)
            postUpdate("WeatherStation_Temperature",temperature)
            humidity = getItemState("WeatherStation_Humidity").format("%.1f")
        else:
            temperature = getItemState("WeatherStation_Temperature").format("%.1f")
            humidity = round(input['event'].getItemState().doubleValue() + OFFSET_HUMIDITY, 1)
            postUpdate("WeatherStation_Humidity",humidity)
      
        msg = u"";
        msg = u"{}{} °C, ".format(msg,temperature)
        msg = u"{}{} %".format(msg,humidity)

        postUpdateIfChanged("WeatherStation_Air_Message", msg)

@rule("sensor_weatherstation.py")
class SunPowerRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Solar_Power_Raw")
        ]

    def execute(self, module, input):
        if getItemState("WeatherStation_Light_Level").intValue() > 500:
            solar_temperature = input['event'].getItemState().doubleValue() + OFFSET_NTC
            outdoor_temperature = getItemState("WeatherStation_Temperature").doubleValue()
            if solar_temperature < outdoor_temperature:
                postUpdateIfChanged("WeatherStation_Solar_Power", 0)
            else:
                diff = solar_temperature - outdoor_temperature
                power = diff * CELSIUS_HEAT_UNIT
                postUpdateIfChanged("WeatherStation_Solar_Power", power)
        else:
            postUpdateIfChanged("WeatherStation_Solar_Power", 0)
            
            
            
            
            
        azimut = getItemState("Sun_Azimuth").doubleValue()
        elevation = getItemState("Sun_Elevation").doubleValue()
        _usedRadians = math.radians(elevation)
        if _usedRadians < 0.0: _usedRadians = 0.0
        
        # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
        # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
        _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
        if _maxRadiation < 0.0: _maxRadiation = 0.0
        
        postUpdateIfChanged("WeatherStation_Solar_Power_Test2", _maxRadiation)

        # apply cloud cover
        _cloudCover = getItemState("Cloud_Cover_Current").doubleValue()
        if _cloudCover > 8.0: _cloudCover = 8.0
        _cloudCoverFactor = _cloudCover / 8.0
        _currentRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )
        
        postUpdateIfChanged("WeatherStation_Solar_Power_Test1", _currentRadiation)

        _messuredRadiation = getItemState("WeatherStation_Solar_Power").doubleValue()
        
        self.log.info(u"SolarPower messured: {}, calculated: {}".format(_messuredRadiation,_currentRadiation))
            
            
@rule("sensor_weatherstation.py")
class UVIndexRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_UV_A_Raw"),
            ItemStateChangeTrigger("WeatherStation_UV_B_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_UV_A_Raw":
            uva = input['event'].getItemState().doubleValue() * UVA_CORRECTION_FACTOR
            postUpdateIfChanged("WeatherStation_UV_A", uva)
            uvb = getItemState("WeatherStation_UV_B").doubleValue()
        else:
            uva = getItemState("WeatherStation_UV_A").doubleValue()
            uvb = input['event'].getItemState().doubleValue() * UVB_CORRECTION_FACTOR
            postUpdateIfChanged("WeatherStation_UV_B", uvb)
          
        uva_weighted = uva * UVA_RESPONSE_FACTOR;
        uvb_weighted = uvb * UVB_RESPONSE_FACTOR;
        uv_index = (uva_weighted + uvb_weighted) / 2.0;
        postUpdateIfChanged("WeatherStation_UV_Index", uv_index)
      
        msg = u"";
        msg = u"{}{} (".format(msg,round(uv_index,1))
        msg = u"{}{:.0f} • ".format(msg,round(uva))
        msg = u"{}{:.0f})".format(msg,round(uvb))

        postUpdateIfChanged("WeatherStation_UV_Message", msg)
