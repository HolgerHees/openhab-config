from custom.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger
from core.actions import Mqtt

import math

OFFSET_TEMPERATURE_1  = 0.0
OFFSET_HUMIDITY_1     = 0
OFFSET_TEMPERATURE_2  = 1.1
OFFSET_HUMIDITY_2     = 7.5
OFFSET_WIND_DIRECTION = 0

#http://www.conversion-website.com/power/Celsius-heat-unit-IT-per-minute-to-watt.html
CELSIUS_HEAT_UNIT = 31.6516756

#https://cdn.sparkfun.com/assets/3/9/d/4/1/designingveml6075.pdf
UVA_RESPONSE_FACTOR = 0.001461
UVB_RESPONSE_FACTOR = 0.002591

UVA_CORRECTION_FACTOR = 1.1 # behind glass
UVB_CORRECTION_FACTOR = 1.8 # behind glass

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
class WeatherstationBatteryRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Battery_Voltage"),
            ItemStateChangeTrigger("WeatherStation_Battery_Current")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Battery_Voltage":
            level = 0
            voltage = input['event'].getItemState().doubleValue()
            if voltage > fuelLevel[0][0]:
                if voltage > fuelLevel[-1][0]:
                    level = 100
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
                            level = ( ( x * (toPercentageLevel - fromPercentageLevel) ) / 100 ) + fromPercentageLevel
                            break
            postUpdateIfChanged("WeatherStation_Battery_Level", level)
        else:
            level = getItemState("WeatherStation_Battery_Level").intValue()
      
        msg = u"";
        msg = u"{}{}%, ".format(msg,level)
        msg = u"{}{}mA".format(msg,getItemState("WeatherStation_Battery_Current").format("%.1f"))

        postUpdateIfChanged("WeatherStation_Battery_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Rain_Counter"),
            ItemStateChangeTrigger("WeatherStation_Rain_State"),
            ItemStateChangeTrigger("WeatherStation_Rain_Heater")
        ]

    def execute(self, module, input):
        zaehlerNeu = getItemState("WeatherStation_Rain_Counter").intValue()
        zaehlerAlt = getHistoricItemState("WeatherStation_Rain_Counter", getNow().withTimeAtStartOfDay()).intValue()
        todayRain = 0
        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            todayRain = float(differenz) * 295.0 / 1000.0
            todayRain = round(todayRain * 10.0) / 10.0
        postUpdateIfChanged("WeatherStation_Rain_Daily", todayRain)

        if getItemState("WeatherStation_Rain_State").intValue() == 0:
            rainState = "Trocken"
        elif getItemState("WeatherStation_Rain_State").intValue() < 3:
            rainState = "Leicht"
        elif getItemState("WeatherStation_Rain_State").intValue() < 6:
            rainState = "Mittel"
        elif getItemState("WeatherStation_Rain_State").intValue() < 9:
            rainState = "Stark"
        else:
            rainState = "Extrem"
      
        msg = u"";
        msg = u"{}{}".format(msg,"{}mm, ".format(todayRain) if todayRain > 0 else "" )
        msg = u"{}{}, ".format(msg,rainState)
        msg = u"{}{}".format(msg,"An" if getItemState("WeatherStation_Rain_Heater").intValue() == 1 else "Aus" )

        postUpdateIfChanged("WeatherStation_Rain_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainCounterRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Rain_Amount")
        ]

    def execute(self, module, input):
        counter = getItemState("WeatherStation_Rain_Counter").intValue();
        counter += getItemState("WeatherStation_Rain_Amount").intValue();

        postUpdateIfChanged("WeatherStation_Rain_Counter", counter)

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
class WeatherstationAir1Rule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature1_Raw"),
            ItemStateChangeTrigger("WeatherStation_Humidity1_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Temperature1_Raw":
            temperature = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_TEMPERATURE_1, 1)
            postUpdate("WeatherStation_Temperature1",temperature)
            humidity = getItemState("WeatherStation_Humidity1").intValue()
        else:
            temperature = getItemState("WeatherStation_Temperature1").format("%.1f")
            humidity = input['event'].getItemState().intValue() + OFFSET_HUMIDITY_1
            postUpdate("WeatherStation_Humidity1",humidity)
      
        msg = u"";
        msg = u"{}{}°C, ".format(msg,temperature)
        msg = u"{}{}%".format(msg,humidity)

        postUpdateIfChanged("WeatherStation_Air1_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationAir2Rule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature2_Raw"),
            ItemStateChangeTrigger("WeatherStation_Humidity2_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Temperature2_Raw":
            temperature = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_TEMPERATURE_2, 1)
            postUpdate("WeatherStation_Temperature2",temperature)
            humidity = getItemState("WeatherStation_Humidity2").format("%.1f")
        else:
            temperature = getItemState("WeatherStation_Temperature2").format("%.1f")
            humidity = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_HUMIDITY_2, 1)
            postUpdate("WeatherStation_Humidity2",humidity)
      
        msg = u"";
        msg = u"{}{}°C, ".format(msg,temperature)
        msg = u"{}{}%".format(msg,humidity)

        postUpdateIfChanged("WeatherStation_Air2_Message", msg)

@rule("sensor_weatherstation.py")
class SunPowerRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Solar_Power_Raw")
        ]

    def execute(self, module, input):
        solar_temperature = input['event'].getItemState().doubleValue()
        outdoor_temperature = getItemState("WeatherStation_Temperature2").doubleValue()
        if solar_temperature < outdoor_temperature:
            postUpdateIfChanged("WeatherStation_Solar_Power", 0)
        else:
            diff = solar_temperature - outdoor_temperature
            power = diff * CELSIUS_HEAT_UNIT
            postUpdateIfChanged("WeatherStation_Solar_Power", power)
            
            
            
            
            
        azimut = getItemState("Sun_Azimuth").doubleValue()
        elevation = getItemState("Sun_Elevation").doubleValue()
        _usedRadians = math.radians(elevation)
        if _usedRadians < 0.0: _usedRadians = 0.0
        
        # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
        # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
        _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
        if _maxRadiation < 0.0: _maxRadiation = 0.0
        
        # apply cloud cover
        _cloudCover = getItemState("Cloud_Cover_Current").doubleValue()
        if _cloudCover > 8.0: _cloudCover = 8.0
        _cloudCoverFactor = _cloudCover / 8.0
        _currentRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )
        
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
        msg = u"{}{} (".format(msg,round(uv_index * 10.0) / 10.0)
        msg = u"{}{}a,".format(msg,round(uva * 10.0) / 10.0)
        msg = u"{}{}b)".format(msg,round(uvb * 10.0) / 10.0)

        postUpdateIfChanged("WeatherStation_UV_Message", msg)
