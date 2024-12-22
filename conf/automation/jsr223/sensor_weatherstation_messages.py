import math
import json
from java.time import ZonedDateTime
from java.time.temporal import ChronoUnit

from shared.helper import rule, getItemState, getItemStateWithFallback, getStableItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged, sendCommandIfChanged, getItemLastUpdate, getItem, startTimer, itemLastChangeOlderThen, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger

DELAYED_UPDATE_TIMEOUT = 3

@rule()
class SensorWeatherstationMessagesLastUpdate:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 * * * * ?")
        ]
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


@rule()
class SensorWeatherstationMessagesRain:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("pOutdoor_WeatherStation_Rain_Daily"),
            ItemStateUpdateTrigger("pOutdoor_WeatherStation_Rain_Rate")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        todayRain = getItemStateWithFallback("pOutdoor_WeatherStation_Rain_Daily",DecimalType(0.0)).doubleValue()
        rainLevel = getItemState("pOutdoor_WeatherStation_Rain_State").intValue()

        if rainLevel == 0:
            rainState = "Trocken"
        elif rainLevel < 3:
            rainState = "Leicht"
        elif rainLevel < 6:
            rainState = "Mittel"
        elif rainLevel < 8:
            rainState = "Stark"
        else:
            rainState = "Extrem"
            
        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State_Message", u"{} ({})".format(rainState,rainLevel))
      
        msg = u"";
        msg = u"{}{}".format(msg,"{} mm, ".format(todayRain) if todayRain > 0 else "" )
        msg = u"{}{} ({})".format(msg,rainState,rainLevel)

        postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Message", msg)
        
    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Daily":
            ammountNeu = getItemStateWithFallback("pOutdoor_WeatherStation_Rain_Daily",DecimalType(0.0)).doubleValue()
            ammountAlt = getHistoricItemState("pOutdoor_WeatherStation_Rain_Daily", ZonedDateTime.now().minusHours(1)).doubleValue()
            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_Hourly", ammountNeu - ammountAlt)
        elif input['event'].getItemName() == "pOutdoor_WeatherStation_Rain_Rate":
            rate = input['event'].getItemState().doubleValue()

            if rate > 100:
                rainLevel = 10
            elif rate > 50:     # > 50.0 violent
                rainLevel = 9
            elif rate > 25.6:   # max 50.0 heavy
                rainLevel = 8
            elif rate > 12.8:
                rainLevel = 7
            elif rate > 6.4:    # max 7.5 moderate
                rainLevel = 6
            elif rate > 3.2:
                rainLevel = 5
            elif rate > 1.6:    # max 2.5 light
                rainLevel = 4
            elif rate > 0.8:
                rainLevel = 3
            elif rate > 0.4:
                rainLevel = 2
            elif rate > 0:
                rainLevel = 1
            else:
                rainLevel = 0

            postUpdateIfChanged("pOutdoor_WeatherStation_Rain_State", rainLevel)

        self.updateTimer = startTimer(self.log, DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers) - 1)

@rule()
class SensorWeatherstationMessagesWind:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Speed"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Wind_Direction")
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
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Temperature"),
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Humidity")
        ]
        self.updateTimer = None

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
        maxLux = getItemState("pOutdoor_Astro_Light_Level").doubleValue()

        octa = getItemState("pOutdoor_Weather_Current_Cloud_Cover").doubleValue()
        if maxLux > 10000:
            lux = getStableItemState(ZonedDateTime.now(),"pOutdoor_WeatherStation_Light_Level",10)
            if lux < maxLux:
                ratio = lux * 6.0 / maxLux
                _octa = 6.0 - ratio
            else:
                _octa = 0.0

            if _octa > octa:
                octa = _octa

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
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Solar_Power")
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

@rule()
class SensorWeatherstationBatteryDetail:
    def __init__(self):
        triggers = [
            ItemStateChangeTrigger("pOutdoor_WeatherStation_Battery_Low")
        ]

    def execute(self, module, input):
        if input['event'].getItemState() == ON:
            postUpdateIfChanged("pOutdoor_WeatherStation_State_Device_Info", "Batterie")
        else:
            postUpdateIfChanged("pOutdoor_WeatherStation_State_Device_Info", "Alles ok")
