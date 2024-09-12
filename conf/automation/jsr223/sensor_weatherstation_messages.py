import math
import json
from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit

from shared.helper import rule, getItemState, getItemStateWithFallback, getStableItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, sendCommandIfChanged, getItemLastUpdate, getItem, startTimer, itemLastChangeOlderThen, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger


#value = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter",ZonedDateTime.now()).intValue()
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
        stack = [ [ ZonedDateTime.now().toInstant().toEpochMilli(), itemValue ] ]
    else:
        stack.append([ZonedDateTime.now().toInstant().toEpochMilli(),itemValue])
        if len(stack) > 5:
            stack = stack[-5:]
        
    #self.log.info(u"Save {}: {}".format(stackName,json.dumps(stack))).
    postUpdate(stackName,json.dumps(stack))
    return stack

def getAvgStackValue(self,stackName,itemName):
    value = getItemState(stackName).toString()
    if value == "NULL":
        self.log.warn(u"Fallback {}".format(stackName))
        stack = addToStack(self,stackName,getItemState(itemName).doubleValue())
    else:
        stack = json.loads(value)
        
    maxTimestamp = ZonedDateTime.now().toInstant().toEpochMilli() + 60000
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
   
@rule()
class SensorWeatherstationMessagesLastUpdate:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?")
        ]
        self.fallbackTimer = None
        #self.notified = False
        #solar3 = getAvgStackValue(self,"pOutdoor_WeatherStation_Solar_Power_Stack","pOutdoor_WeatherStation_Solar_Power_Raw")

    def execute(self, module, input):
        now = ZonedDateTime.now()
        
        newestUpdate = None
        oldestUpdate = None
        items = getItem("gWeatherstationInputValues").getAllMembers()
        states = {}
        
        for item in items:
            _update = getItemLastUpdate(item)
            if _update.year == 1970:
                continue

            if newestUpdate is None or _update.isAfter(newestUpdate):
                newestUpdate = _update

            if oldestUpdate is None or _update.isBefore(oldestUpdate):
                oldestUpdate = _update
                #self.log.info("{} {}".format(item.getName(),getItemLastUpdate(item)))
                
            lastUpdate = getItemLastUpdate(item)
            minutes = ChronoUnit.MINUTES.between(lastUpdate,now)
            states[item.getName()] = [minutes,"{:.0f} min: {} ({})".format(minutes,item.getName(),getItemLastUpdate(item))]
        
        # Special handling for heating updates
        # Either the pOutdoor_WeatherStation_Rain_Heater_Request is updated every 15 minutes (heating inactive) or every minute (heating is active)
        # Or the pOutdoor_WeatherStation_Rain_Heater is updated every 5 minutes
        #_heaterValueUpdate = getItemLastUpdate("pOutdoor_WeatherStation_Rain_Heater")
        #_heaterRequestUpdate = getItemLastUpdate("pOutdoor_WeatherStation_Rain_Heater_Request")
        #_update = _heaterValueUpdate if _heaterValueUpdate.isAfter(_heaterRequestUpdate) else _heaterRequestUpdate
        #if _update.isAfter(newestUpdate):
        #    newestUpdate = _update
        #if _update.isBefore(oldestUpdate):
        #    oldestUpdate = _update

        if newestUpdate is None or oldestUpdate is None:
            self.log.error("Update time calculation has a problem")
            return
                
        newestUpdateInMinutes = ChronoUnit.MINUTES.between(newestUpdate,now)
        newestUpdateInMinutesMsg = u"{:.0f}".format(newestUpdateInMinutes) if newestUpdateInMinutes >= 1 else u"<1"
        
        oldestUpdateInMinutes = ChronoUnit.MINUTES.between(oldestUpdate,now)
        oldestUpdateInMinutesMsg = u"{:.0f}".format(oldestUpdateInMinutes) if oldestUpdateInMinutes >= 1 else u"<1"
        
        if newestUpdateInMinutesMsg != oldestUpdateInMinutesMsg:
            msg = u"{} bis {} min.".format(newestUpdateInMinutesMsg,oldestUpdateInMinutesMsg)
        else:
            msg = u"{} min.".format(newestUpdateInMinutesMsg)
            
        postUpdateIfChanged("pOutdoor_WeatherStation_Update_Message", msg)

        is_working = oldestUpdateInMinutes <= 60
        postUpdateIfChanged("pOutdoor_WeatherStation_Is_Working", ON if is_working else OFF)
        postUpdateIfChanged("eOther_Error_WeatherStation_Message", "" if is_working else u"Keine Updates seit mehr als 60 Minuten")

        temperatureItemName = 'pOutdoor_WeatherStation_Temperature' if 'pOutdoor_WeatherStation_Temperature_Raw' in states and states['pOutdoor_WeatherStation_Temperature_Raw'][0] < 30 else 'pGF_Utilityroom_Heating_Temperature_Outdoor'
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

        if oldestUpdateInMinutes > 30:
            if self.fallbackTimer is None:
                sendCommandIfChanged("pMobile_Socket_8_Powered", OFF)
                NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"Weatherstation", u"Fallback switched off")
                self.fallbackTimer = startTimer(self.log, 30, self.fallbackReactivation)
        else:
            self.fallbackTimer = None

    def fallbackReactivation(self):
        sendCommandIfChanged("pMobile_Socket_8_Powered", ON)
        NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_NOTICE, u"Weatherstation", u"Fallback switched on")

#@rule()
#class WeatherstationBattery:
#    def __init__(self):
#        self.triggers = [
#            #CronTrigger("0/5 * * * * ?"),
#            ItemStateChangeTrigger("pOutdoor_WeatherStation_Battery_Voltage"),
#            ItemStateChangeTrigger("pOutdoor_WeatherStation_Battery_Current")
#        ]
#        self.updateTimer = None

#    def delayUpdate(self):
#        level = getItemState("pOutdoor_WeatherStation_Battery_Level").intValue()
#        current = getItemState("pOutdoor_WeatherStation_Battery_Current").doubleValue()
            
#        msg = u"";
#        msg = u"{}{:.0f} %, ".format(msg,level)
#        msg = u"{}{} mA".format(msg,getItemState("pOutdoor_WeatherStation_Battery_Current").intValue())

#        postUpdateIfChanged("pOutdoor_WeatherStation_Battery_Message", msg)
        
#        self.updateTimer = None

#    def execute(self, module, input):
#        if input['event'].getItemName() == "pOutdoor_WeatherStation_Battery_Voltage":
#            level = 0.0
#            voltage = input['event'].getItemState().doubleValue()
#            if voltage > fuelLevel[0][0]:
#                if voltage > fuelLevel[-1][0]:
#                    level = 100.0
#                else:
#                    for i in range(1,len(fuelLevel)):
#                        toVoltageLevel = fuelLevel[i][0]

#                        if voltage < toVoltageLevel:
#                            fromVoltageLevel = fuelLevel[i-1][0]

#                            toPercentageLevel = fuelLevel[i][1]
#                            fromPercentageLevel = fuelLevel[i-1][1]
                            
#                            # toVoltageLevel - fromVoltageLevel => 100%
#                            # voltage - fromVoltageLevel => X
#                            x = ( (voltage - fromVoltageLevel) * 100 ) / (toVoltageLevel - fromVoltageLevel)
                            
#                            # toPercentageLevel - fromPercentageLevel => 100%
#                            # ?? => x
#                            level = int(round( ( ( x * (toPercentageLevel - fromPercentageLevel) ) / 100 ) + fromPercentageLevel ))
#                            break
                          
#            postUpdateIfChanged("pOutdoor_WeatherStation_Battery_Level", level)
         
#        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
        
@rule()
class SensorWeatherstationMessagesRainHeater:
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
                self.timer = startTimer(self.log, 300,self.disable) # max 5 min

            # heating requests are not handled like normal mqtt topics with a stateTopic and a commandTopic. Instead:
            # 1. the weather station is sending a pOutdoor_WeatherStation_Rain_Heater_Request
            # 2. openhab is answering this request with a mqtt response
            mqttActions = actions.get("mqtt","mqtt:broker:mosquitto")
            mqttActions.publishMQTT("mysensors-sub-1/1/4/1/0/2",u"{}".format(1 if getItemState("pOutdoor_WeatherStation_Rain_Heater") == ON else 0))

@rule()
class SensorWeatherstationMessagesRain:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 0 0 * * ?"), # to reset daily counter at midnight
            ItemStateUpdateTrigger("pOutdoor_WeatherStation_Rain_Impulse"), # each count update must be used
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Rate"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Rain_Heater")
        ]
        self.updateTimer = None

        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State", 0)

    def delayUpdate(self):
        todayRain = getItemStateWithFallback("pOutdoor_WeatherStation_Rain_Daily",DecimalType(0.0)).doubleValue()
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
        if input['event'].getType() == "TimerEvent":
            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Daily", 0)
            # must be delayed, to give item update time to apply
            self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer)
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Heater":
            self.delayUpdate()
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Impulse":
            impulseCount = input['event'].getItemState().intValue()
            if impulseCount == 0:
                return

            zaehlerNeu = getItemStateWithFallback("pOutdoor_WeatherStation_Rain_Counter",DecimalType(0)).intValue()
            zaehlerNeu += impulseCount
            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Counter", zaehlerNeu)

            todayRain = 0
            refDay = ZonedDateTime.now()
            zaehlerAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter", refDay.toLocalDate().atStartOfDay(refDay.getZone())).intValue()
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

            if rainLevel > 0 and getItemState("pOutdoor_Weather_Current_Humidity").doubleValue() >= 100:
                timeOffice = (11 - rainLevel) * 15
                if itemLastChangeOlderThen("pOutdoor_WeatherStation_Rain_Counter", ZonedDateTime.now().minusMinutes(timeOffice)):
                    temperature = getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
                    dewpoint = getItemState("pOutdoor_WeatherStation_Dewpoint").doubleValue()
                    if temperature - dewpoint <= 3 and getItemState("pOutdoor_Weather_Current_Humidity").doubleValue() >= 100:
                        rainLevel = rainLevel * -1

            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State", rainLevel)

        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers) - 1)

@rule()
class SensorWeatherstationMessagesRainLastHour:
    def __init__(self):
        self.triggers = [CronTrigger("0 */5 * * * ?")]

    def execute(self, module, input):
        zaehlerNeu = getItemStateWithFallback("pOutdoor_WeatherStation_Rain_Counter",DecimalType(0)).intValue()

        zaehlerAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter", ZonedDateTime.now().minusMinutes(15)).intValue()
        last15MinRain = 0
        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            last15MinRain = float(differenz) * 257.5 / 1000.0
            #0.2575
            #0.2794 mm
        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Current_15Min", last15MinRain)

        zaehlerAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Counter", ZonedDateTime.now().minusHours(1)).intValue()
        lastHourRain = 0
        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            lastHourRain = float(differenz) * 257.5 / 1000.0
            #0.2575
            #0.2794 mm
        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Current", lastHourRain)

@rule()
class SensorWeatherstationMessagesWind:
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
            directionLong = u"Nord"
            directionShort = u"N"
        elif direction < 68: 
            directionLong = u"Nordost"
            directionShort = u"NO"
        elif direction < 113: 
            directionLong = u"Ost"
            directionShort = u"O"
        elif direction < 158: 
            directionLong = u"Südost"
            directionShort = u"SO"
        elif direction < 203: 
            directionLong = u"Süd"
            directionShort = u"S"
        elif direction < 248: 
            directionLong = u"Südwest"
            directionShort = u"SW"
        elif direction < 293: 
            directionLong = u"West"
            directionShort = u"W"
        elif direction < 338: 
            directionLong = u"Nordwest"
            directionShort = u"NW"
        else:
            directionLong = u""
            directionShort = u""
        
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Direction_Long", directionLong)
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Direction_Short", directionShort)
        
        if getItemState("pOutdoor_WeatherStation_Wind_Speed").doubleValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("pOutdoor_WeatherStation_Wind_Speed").format("%.1f"),directionLong)

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

@rule()
class SensorWeatherstationMessagesUpdateWind:
    def __init__(self):
        self.triggers = [
          CronTrigger("0 */5 * * * ?")
        ]

    def execute(self, module, input):
        value = getMaxItemState("pOutdoor_WeatherStation_Wind_Gust", ZonedDateTime.now().minusMinutes(15)).doubleValue()
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Gust_15Min", value)

        value = getMaxItemState("pOutdoor_WeatherStation_Wind_Gust", ZonedDateTime.now().minusMinutes(60)).doubleValue()
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Gust_1h", value)

        value = getMaxItemState("pOutdoor_WeatherStation_Wind_Speed", ZonedDateTime.now().minusMinutes(15)).doubleValue()
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Speed_15Min", value)

        value = getMaxItemState("pOutdoor_WeatherStation_Wind_Speed", ZonedDateTime.now().minusMinutes(60)).doubleValue()
        postUpdateIfChanged("pOutdoor_WeatherStation_Wind_Speed_1h", value)

@rule()
class SensorWeatherstationMessagesAir:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature_Raw"),
            ItemStateChangeTrigger("pOutdoor_Weather_Current_Humidity"), # fallback until humidity sensor is fixed
            #ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity_Raw"),
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

        return temperature
 
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
            temperature = self.calculateTemperature()
        else:
            temperature = round(getItemState("pOutdoor_WeatherStation_Temperature").doubleValue(),1)

        humidity = getItemState("pOutdoor_WeatherStation_Humidity").intValue()
        
        self.calculateDewpoint(temperature,humidity)
              
        msg = u"";
        msg = u"{}{} °C, ".format(msg,temperature)
        msg = u"{}{} %".format(msg,humidity)

        postUpdateIfChanged("pOutdoor_WeatherStation_Air_Message", msg)
        
        self.updateTimer = None
        self.solarUpdate = None
        self.temperatureUpdate = None

    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_Weather_Current_Humidity":
        #if input['event'].getItemName() == "pOutdoor_WeatherStation_Humidity_Raw":
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

@rule()
class SensorWeatherstationPerceivedTemperature:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Light_Level")
        ]

        #self.calc()

    def calc(self):
        lux = getStableItemState(ZonedDateTime.now(),"pOutdoor_WeatherStation_Light_Level",10)
        #input['event'].getItemState().intValue()

        #pOutdoor_WeatherStation_Solar_Power
        maxLuminationRatio = getItemState("pOutdoor_WeatherStation_Solar_Power_Max").doubleValue() / 900
        maxLux = 50000 * maxLuminationRatio

        octa = getItemState("pOutdoor_Weather_Current_Cloud_Cover").doubleValue()
        #self.log.info("{}".format(octa))

        if maxLux > 10000:
            if lux < maxLux:
                ratio = lux * 6.0 / maxLux
                _octa = 6.0 - ratio
            else:
                _octa = 0.0
            if _octa > octa:
                octa = _octa

        #self.log.info("{}".format(octa))
        postUpdateIfChanged("pOutdoor_WeatherStation_Cloud_Cover", octa)

    def execute(self, module, input):
        self.calc()

@rule()
class SensorWeatherstationPerceivedTemperature:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Speed_15Min"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Solar_Power"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature_Perceived")
        ]

        self.calc(None, None)

    def getWindchill(self, temp, speed):
        # https://de.wikipedia.org/wiki/Windchill

        #return 33 + ( 0.478 + 0.237 * math.sqrt(speed) - 0.0124 * speed ) * ( temp - 33 )
        return 13.12 + 0.6215 * temp + ( 0.3965 * temp - 11.37 ) * speed**0.16

    def getHeatindex(self, temp, humidity):
        # https://de.wikipedia.org/wiki/Hitzeindex
        return -8.784695 + 1.61139411 * temp + 2.338549 * humidity - 0.14611605 * temp * humidity - 0.012308094 * temp**2 - 0.016424828 * humidity**2 + 0.002211732 * temp**2 * humidity + 0.00072546 * temp * humidity**2 - 0.000003582 * temp**2 * humidity**2

    def calc(self, item_name, item_value):
        temp = item_value if item_name == "pOutdoor_WeatherStation_Temperature" else getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
        speed = item_value if item_name == "pOutdoor_WeatherStation_Wind_Speed_15Min" else getItemState("pOutdoor_WeatherStation_Wind_Speed_15Min").doubleValue()
        #humidity = item_value if item_name == "pOutdoor_Weather_Current_Humidity" else getItemState("pOutdoor_Weather_Current_Humidity").doubleValue()
        humidity = item_value if item_name == "pOutdoor_WeatherStation_Humidity" else getItemState("pOutdoor_WeatherStation_Humidity").doubleValue()
        solar = item_value if item_name == "pOutdoor_WeatherStation_Solar_Power" else getItemState("pOutdoor_WeatherStation_Solar_Power").doubleValue()
        provider = getItemState("pOutdoor_Weather_Current_Temperature_Perceived").doubleValue()

        windChillTemp = self.getWindchill(temp, speed) if temp <= 10 and speed >= 5 else temp
        headIndexTemp = self.getHeatindex(temp, humidity) if temp >= 22 else temp


        windChillDiff = windChillTemp - temp
        headIndexDiff = headIndexTemp - temp
        radiationFactor = 1.2 if solar > 800 else 1.0 + ( solar * 0.2 / 800 )

        calculated = ( temp + windChillDiff + headIndexDiff ) * radiationFactor

        self.log.info("Current: {}, Provider: {}, Calculated: {}, Windchill: {}, Heatindex: {}, Factor: {}".format(temp, provider, calculated, windChillDiff, headIndexDiff, radiationFactor))

        postUpdateIfChanged("pOutdoor_WeatherStation_Temperature_Perceived", calculated)

    def execute(self, module, input):
        self.calc(input['event'].getItemName(), input['event'].getItemState().doubleValue())

#@rule()
#class SensorWeatherstationPerceivedTemperatureAlt:
#    def __init__(self):
#        self.triggers = [
#            ItemStateChangeTrigger("pOutdoor_Weather_Current_Temperature_Perceived")
#        ]

#        self.calc(None, None)

#    def calc(self, item_name, item_value):
#        provider = getItemState("pOutdoor_Weather_Current_Temperature_Perceived").doubleValue()

#        postUpdateIfChanged("pOutdoor_WeatherStation_Temperature_Perceived", provider)

#    def execute(self, module, input):
#        self.calc(input['event'].getItemName(), input['event'].getItemState().doubleValue())

@rule()
class SensorWeatherstationMessagesUVIndex:
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
