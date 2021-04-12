from shared.helper import rule, getNow, getItemState, getStableItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, getItemLastUpdate, getItem, startTimer, createTimer, itemLastChangeOlderThen
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger
from custom.sun import SunRadiation

from org.joda.time import DateTime
import math
import json
import traceback

#value = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter",getNow()).intValue()
#postUpdate("pOutdoor_WeatherStation_Rain_Counter",value)

# base offset measured at 25°C
#OFFSET_TEMPERATURE  = 1.1
OFFSET_TEMPERATURE  = 1.1
# compensate heating from direct sunlight
# 1.2 °C negative temperature offset for each 10 °C diff between ntc and raw temperature
#LAZY_OFFSET_TEMPERATURE  = 1.2
LAZY_OFFSET_TEMPERATURE  = 2.0

OFFSET_WIND_DIRECTION = -135

OFFSET_NTC = -0.1

#http://www.conversion-website.com/power/Celsius-heat-unit-IT-per-minute-to-watt.html
#CELSIUS_HEAT_UNIT = 31.6516756
CELSIUS_HEAT_UNIT = 22

#https://cdn.sparkfun.com/assets/3/9/d/4/1/designingveml6075.pdf
#UVA_RESPONSE_FACTOR = 0.001461
#UVB_RESPONSE_FACTOR = 0.002591
UVA_RESPONSE_FACTOR = 0.001461
UVB_RESPONSE_FACTOR = 0.002591

UVA_CORRECTION_FACTOR = 0.5 # behind glass
UVB_CORRECTION_FACTOR = 0.5 # behind glass

DELAYED_UPDATE_TIMEOUT = 3

fuelLevel =[
  [ 2800, 0 ],
  [ 3375, 7 ],
  [ 3500, 14 ],
  [ 3625, 50 ],
  [ 4200, 100 ]
];

fuelLevelOld =[
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

def addToStack(self,stackName,itemValue):
    value = getItemState(stackName).toString()
    if value == "NULL":
        stack = []
    else:
        stack = json.loads(value)
        
    if itemValue == None:
        # avoid adding None twice
        if stack[len(stack)-1][1] == None:
            return
        stack = [ [ getNow().getMillis(), itemValue ] ]
    else:
        stack.append([getNow().getMillis(),itemValue])
        if len(stack) > 5:
            stack = stack[-5:]
        
    #self.log.info(u"Save {}: {}".format(stackName,json.dumps(stack)))
    postUpdate(stackName,json.dumps(stack))
    return stack

def getAvgStackValue(self,stackName,itemName):
    value = getItemState(stackName).toString()
    if value == "NULL":
        self.log.warn(u"Fallback {}".format(stackName))
        stack = addToStack(self,stackName,getItemState(itemName).doubleValue())
    else:
        stack = json.loads(value)
        
    maxTimestamp = getNow().getMillis() + 60000
    minTimestamp = maxTimestamp - 5 * 60 * 1000
    currentTimestamp = maxTimestamp
    
    avgValue = 0
    for index, x in enumerate( reversed(stack) ): 
        if x[1] == None:
            break
        fromTimestamp = x[0] if x[0] > minTimestamp else minTimestamp
        avgValue += x[1] * ( currentTimestamp - fromTimestamp )
        currentTimestamp = fromTimestamp
        if currentTimestamp == minTimestamp:
            break
          
    # return immediately if:
    # - value timestamp == maxTimestamp
    # - last value is None
    if maxTimestamp == currentTimestamp:
        return stack[len(stack)-1][1]
      
    #self.log.info(u"{}".format(maxTimestamp))
    #self.log.info(u"{}".format(minTimestamp))
    #self.log.info(u"{}".format(currentTimestamp))
    #self.log.info(u"{}".format(json.dumps(stack)))
    avgValue = avgValue / (maxTimestamp - currentTimestamp)  

    #self.log.info(u"AVG {}: {}".format(stackName,avgValue))
    return avgValue
   
@rule("sensor_weatherstation.py")
class WeatherstationLastUpdateRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?")
        ]
        self.notified = False
        #solar3 = getAvgStackValue(self,"pOutdoor_WeatherStation_Solar_Power_Stack","pOutdoor_WeatherStation_Solar_Power_Raw")

    def execute(self, module, input):
        now = getNow().getMillis()
        
        newestUpdate = 0
        oldestUpdate = now
        items = getItem("gWeatherstationInputValues").getAllMembers()
        states = {}
        
        for item in items:
            _update = getItemLastUpdate(item).getMillis()
            if _update > newestUpdate:
                newestUpdate = _update
            if _update < oldestUpdate:
                oldestUpdate = _update
                #self.log.info("{} {}".format(item.getName(),getItemLastUpdate(item)))
                
            lastUpdate = getItemLastUpdate(item)
            minutes = round( (now - lastUpdate.getMillis() ) / 1000.0 / 60.0 )
            states[item.getName()] = [minutes,"{:.0f} min: {} ({})".format(minutes,item.getName(),getItemLastUpdate(item))]
        
        # Special handling for heating updates
        # Either the pOutdoor_WeatherStation_Rain_Heater_Request is updated every 15 minutes (heating inactive) or every minute (heating is active)
        # Or the pOutdoor_WeatherStation_Rain_Heater is updated every 5 minutes
        #_heaterValueUpdate = getItemLastUpdate("pOutdoor_WeatherStation_Rain_Heater").getMillis()
        #_heaterRequestUpdate = getItemLastUpdate("pOutdoor_WeatherStation_Rain_Heater_Request").getMillis()
        #_update = _heaterValueUpdate if _heaterValueUpdate > _heaterRequestUpdate else _heaterRequestUpdate
        #if _update > newestUpdate:
        #    newestUpdate = _update
        #if _update < oldestUpdate:
        #    oldestUpdate = _update
                
        newestUpdateInMinutes = (now - newestUpdate) / 1000.0 / 60.0
        newestUpdateInMinutes = round(newestUpdateInMinutes)
        newestUpdateInMinutesMsg = u"{:.0f}".format(newestUpdateInMinutes) if newestUpdateInMinutes >= 1 else u"<1"
        
        oldestUpdateInMinutes = (now - oldestUpdate) / 1000.0 / 60.0
        oldestUpdateInMinutes = round(oldestUpdateInMinutes)
        oldestUpdateInMinutesMsg = u"{:.0f}".format(oldestUpdateInMinutes) if oldestUpdateInMinutes >= 1 else u"<1"
        
        if newestUpdateInMinutesMsg != oldestUpdateInMinutesMsg:
            msg = u"{} bis {} min.".format(newestUpdateInMinutesMsg,oldestUpdateInMinutesMsg)
        else:
            msg = u"{} min.".format(newestUpdateInMinutesMsg)
            
        postUpdateIfChanged("pOutdoor_WeatherStation_Update_Message", msg)
        postUpdateIfChanged("pOutdoor_WeatherStation_Is_Working", ON if oldestUpdateInMinutes <= 60 else OFF)
        
        temperatureItemName = 'pOutdoor_WeatherStation_Temperature' if states['pOutdoor_WeatherStation_Temperature_Raw'][0] < 30 else 'pGF_Utilityroom_Heating_Temperature_Outdoor'
        postUpdateIfChanged("pOutdoor_WeatherStation_Temperature_Item_Name", temperatureItemName )
            
        if oldestUpdateInMinutes > 10:
            for state in states:
                self.log.debug(states[state][1])
        #        
        #    if not self.notified:
        #        self.log.error("Weatherstation has problems")
        #        self.notified = True
        #elif self.notified:
        #    self.log.error("Weatherstation is working")
        #    self.notified = False
        
@rule("sensor_weatherstation.py")
class WeatherstationBatteryRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Battery_Voltage"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Battery_Current")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        level = getItemState("pOutdoor_WeatherStation_Battery_Level").intValue()
        current = getItemState("pOutdoor_WeatherStation_Battery_Current").doubleValue()
            
        msg = u"";
        msg = u"{}{:.0f} %, ".format(msg,level)
        msg = u"{}{} mA".format(msg,getItemState("pOutdoor_WeatherStation_Battery_Current").intValue())

        postUpdateIfChanged("pOutdoor_WeatherStation_Battery_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Battery_Voltage":
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
                            level = int(round( ( ( x * (toPercentageLevel - fromPercentageLevel) ) / 100 ) + fromPercentageLevel ))
                            break
                          
            postUpdateIfChanged("pOutdoor_WeatherStation_Battery_Level", level)
         
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
        
@rule("sensor_weatherstation.py")
class WeatherstationRainHeaterRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("pOutdoor_WeatherStation_Rain_Heater_Request"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Heater")
        ]
        self.timer = None

    def disable(self):
        self.log.warn(u"Disable rain heater to avoid overheating")
        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Heater",OFF)
        self.timer = None
        
    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Heater":
            if input['event'].getItemState() == OFF:
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = None
        else:
            if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON and self.timer == None:
                self.timer = createTimer(self.log, 300,self.disable) # max 5 min
                self.timer.start()

            # heating requests are not handled like normal mqtt topics with a stateTopic and a commandTopic. Instead:
            # 1. the weather station is sending a pOutdoor_WeatherStation_Rain_Heater_Request
            # 2. openhab is answering this request with a mqtt response
            mqttActions = actions.get("mqtt","mqtt:broker:mosquitto")
            mqttActions.publishMQTT("mysensors-sub-1/1/4/1/0/2",u"{}".format(1 if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON else 0))

@rule("sensor_weatherstation.py")
class WeatherstationRainRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 0 * * ?"), # to reset daily counter at midnight
            ItemStateUpdateTrigger("pOutdoor_WeatherStation_Rain_Impulse"), # each count update must be used
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Rate"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Heater")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        todayRain = getItemState("pOutdoor_WeatherStation_Rain_Daily").doubleValue()
        rainLevel = getItemState("pOutdoor_WeatherStation_Rain_State").intValue()

        if rainLevel < 0:
            temperature = getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
            rainState = "Tau" if temperature >= 0 else "Raureif"
        elif rainLevel == 0:
            rainState = "Trocken"
        elif rainLevel < 3:
            rainState = "Leicht"
        elif rainLevel < 6:
            rainState = "Mittel"
        elif rainLevel < 9:
            rainState = "Stark"
        else:
            rainState = "Extrem"
            
        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State_Message", u"{} ({})".format(rainState,rainLevel))
      
        msg = u"";
        msg = u"{}{}".format(msg,"{} mm, ".format(todayRain) if todayRain > 0 else "" )
        msg = u"{}{} ({}), ".format(msg,rainState,rainLevel)
        msg = u"{}{}".format(msg,"An" if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON else "Aus" )

        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Message", msg)
        
    def execute(self, module, input):
        if 'event' not in input:
            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Daily", 0)
            # must be delayed, to give item update time to apply
            self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer)
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Heater":
            self.delayUpdate()
        else:
            if input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Impulse":
                impulseCount = input['event'].getItemState().intValue()
                
                if impulseCount == 0:
                    return
                  
                zaehlerNeu = getItemState("pOutdoor_WeatherStation_Rain_Counter").intValue()
                zaehlerNeu += impulseCount
                postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Counter", zaehlerNeu)
                
                todayRain = 0
                zaehlerAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter", getNow().withTimeAtStartOfDay()).intValue()
                if zaehlerAlt != zaehlerNeu:
                    differenz = zaehlerNeu - zaehlerAlt
                    if differenz < 0:
                        differenz = zaehlerNeu

                    todayRain = float(differenz) * 257.5 / 1000.0
                    todayRain = round(todayRain,1)
                postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Daily", todayRain)
            elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Rate":
                rateUpdate = input['event'].getItemState().intValue()
                
                if rateUpdate   <= 524:
                    rainLevel = 10
                elif rateUpdate   <= 1310:
                    rainLevel = 9
                elif rateUpdate   <= 3276:
                    rainLevel = 8
                elif rateUpdate   <= 8192:
                    rainLevel = 7
                elif rateUpdate   <= 20480:
                    rainLevel = 6
                elif rateUpdate   <= 51200:
                    rainLevel = 5
                elif rateUpdate   <= 128000:
                    rainLevel = 4
                elif rateUpdate   <= 320000:
                    rainLevel = 3
                elif rateUpdate   <= 800000:
                    rainLevel = 2
                elif rateUpdate   <= 2000000:
                    rainLevel = 1
                else:
                    rainLevel = 0                      
 
                if rainLevel > 0:
                    timeOffice = (11 - rainLevel) * 15
                    if itemLastChangeOlderThen("pOutdoor_WeatherStation_Rain_Counter", getNow().minusMinutes(timeOffice)):
                        temperature = getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
                        dewpoint = getItemState("pOutdoor_WeatherStation_Dewpoint").doubleValue()
                        if temperature - dewpoint <= 3:
                            rainLevel = rainLevel * -1

                postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State", rainLevel)
                
            self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers) - 1)

@rule("sensor_weatherstation.py")
class WeatherstationRainLastHourRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 */15 * * * ?")]

    def execute(self, module, input):
        zaehlerNeu = getItemState("pOutdoor_WeatherStation_Rain_Counter").intValue()
        zaehlerAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter", getNow().minusHours(1)).intValue()
        lastHourRain = 0

        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            lastHourRain = float(differenz) * 257.5 / 1000.0
            #0.2575
            #0.2794 mm

        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Current", lastHourRain)
        
@rule("sensor_weatherstation.py")
class WeatherstationWindRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Speed"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Direction_Raw")
        ]

        self.updateTimer = None

    def delayUpdate(self):
        direction = getItemState("pOutdoor_WeatherStation_Wind_Direction").intValue()

        if direction >= 338 or direction < 23: 
            directionMsg = u"Nord"
        elif direction < 68: 
            directionMsg = u"Nordost"
        elif direction < 113: 
            directionMsg = u"Ost"
        elif direction < 158: 
            directionMsg = u"Südost"
        elif direction < 203: 
            directionMsg = u"Süd"
        elif direction < 248: 
            directionMsg = u"Südwest"
        elif direction < 293: 
            directionMsg = u"West"
        elif direction < 338: 
            directionMsg = u"Nordwest"
        else:
            directionMsg = u""
        
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Direction_Message", directionMsg)
        
        if getItemState("pOutdoor_WeatherStation_Wind_Speed").doubleValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("pOutdoor_WeatherStation_Wind_Speed").format("%.1f"),directionMsg)

        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Message", msg)

        self.updateTimer = None
        
    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Wind_Direction_Raw":
            direction = input['event'].getItemState().intValue() + OFFSET_WIND_DIRECTION
            if direction > 360:
                direction -= 360
            elif direction < 0:
                direction += 360
            postUpdate("pOutdoor_WeatherStation_Wind_Direction",direction)            
          
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
  
@rule("sensor_weatherstation.py")
class UpdateWindLast15MinutesRule:
    def __init__(self):
        self.triggers = [
          CronTrigger("0 */5 * * * ?")
        ]

    def execute(self, module, input):
        value = getMaxItemState("pOutdoor_WeatherStation_Wind_Speed", getNow().minusMinutes(15)).doubleValue()
        
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Current", value)
        
@rule("sensor_weatherstation.py")
class WeatherstationAirRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature_Raw"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity_Raw"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Solar_Temperature_Raw")
        ]
        self.updateTimer = None
        self.temperatureUpdate = None
        self.solarUpdate = None
        
    def calculateSolarPower(self):
        if getItemState("pOutdoor_WeatherStation_Light_Level").intValue() > 500:
            solar_temperature = getItemState("pOutdoor_WeatherStation_Solar_Temperature_Raw").doubleValue() + OFFSET_NTC
            outdoor_temperature = getItemState("pOutdoor_WeatherStation_Temperature_Raw").doubleValue()
            if outdoor_temperature > -100 and outdoor_temperature < 100:
                if solar_temperature < outdoor_temperature:
                    postUpdateIfChanged("pOutdoor_WeatherStation_Solar_Power", 0)
                else:
                    diff = solar_temperature - outdoor_temperature
                    power = diff * CELSIUS_HEAT_UNIT
                    postUpdateIfChanged("pOutdoor_WeatherStation_Solar_Power", round(power,1))
                    
            if self.solarUpdate != None:
                addToStack(self,"pOutdoor_WeatherStation_Solar_Temperature_Stack",solar_temperature)  
        else:
            if self.solarUpdate != None:
                addToStack(self,"pOutdoor_WeatherStation_Solar_Temperature_Stack",None)  
                
            postUpdateIfChanged("pOutdoor_WeatherStation_Solar_Power", 0)
            
        azimut = getItemState("pOutdoor_Astro_Sun_Azimuth").doubleValue()
        elevation = getItemState("pOutdoor_Astro_Sun_Elevation").doubleValue()
        _usedRadians = math.radians(elevation)
        if _usedRadians < 0.0: _usedRadians = 0.0
        
        # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
        # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
        _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
        if _maxRadiation < 0.0: _maxRadiation = 0.0
        
        postUpdateIfChanged("pOutdoor_WeatherStation_Solar_Power_Max", _maxRadiation)
        
    def calculateTemperature(self):          
        # don't add invalid values to stack
        if self.temperatureUpdate != None and self.temperatureUpdate > -100 and self.temperatureUpdate < 100:
            addToStack(self,"pOutdoor_WeatherStation_Temperature_Stack",self.temperatureUpdate)
          
        temperature = getAvgStackValue(self,"pOutdoor_WeatherStation_Temperature_Stack","pOutdoor_WeatherStation_Temperature_Raw")
        solar_temperature = getAvgStackValue(self,"pOutdoor_WeatherStation_Solar_Temperature_Stack","pOutdoor_WeatherStation_Solar_Temperature_Raw")

        if solar_temperature != None and solar_temperature > temperature:
            offset = (solar_temperature - temperature) * LAZY_OFFSET_TEMPERATURE / 10.0
            temperature = temperature - offset
        temperature = round(temperature + OFFSET_TEMPERATURE, 1)
        postUpdateIfChanged("pOutdoor_WeatherStation_Temperature",temperature)

        # only temporary for debugging
        postUpdateIfChanged("pOutdoor_WeatherStation_SolarDiffCurrent", ( solar_temperature - temperature ) / 10.0 if solar_temperature != None else 0 )
 
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

        postUpdateIfChanged("pOutdoor_WeatherStation_Dewpoint", round(dewpoint,1))
        
    def delayUpdate(self):
        # we need to calculate only if we have outdoor or solar temperature changes
        if self.solarUpdate != None or self.temperatureUpdate != None:
            self.calculateSolarPower()
            self.calculateTemperature()
        
        temperature = round(getItemState("pOutdoor_WeatherStation_Temperature").doubleValue(),1)
        humidity = getItemState("pOutdoor_WeatherStation_Humidity").intValue()
        
        self.calculateDewpoint(temperature,humidity)
              
        msg = u"";
        msg = u"{}{} °C, ".format(msg,temperature)
        msg = u"{}{}.0 %".format(msg,humidity)

        postUpdateIfChanged("pOutdoor_WeatherStation_Air_Message", msg)
        
        self.updateTimer = None
        self.solarUpdate = None
        self.temperatureUpdate = None

    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Humidity_Raw":
            humidity = int(round(input['event'].getItemState().doubleValue()))
            if humidity > 0 and humidity <= 100:
                postUpdate("pOutdoor_WeatherStation_Humidity",humidity)
            else:
                self.log.warn(u"Fallback. Got wrong humidity value: {}".format(humidity))
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Solar_Temperature_Raw":
            self.solarUpdate = input['event'].getItemState().doubleValue()
        else:
            self.temperatureUpdate = input['event'].getItemState().doubleValue()
          
        # delay to take care of the latest pOutdoor_WeatherStation_Solar_Power_Raw update
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("sensor_weatherstation.py")
class UVIndexRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_UV_A_Raw"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_UV_B_Raw")
        ]

        self.updateTimer = None

    def delayUpdate(self):
        uva = getItemState("pOutdoor_WeatherStation_UV_A").doubleValue()
        uvb = getItemState("pOutdoor_WeatherStation_UV_B").doubleValue()
        
        uva_weighted = uva * UVA_RESPONSE_FACTOR;
        uvb_weighted = uvb * UVB_RESPONSE_FACTOR;
        uv_index = round( (uva_weighted + uvb_weighted) / 2.0, 1 );
        postUpdateIfChanged("pOutdoor_WeatherStation_UV_Index", uv_index)
      
        msg = u"";
        msg = u"{}{} (".format(msg,uv_index)
        msg = u"{}{:.0f} • ".format(msg,round(uva))
        msg = u"{}{:.0f})".format(msg,round(uvb))

        postUpdateIfChanged("pOutdoor_WeatherStation_UV_Message", msg)
        
        self.updateTimer = None

    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_UV_A_Raw":
            uva = input['event'].getItemState().doubleValue() * UVA_CORRECTION_FACTOR
            postUpdateIfChanged("pOutdoor_WeatherStation_UV_A", uva)
        else:
            uvb = input['event'].getItemState().doubleValue() * UVB_CORRECTION_FACTOR
            postUpdateIfChanged("pOutdoor_WeatherStation_UV_B", uvb)
          
        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
