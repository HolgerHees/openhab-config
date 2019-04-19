import time
import math
from org.joda.time import DateTime, DateTimeZone
from org.joda.time.format import DateTimeFormat

from marvin.helper import rule, getNow, getGroupMember, itemLastUpdateOlderThen, getItemLastUpdate, getHistoricItemState, getHistoricItemEntry, getItemState, getMaxItemState, getItem, postUpdate, postUpdateIfChanged, sendCommand, createTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger
from core.actions import Transformation

OFFSET_FORMATTER = DateTimeFormat.forPattern("HH:mm")

BEDROOM_REDUCTION = 2.5
NIGHT_REDUCTION = 2.0
MIN_HEATING_TIME = 15 # 'Heizen mit WW' should be active at least for 15 min.
MIN_ONLY_WW_TIME = 15 # 'Nur WW' should be active at least for 15 min.
LAZY_OFFSET = 90 # Offset time until any heating has an effect

class HeatingHelper:
    stableReferences = {}
    outdatetForecast = None
    openFFContacts = None
    openSFContacts = None
    longOpenFFContacts = {}
    longOpenSFContacts = {}
    lastReferenceSource = None
    lastReferenceValue = 0.0
     
    def getStableValue( self, now, itemName, checkTimeRange, cached = False ):
        
        cacheKey = u"{}-{}".format(itemName,checkTimeRange)
         
        if cached:
            cacheValue = HeatingHelper.stableReferences.get( cacheKey )
            if cacheValue != None:
                return cacheValue
        
        currentEndTime = now
        currentEndTimeMillis = currentEndTime.getMillis()
        minTimeMillis = currentEndTimeMillis - ( checkTimeRange * 60 * 1000 )

        value = 0.0
        duration = 0

        # get and cache "real" item to speedup getHistoricItemEntry. Otherwise "getHistoricItemEntry" will lookup the item by its name every time
        item = getItem(itemName)
        
        while True:
            entry = getHistoricItemEntry(item, currentEndTime )

            currentStartMillis = entry.getTimestamp().getTime()

            if currentStartMillis < minTimeMillis:
                currentStartMillis = minTimeMillis

            _duration = currentEndTimeMillis - currentStartMillis
            _value = entry.getState().doubleValue()

            duration = duration + _duration
            value = value + ( _value * _duration )

            currentEndTimeMillis = currentStartMillis -1

            if currentEndTimeMillis < minTimeMillis:
                break

            currentEndTime = DateTime(currentEndTimeMillis)

        value = ( value / duration )

        cacheValue = HeatingHelper.stableReferences.get( cacheKey )
        
        if cacheValue != None:
            # warming up - avg should be 80% above the current level
            if value > cacheValue:
                # 21.07 => 21.0
                # 21.08 => 21.1
                value = round( value - 0.03, 1 )
            # cooling down - avg should be 80% below the current level
            else:
                # 21.01 => 21.0
                # 21.02 => 21.1
                value = round( value + 0.03, 1 )
        else:
            value = round( value, 1 )
            
        HeatingHelper.stableReferences[ cacheKey ] = value
        
        return value

    def isOutdatetForecast(self, cached = False):
        if cached == False or HeatingHelper.outdatetForecast is None:
            HeatingHelper.outdatetForecast = itemLastUpdateOlderThen("Temperature_Garden_Forecast4", getNow().minusMinutes(360) )
        return HeatingHelper.outdatetForecast

    def _getCloudData( self, cloudCoverItem ):
        if self.isOutdatetForecast(True):
            self.log.info(u"Forecast: ERROR • Fall back to full cloud cover.")
            return 9.0
        
        return getItemState(cloudCoverItem).doubleValue()

    def _getSunData( self, time ):

        # Constants                                                                                                                                                                                                                                 
        K = 0.017453                                                                                                                                                                                                                      

        # Change this reflecting your destination                                                                                                                                                                                                   
        latitude = 52.347767                                                                                                                                                                                                              
        longitude = 13.621287

        # allways +1 Berlin winter time
        local = time.toDateTime(DateTimeZone.forOffsetHours(1))

        day = local.getDayOfYear()
        hour = local.getHourOfDay() + (local.getMinuteOfHour()/60.0)

        # Source: http://www.jgiesen.de/SME/tk/index.htm
        deklination = -23.45 * math.cos( K * 360 * (day + 10) / 365 )
        zeitgleichung = 60.0 * (-0.171 * math.sin( 0.0337*day+0.465) - 0.1299 * math.sin( 0.01787*day-0.168))
        stundenwinkel = 15.0 * ( hour - (15.0-longitude)/15.0 - 12.0 + zeitgleichung/60.0)
        x = math.sin(K * latitude) * math.sin(K * deklination) + math.cos(K * latitude) * math.cos(K * deklination) * math.cos(K * stundenwinkel)
        y = - (math.sin(K*latitude) * x - math.sin(K*deklination)) / (math.cos(K*latitude) * math.sin(math.acos(x)))
        elevation = math.asin(x) / K

        isBreak = hour <= 12.0 + (15.0-longitude)/15.0 - zeitgleichung/60.0
        if isBreak: azimut = math.acos(y) / K
        else: azimut = 360.0 - math.acos(y) / K

        return elevation, azimut

    def getSunPowerPerMinute( self, logPrefix, activeRooms, referenceTime, cloudCoverItem, isForecast ):

        cloudCover = self._getCloudData( cloudCoverItem )
        elevation, azimut = self._getSunData( referenceTime )

        # 125° 1/2 der Hauswand	
        southMultiplier = 0
        if azimut >= 100 and azimut <= 260 and elevation >= 12.0:
            # 100° (0) => -1 (0)
            # 260° (160) => 1 (2)
            southX = ( ( azimut - 100.0 ) * 2.0 / 160.0 ) - 1.0
            southMultiplier = ( math.pow( southX, 10.0 ) * -1.0 ) + 1.0

        westMultiplier = 0
        if azimut >= 190 and azimut <= 350 and elevation >= 8.0:
            # https://rechneronline.de/funktionsgraphen/
            # 190° (0) => -1 (0)
            # 350° (160) => 1 (2)           
            westX = ( ( azimut - 190.0 ) * 2.0 / 160.0 ) - 1.0
            westMultiplier = ( math.pow( westX, 10.0 ) * -1.0 ) + 1.0

        southActive = southMultiplier > 0.0
        westActive  = westMultiplier > 0.0
        
        # in the morning the sun must be above 20°
        # and in the evening the sun must be above 10°
        if southActive or westActive:
            _usedRadians = math.radians(elevation)
            if _usedRadians < 0.0: _usedRadians = 0.0
            
            # Cloud Cover is between 0 and 9 - but converting to 0 and 8
            # https://en.wikipedia.org/wiki/Okta
            _cloudCover = cloudCover
            if _cloudCover > 8.0: _cloudCover = 8.0
            _cloudCoverFactor = _cloudCover / 8.0
            
            # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
            # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
            _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
            if _maxRadiation < 0.0: _maxRadiation = 0.0
            _currentRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )

            _activeRadiation = 0.0
            _effectiveSouthRadiation = _currentRadiation * 0.37 * southMultiplier
            _effectiveWestRadiation = _currentRadiation * 0.37 * westMultiplier
            
            # Südseite bis ca. 16 Uhr
            if _effectiveSouthRadiation > 0.0:
                # 0 means 0% down
                if isForecast or getItemState("Shutters_SF_Bathroom") == PercentType.ZERO:
                    _activeRadiation = _activeRadiation + ( ( 0.86 * 1.00 ) * _effectiveSouthRadiation )
                if isForecast or getItemState("Shutters_SF_Dressingroom") == PercentType.ZERO:
                    _activeRadiation = _activeRadiation + ( ( 0.86 * 1.00 ) * _effectiveSouthRadiation )

            # Westseite ab ca. 14 Uhr
            if _effectiveWestRadiation > 0.0:
                # 0 means 0% down
                if isForecast or getItemState("Shutters_SF_Bedroom") == PercentType.ZERO:
                   _activeRadiation = _activeRadiation + ( ( 0.615 * 1.00 * 3.0 ) * _effectiveWestRadiation )
                if isForecast or getItemState("Shutters_FF_Kitchen") == PercentType.ZERO:
                    _activeRadiation = _activeRadiation + ( ( 0.645 * 1.01 * 2.0 ) * _effectiveWestRadiation )
                    
                # exclude inactive rooms from sun power to exclude their effects from further calculation
                if activeRooms.get("livingroom"):
                    if isForecast or getItemState("Shutters_FF_Livingroom_Terrace") == PercentType.ZERO:
                        _activeRadiation = _activeRadiation + ( ( 0.625 * 2.13 * 3.0 ) * _effectiveWestRadiation )
                    if isForecast or getItemState("Shutters_FF_Livingroom_Couch") == PercentType.ZERO:
                        _activeRadiation = _activeRadiation + ( ( 0.655 * 2.13 * 2.0 ) * _effectiveWestRadiation )
            
            _activeRadiation = round( _activeRadiation / 60.0, 1 )
            _effectiveSouthRadiation = round( _effectiveSouthRadiation / 60.0, 1 )
            _effectiveWestRadiation = round( _effectiveWestRadiation / 60.0, 1 )

            activeDirections = []
            if southActive: activeDirections.append("S")
            if westActive: activeDirections.append("W")
            activeMsg = u" • {}".format("+".join(activeDirections))
        else:
            _activeRadiation = 0.0
            _effectiveSouthRadiation = 0.0
            _effectiveWestRadiation = 0.0

            activeMsg = u""
            
        sunElevationMsg = int( round( elevation, 0 ) )
        sunAzimutMsg = int( round( azimut, 0 ) )

        self.log.info(u"{} Azimut {}° • Elevation {}° • Clouds {} octas{}".format(logPrefix, sunAzimutMsg, sunElevationMsg, cloudCover, activeMsg) )

        return _activeRadiation, _activeRadiation, _effectiveSouthRadiation, _effectiveWestRadiation
       
    def getOpenWindows( self, cached = False ):
        if cached == False or HeatingHelper.openSFContacts is None:
            now = getNow()
            # should be at least 2 minutes open
            shortReference = now.minusMinutes(2)
            longStartReference = now.minusMinutes(5)
            longEndReference = now.minusMinutes(10)
            
            HeatingHelper.openFFContacts = {}
            if getItemState("Door_FF_Floor") == OPEN:
                door = getItem("Door_FF_Floor")
                if itemLastUpdateOlderThen(door,shortReference):
                    HeatingHelper.openFFContacts[door.getName()] = door
                
            if getItemState("Sensor_Window_FF") == OPEN:
                for sensor in getGroupMember("Sensor_Window_FF"):
                    if sensor.getName() != "Window_FF_Garage" and sensor.getState() == OPEN and itemLastUpdateOlderThen(sensor,shortReference):
                        HeatingHelper.openFFContacts[sensor.getName()] = sensor
    
            # add new contacts
            for sensorName in set(HeatingHelper.openFFContacts) - set(HeatingHelper.longOpenFFContacts):
                sensor = HeatingHelper.openFFContacts.get(sensorName)
                if itemLastUpdateOlderThen(sensor,longStartReference):
                    HeatingHelper.longOpenFFContacts[sensor.getName()] = sensor
                    
            # clean old contacts
            for sensorName in set(HeatingHelper.longOpenFFContacts) - set(HeatingHelper.openFFContacts):
                sensor = HeatingHelper.longOpenFFContacts.get(sensorName)
                if itemLastUpdateOlderThen(sensor,longEndReference):
                    HeatingHelper.longOpenFFContacts.pop(sensor.getName(),None)
                
            HeatingHelper.openSFContacts = {}
            if getItemState("Sensor_Window_SF") == OPEN:
                for sensor in getGroupMember("Sensor_Window_SF"):
                    if sensor.getName() != "Window_SF_Attic" and sensor.getState() == OPEN and itemLastUpdateOlderThen(sensor,shortReference):
                        HeatingHelper.openSFContacts[sensor.getName()] = sensor
                        
            # add new contacts
            for sensorName in set(HeatingHelper.openSFContacts) - set(HeatingHelper.longOpenSFContacts):
                sensor = HeatingHelper.openSFContacts.get(sensorName)
                if itemLastUpdateOlderThen(sensor,longStartReference):
                    HeatingHelper.longOpenSFContacts[sensor.getName()] = sensor
                    
            # clean old contacts
            for sensorName in set(HeatingHelper.longOpenSFContacts) - set(HeatingHelper.openSFContacts):
                sensor = HeatingHelper.longOpenSFContacts.get(sensorName)
                if itemLastUpdateOlderThen(sensor,longEndReference):
                    HeatingHelper.longOpenSFContacts.pop(sensor.getName(),None)

            #self.log.info(u"{} {}".format(HeatingHelper.openFFContacts,HeatingHelper.openSFContacts))
            #self.log.info(u"{} {}".format(HeatingHelper.longOpenFFContacts,HeatingHelper.longOpenSFContacts))
            
        return { "ffCount": len(HeatingHelper.openFFContacts), "totalFfCount": 6, "sfCount": len(HeatingHelper.openSFContacts), "totalSfCount": 5 }
    
    def getLongOpenWindows( self ):
        return { "ffCount": len(HeatingHelper.longOpenFFContacts), "totalFfCount": 6, "sfCount": len(HeatingHelper.longOpenSFContacts), "totalSfCount": 5 }

    def getHeatingPowerPerMinute( self, activeRooms, pumpSpeed, temperature_Pipe_Out, temperature_Pipe_In):
        # To warmup 1 liter of wather you need 4,182 Kilojoule
        # 1 Wh == 3,6 kJ
        # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
        _referencePower = 1162 # per Watt je m³/K
        #_maxVolume = 1.2 # 1200l max Volumenstrom of a Vitodens 200-W Typ B2HA with 13kW
        _maxVolume = 0.584 # 584l Nenn-Umlaufwassermenge of a Vitodens 200-W Typ B2HA with 13kW
        
        circulationDiff = temperature_Pipe_Out - temperature_Pipe_In
        pumpVolume = round( ( _maxVolume * pumpSpeed ) / 100.0, 2 )
        currentHeatingPowerPerMinute = round( ( _referencePower * pumpVolume * circulationDiff ) / 60.0, 1 )
        
        maxHeatingPowerPerMinute = currentHeatingPowerPerMinute
        
        # remove inactive rooms from heating power to exclude their effects from further calculation
        if not activeRooms.get("livingroom"):
            # Livingroom is 23.2049195152831% of the whole heating area
            currentHeatingPowerPerMinute = round( currentHeatingPowerPerMinute * 0.768, 1 )
      
        return currentHeatingPowerPerMinute, pumpVolume, maxHeatingPowerPerMinute
    
    def getCoolingPowerPerMinute( self, logPrefix, activeRooms, outdoorTempReference, outdoorTemperature, livingroomTemperature, bedroomTemperature, atticTemperature, sunPower, sunPowerMax, openWindow ):

        densitiyAir = 1.2041
        cAir = 1.005

        _lowerVolume = 231.8911
        _upperVolume = 216.5555

        # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
        _n50 = 1.0
        _e = 0.07
        _f = 15.0

        # https://www.ubakus.de/u-wert-rechner/
        _floorUValue = 24.799056
        _egUValue = 58.08226065
        _ogUValue = 43.9353196
        _atticUValue = 18.8523478
        
        # https://www.u-wert.net
        floorPower = _floorUValue * ( livingroomTemperature - outdoorTemperature )
        egPower = _egUValue * ( livingroomTemperature - outdoorTemperature )
        ogPower = _ogUValue * ( bedroomTemperature - outdoorTemperature )
        atticPower = _atticUValue * ( bedroomTemperature - atticTemperature )

        # *** Calculate power loss by ventilation ***
        _ventilationLevel = getItemState("Ventilation_Outgoing").intValue()
        _ventilationTempDiff = getItemState("Ventilation_Outdoor_Outgoing_Temperature").doubleValue() - getItemState("Ventilation_Outdoor_Incoming_Temperature").doubleValue()
        # apply outdoor temperature changes to ventilation in / out difference
        if outdoorTempReference != outdoorTemperature:
            ventilationOffset = ( outdoorTempReference - outdoorTemperature ) / 4
            if _ventilationTempDiff + ventilationOffset > 0:
                _ventilationTempDiff = _ventilationTempDiff + ventilationOffset
        # Ventilation Power
        # 15% => 40m³/h		XX => ?
        # 100% => 350m³/h		85 => 310
        _ventilationVolume = ( ( ( _ventilationLevel - 15.0 ) * 310.0 ) / 85.0 ) + 40.0
        _ventilationUValue = _ventilationVolume * densitiyAir * cAir
        _ventilationPowerInKJ = _ventilationUValue * _ventilationTempDiff
        ventilationPowerInW = _ventilationPowerInKJ / 3.6

        # Leaking Power
        _leakingLowerTemperatureDiff = livingroomTemperature - outdoorTemperature
        _leakingLowerVolume = ( _lowerVolume * _n50 * _e ) / ( 1 + ( _f / _e ) * ( ( ( 0.1 * 0.4 ) / _n50 ) * ( ( 0.1 * 0.4 ) / _n50 ) ) )
        _leakingLowerUValue = _leakingLowerVolume * densitiyAir * cAir
        _leakingLowerPowerInKJ = _leakingLowerUValue * _leakingLowerTemperatureDiff

        _leakingUpperTemperatureDiff = bedroomTemperature - outdoorTemperature
        _leakingUpperVolume = ( _upperVolume * _n50 * _e ) / ( 1 + ( _f / _e ) * ( ( ( 0.1 * 0.4 ) / _n50 ) * ( ( 0.1 * 0.4 ) / _n50 ) ) )
        _leakingUpperUValue = _leakingUpperVolume * densitiyAir * cAir
        _leakingUpperPowerInKJ = _leakingUpperUValue * _leakingUpperTemperatureDiff

        leakingPowerInW = ( _leakingLowerPowerInKJ + _leakingUpperPowerInKJ ) / 3.6
        totalPower = ( floorPower + egPower + ogPower + atticPower ) + ventilationPowerInW + leakingPowerInW

        maxTotalPower = totalPower
        # remove inactive room from cooling power to exclude their effects from further calculation
        if not activeRooms.get("livingroom"):
            # Livingroom is 14.7448138257267% or 21.4786205 W/h/K of the whole house UValue
            totalPower = round( totalPower * 0.853, 1 )

        # open window cooling always applies completely and ignoring deactivated rooms, because of the inhouse air circulation related on this windows
        egExchangePower = ( ( (egPower + floorPower) * openWindow["ffCount"] ) / openWindow["totalFfCount"] ) * 2.0
        ogExchangePower = ( ( (ogPower + atticPower) * openWindow["sfCount"] ) / openWindow["totalSfCount"] ) * 2.0

        # sunPower and openWindow are already adjusted to exclude inactive rooms
        coolingPower = round( ( (totalPower + egExchangePower + ogExchangePower) / 60.0 ) - sunPower, 1 )
        maxCoolingPower = round( ( (maxTotalPower + egExchangePower + ogExchangePower) / 60.0 ) - sunPowerMax, 1 )

        # log messages
        baseMsg = round( ( ( floorPower + egPower + ogPower + atticPower ) / 60.0 ) * -10.0 ) / 10.0
        ventilationMsg = round( ( ( ventilationPowerInW / 60.0 ) * -10.0 ) ) / 10.0
        leakingMsg = round( ( leakingPowerInW / 60.0 ) * -10.0 ) / 10.0
        windowMsg = round( ( ( egExchangePower + ogExchangePower ) / 60.0 ) * -10.0 ) / 10.0
        self.log.info(u"{} Wall {} • Air {} • Leak {} • Window {} • Sun {}".format(logPrefix, baseMsg, ventilationMsg, leakingMsg, windowMsg, sunPowerMax) )

        return coolingPower, maxCoolingPower

    def getNeededEnergyForOneDegrees( self, activeRooms, livingroomTemperature, bedroomTemperature ):

        # 15°C => 1.2250
        # 30°C => 1.1644

        # 0°C  => 0
        # 15°C => -0.0606

        # https://www.ubakus.de/u-wert-rechner/
        _minDensity = 1.1644
        maxDensity = 1.2250
        _cAir = 1.005 # KJ / KG
        _jouleKWRatio = 3.6

        _lowerVolume = 231.8911
        _upperVolume = 216.5555

        _lowerFloorPower = 15379.708453125
        _upperFloorPower = 6784.08459444445

        _lowerDensity = ( ( livingroomTemperature - 15.0 ) * ( _minDensity - maxDensity ) / 15.0 ) + maxDensity
        if _lowerDensity < _minDensity: _lowerDensity = _minDensity
        elif _lowerDensity > maxDensity: _lowerDensity = maxDensity

        _upperDensity = ( ( bedroomTemperature - 15.0 ) * ( _minDensity - maxDensity ) / 15.0 ) + maxDensity
        if _upperDensity < _minDensity: _upperDensity = _minDensity
        elif _upperDensity > maxDensity: _upperDensity = maxDensity

        _lowerAirPower = _lowerVolume * _lowerDensity * _cAir / _jouleKWRatio
        _upperAirPower = _upperVolume * _upperDensity * _cAir / _jouleKWRatio

        lowerPower = _lowerFloorPower + _lowerAirPower
        upperPower = _upperFloorPower + _upperAirPower
        
        neededPower = lowerPower + upperPower
        
        maxPower = neededPower
        
        # remove inactive rooms from needed power to exclude their effects from further calculation
        if not activeRooms.get("livingroom"):
            neededPower = neededPower - 6012.96212326389

        return neededPower, maxPower

    def getCurrentHeatingPowerPerMinute( self, activeRooms ):
        pumpSpeed = getItemState("Heating_Circuit_Pump_Speed").intValue()
        if pumpSpeed == 0: 
            return 0.0, pumpSpeed, 0.0
        
        outValue = getItemState("Heating_Temperature_Pipe_Out").doubleValue()
        inValue = getItemState("Heating_Temperature_Pipe_In").doubleValue()

        currentHeatingPowerPerMinute, pumpVolume, maxHeatingPowerPerMinute = self.getHeatingPowerPerMinute(activeRooms,pumpSpeed,outValue,inValue)

        self.log.info(u"        : Diff {}°C • VL {}°C • RL {}°C • {}% ({} m³)".format((outValue - inValue),outValue,inValue,pumpSpeed,pumpVolume))
        
        return currentHeatingPowerPerMinute, pumpSpeed, maxHeatingPowerPerMinute

    def getPossibleHeatingPowerPerMinute( self, activeRooms, now, currentLivingroomTemp, currentBedroomTemp, currentOutdoorTemp, lastHeatingChange ):
        # Estimation is based on 100% heating pump speed and a avg temperature difference 16.1°C between in and out water
        temperature_Pipe_In = ( ( currentLivingroomTemp + currentBedroomTemp ) / 2 ) if activeRooms.get("livingroom") else currentBedroomTemp
        
        if lastHeatingChange.getMillis() < now.minusHours(12).getMillis():
            # 0.3 steilheit
            # niveau 12k
            # 20° => 36°
            # -20^ => 47°   
            
            # 15 (0) => 32 (0)
            # -15 (-30) => 44 (12)
            if currentOutdoorTemp > 15.0: 
                maxVL = 32
            elif currentOutdoorTemp < -15.0:
                maxVL = 44 
            else:
                maxVL = ( ( currentOutdoorTemp - 15.0 ) * -0.4 ) + 32.0
        else:
            maxVL = temperature_Pipe_In + 11.5
          
        #self.log.info(u"{} {}".format( maxVL, temperature_Pipe_In ))

        _possibleHeatingPowerPerMinute, _, _maxHeatingPowerPerMinute = self.getHeatingPowerPerMinute( activeRooms, 100.0, maxVL, temperature_Pipe_In )
        
        return _possibleHeatingPowerPerMinute, 0, _maxHeatingPowerPerMinute

    def getCurrentCoolingPowerPerMinute(self, activeRooms, now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, openWindow ):
        _sunPower, _sunPowerMax, _effectiveSouthRadiation, _effectiveWestRadiation = self.getSunPowerPerMinute( u"Current :", activeRooms, now, "Cloud_Cover_Current", False )
        _coolingPowerPerMinute, _maxPowerPerMinute = self.getCoolingPowerPerMinute( u"        :", activeRooms, currentOutdoorTemp, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _sunPowerMax, openWindow )
        
        return _coolingPowerPerMinute, _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation, _maxPowerPerMinute

    def getCurrentForecastCoolingPowerPerMinute(self, hours, activeRooms, now, currentOutdoorTemp, currentOutdoorForecastTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, openWindow ):
        _sunPower, _sunPowerMax, _, _ = self.getSunPowerPerMinute( u"FC {}h   :".format(hours), activeRooms, now.plusMinutes(hours*60), u"Cloud_Cover_Forecast{}".format(hours), True )
        _coolingPowerPerMinute, _maxPowerPerMinute = self.getCoolingPowerPerMinute( u"        :", activeRooms, currentOutdoorTemp, currentOutdoorForecastTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _sunPowerMax, openWindow )
        if _coolingPowerPerMinute != _maxPowerPerMinute:
            self.log.info(u"        : ⇲ CD -{} W/min. ⇩".format(_maxPowerPerMinute))
        self.log.info(u"        : CD -{} W/min. ({}°C) ⇩".format(_coolingPowerPerMinute,currentOutdoorForecastTemp) )
        return _coolingPowerPerMinute, _maxPowerPerMinute

    def _cleanupChargeLevel( self, totalChargeLevel, _cleanableChargeDiff ):

        _totalChargeLevel = totalChargeLevel - _cleanableChargeDiff

        return round( _totalChargeLevel, 1 ) if _totalChargeLevel > 0.0 else 0.0

    def _useLivingroomReference( self, currentBedroomTemp, bedroomTarget, currentLivingroomTemp, livingroomTarget ):
        #if livingroomTarget >= currentLivingroomTemp:
        #    return True
        livingroomDiff = livingroomTarget - currentLivingroomTemp
        bedroomDiff = bedroomTarget - currentBedroomTemp
        return livingroomDiff >= bedroomDiff
    
    def calculcateCurrentChargeLevel(self, totalChargeLevel, baseHeatingPower, targetLivingroomTemp, currentLivingroomTemp, targetBedroomTemp, currentBedroomTemp, outdoorReduction ):        
        _currentChargeLevel = totalChargeLevel
        
        # targetLivingroomTemp and targetBedroomTemp must be without night reduction,
        # that why we can't use stored target values like Heating_Temperature_Livingroom_Target and Heating_Temperature_Bedroom_Target
        # we need this, because all upcoming calculations should not consider night reduction

        _useLivingroomReference = self._useLivingroomReference( currentBedroomTemp, targetBedroomTemp, currentLivingroomTemp, targetLivingroomTemp )
        _currentSource = "Temperature_FF_Livingroom" if _useLivingroomReference else "Temperature_SF_Bedroom"
        _currentTemp = currentLivingroomTemp if _useLivingroomReference else currentBedroomTemp
        _targetTemp = targetLivingroomTemp if _useLivingroomReference else targetBedroomTemp

        if HeatingHelper.lastReferenceSource == _currentSource:
            if _currentTemp > HeatingHelper.lastReferenceValue:
                _heatedUpTempDiff = _currentTemp - HeatingHelper.lastReferenceValue
                _currentChargeLevel = self._cleanupChargeLevel( _currentChargeLevel, baseHeatingPower * _heatedUpTempDiff )
        
        _targetTemperatureDiff = _targetTemp - _currentTemp - outdoorReduction
        if _targetTemperatureDiff < 0.0: _targetTemperatureDiff = 0.0
        _neededHeatingPower = baseHeatingPower * _targetTemperatureDiff

        ### Energy available after lazy charge calculation 
        _targetChargeLevelDiff = round( _currentChargeLevel - _neededHeatingPower, 1 )
        
        #self.log.info(u"        : => TARGET: {}°C, CURRENT: {}°C, DIFF: {}°C".format(_targetTemp,_currentTemp,_targetTemperatureDiff))
        #self.log.info(u"        : => LEVEL: {} W, ADD: {} W, MISS: {} W".format(_currentChargeLevel, _targetChargeLevelDiff, _missingChargeLevel))

        return _currentChargeLevel, _targetChargeLevelDiff, _useLivingroomReference

    def calculateAdjustedTotalChargeLevel( self, now, baseHeatingPower, currentBedroomTemp, currentLivingroomTemp ):
        _currentChargeLevel = getItemState("Heating_Charged").doubleValue()

        _livingroomTarget = getItemState("Heating_Temperature_Livingroom_Target").doubleValue()
        _bedroomTarget = getItemState("Heating_Temperature_Bedroom_Target").doubleValue()

        _useLivingroomReference = self._useLivingroomReference( currentBedroomTemp, _bedroomTarget, currentLivingroomTemp, _livingroomTarget )
        _currentSource = "Temperature_FF_Livingroom" if _useLivingroomReference else "Temperature_SF_Bedroom"
        _currentTemp = self.getStableValue( now, _currentSource, 20 )
        
        if HeatingHelper.lastReferenceSource == _currentSource:
            if _currentTemp != HeatingHelper.lastReferenceValue:
                if _currentTemp < HeatingHelper.lastReferenceValue:
                    self.log.info(u"Cleanup : Reference to {} adjusted".format(_currentTemp) )
                elif _currentTemp > HeatingHelper.lastReferenceValue:
                    _heatedUpTempDiff = _currentTemp - HeatingHelper.lastReferenceValue
                    _currentChargeLevel = self._cleanupChargeLevel( _currentChargeLevel, baseHeatingPower * _heatedUpTempDiff )
                    self.log.info(u"Cleanup : Reference to {} and Charged to {} adjusted".format(_currentTemp,_currentChargeLevel) )
        else:
            HeatingHelper.lastReferenceSource = _currentSource
        
        HeatingHelper.lastReferenceValue = _currentTemp

        return _currentChargeLevel
    
    def logPowerAdjustments( self, currentCoolingPowerPerMinute, maxCoolingPowerPerMinute, currentHeatingPowerPerMinute, maxHeatingPowerPerMinute, baseHeatingPower, maxHeatingPower ):
        msg = None
        if currentCoolingPowerPerMinute != maxCoolingPowerPerMinute:
            msg = u"CD -{} W/min. ⇩".format(maxCoolingPowerPerMinute)

        if currentHeatingPowerPerMinute != maxHeatingPowerPerMinute:
            if msg != None: msg = u"{} • ".format(msg)
            msg = u"{}HU {} W/min. ⇧".format(msg,maxHeatingPowerPerMinute)
            
        if baseHeatingPower != maxHeatingPower:
            if msg != None: msg = u"{} • ".format(msg)
            msg = u"{}Slot {} KW/K".format(msg,round( maxHeatingPower / 1000.0, 1 ))
            
        if msg != None:
            self.log.info(u"        : ⇲ {}".format(msg))
 
'''@rule("heating_control.py")
class MoveCircuitSwitchRule(HeatingHelper):
    def __init__(self):
        self.triggers = [CronTrigger("0 0 0 * * ?")]

    def callback(self):
        self.log.info(u"Toogle  : Livingroom circuit OFF")
        sendCommand("Heating_Livingroom_Circuit",OFF)
    
    def execute(self, module, input):
        # switch after 2 days of inactivity livingroom circuit once to avoid ventile damages
        if itemLastUpdateOlderThen("Heating_Livingroom_Circuit", getNow().minusMinutes(60*24*2)):
            if getItemState("Heating_Livingroom_Circuit") == OFF:
                self.log.info(u"Toogle  : Livingroom circuit ON")
                sendCommand("Heating_Livingroom_Circuit",ON)
                createTimer(120, self.callback)'''
        
@rule("heating_control.py")
class CalculateChargeLevelRule(HeatingHelper):
    def __init__(self):
        self.triggers = [CronTrigger("15 * * * * ?")]

    def execute(self, module, input):
        now = getNow()
        
        self.log.info(u">>>")

        currentLivingroomTemp = self.getStableValue( now, "Temperature_FF_Livingroom", 10 )
        currentBedroomTemp = self.getStableValue( now, "Temperature_SF_Bedroom", 10 )
        currentAtticTemp = self.getStableValue( now, "Temperature_SF_Attic", 10 )
        #currentOutdoorTemp = self.getStableValue( now, "Temperature_Garden", 10 )
        currentOutdoorTemp = self.getStableValue( now, "Heating_Temperature_Outdoor", 10 )

        currentLivingRoomCircuit = getItemState("Heating_Livingroom_Circuit")
        isLivingRoomCircuitActive = currentLivingRoomCircuit == ON
        activeRooms = { "livingroom": isLivingRoomCircuitActive }

        # Get current open windows
        openWindow = self.getOpenWindows()

        # Calculate current cooling power per minute, based on temperature differences, sun power and open windows
        currentCoolingPowerPerMinute, sunPower, effectiveSouthRadiation, effectiveWestRadiation, maxCoolingPowerPerMinute = self.getCurrentCoolingPowerPerMinute( activeRooms, now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, openWindow )
        
        # Get Needed energy to warmup the house by one degrees
        baseHeatingPower, maxHeatingPower = self.getNeededEnergyForOneDegrees( activeRooms, currentLivingroomTemp, currentBedroomTemp )

        # Calculate the "real" heating power based on the pump speed.
        currentHeatingPowerPerMinute, currentPumpSpeedInPercent, maxHeatingPowerPerMinute = self.getCurrentHeatingPowerPerMinute( activeRooms )
        
        self.logPowerAdjustments( currentCoolingPowerPerMinute, maxCoolingPowerPerMinute, currentHeatingPowerPerMinute, maxHeatingPowerPerMinute, baseHeatingPower, maxHeatingPower )
            
        # some logs
        self.log.info(u"        : CD {} W/min. ({}°C) ⇩ • HU {} W/min. ({}%) ⇧".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp,currentHeatingPowerPerMinute,currentPumpSpeedInPercent) )

        slotHeatingPower = round( baseHeatingPower * 0.1, 1 )
        
        self.log.info(u"Slot    : {} KW/K • {} W/0.1K".format(round( baseHeatingPower / 1000.0, 1 ),slotHeatingPower ) )

        self.setSunStates( currentOutdoorTemp, currentAtticTemp, currentBedroomTemp, currentLivingroomTemp, sunPower, effectiveSouthRadiation, effectiveWestRadiation )

        # Get the house charge level. If we detect a house warmup, we remove "adjust" the needed amount energy for heating up in 0.1°C levels
        totalChargeLevel = self.calculateAdjustedTotalChargeLevel( now, baseHeatingPower, currentBedroomTemp, currentLivingroomTemp )
    
        # Apply difference between heating power and cooling power to the chage level
        totalChargeLevel = totalChargeLevel - currentCoolingPowerPerMinute + currentHeatingPowerPerMinute
        totalChargeLevel = round( totalChargeLevel, 1 )
        if totalChargeLevel < 0.0: totalChargeLevel = 0.0
        postUpdateIfChanged( "Heating_Charged", totalChargeLevel )

        self.log.info(u"Charged : {} W total incl. buffer".format(totalChargeLevel) )

        self.log.info(u"<<<")

    def setSunStates(self, currentOutdoorTemp, currentAtticTemp, currentBedroomTemp, currentLivingroomTemp, sunPower, effectiveSouthRadiation, effectiveWestRadiation ):
      
        postUpdateIfChanged( "Solar_Power", sunPower )

        if effectiveSouthRadiation > 0.0 or effectiveWestRadiation > 0.0:
          
            heatingLivingroomTarget = round( getItemState("Heating_Temperature_Livingroom_Target").doubleValue(), 1 )
            heatingBedroomTarget = round( getItemState("Heating_Temperature_Bedroom_Target").doubleValue(), 1 )

            atticRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Attic") == ON:
                if effectiveSouthRadiation < 3.7 or currentAtticTemp < atticRef or currentOutdoorTemp < atticRef:
                    postUpdate("State_Sunprotection_Attic", OFF )
            elif effectiveSouthRadiation > 3.8 and currentAtticTemp >= atticRef and currentOutdoorTemp >= atticRef:
                postUpdate("State_Sunprotection_Attic", ON )

            bathroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Bathroom") == ON:
                if effectiveSouthRadiation < 3.7 or currentBedroomTemp < bathroomRef or currentOutdoorTemp < bathroomRef:
                    postUpdate("State_Sunprotection_Bathroom", OFF )
            elif effectiveSouthRadiation > 3.8 and currentBedroomTemp >= bathroomRef and currentOutdoorTemp >= bathroomRef:
                postUpdate("State_Sunprotection_Bathroom", ON )

            dressingroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Dressingroom") == ON:
                if effectiveSouthRadiation < 3.7 or currentBedroomTemp < dressingroomRef or currentOutdoorTemp < dressingroomRef:
                    postUpdate("State_Sunprotection_Dressingroom", OFF )
            elif effectiveSouthRadiation > 3.8 and currentBedroomTemp >= dressingroomRef and currentOutdoorTemp >= dressingroomRef:
                postUpdate("State_Sunprotection_Dressingroom", ON )

            bedroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Bedroom") == ON:
                if effectiveWestRadiation < 3.7 or currentBedroomTemp < bedroomRef or currentOutdoorTemp < bedroomRef:
                    postUpdate("State_Sunprotection_Bedroom", OFF )
            elif effectiveWestRadiation > 3.8 and currentBedroomTemp >= bedroomRef and currentOutdoorTemp >= bedroomRef:
                postUpdate("State_Sunprotection_Bedroom", ON )

            livingroomRef = heatingLivingroomTarget - 1.0
            if getItemState("State_Sunprotection_Livingroom") == ON:
                if effectiveWestRadiation < 3.7 or currentLivingroomTemp < livingroomRef or currentOutdoorTemp < livingroomRef:
                    postUpdate("State_Sunprotection_Livingroom", OFF )
            elif effectiveWestRadiation > 3.8 and currentLivingroomTemp >= livingroomRef and currentOutdoorTemp >= livingroomRef:
                postUpdate("State_Sunprotection_Livingroom", ON )

@rule("heating_control.py")
class HeatingCheckRule(HeatingHelper):
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Auto_Mode"),
            CronTrigger("30 */2 * * * ?")
        ]
        self.nightModeActive = False
        self.forcedBufferReferenceTemperature = None
        self.forcedBufferReferenceDate = -1
        self.activeHeatingOperatingMode = -1

    def execute(self, module, input):
        now = getNow()

        self.log.info(u">>>")
        
        minBufferChargeLevel = 0
        
        currentLivingroomTemp = self.getStableValue( now, "Temperature_FF_Livingroom", 10, True )
        currentBedroomTemp = self.getStableValue( now, "Temperature_SF_Bedroom", 10, True )
        currentAtticTemp = self.getStableValue( now, "Temperature_SF_Attic", 10, True )
        #currentOutdoorTemp = self.getStableValue( now, "Temperature_Garden", 10, True )
        currentOutdoorTemp = self.getStableValue( now, "Heating_Temperature_Outdoor", 10 )

        # not changed since 6 hours.
        if self.isOutdatetForecast():
            self.log.info(u"Forecast: ERROR • Fall back to current temperature.")
            currentOutdoorForecast4Temp = currentOutdoorTemp
            currentOutdoorForecast8Temp = currentOutdoorTemp
        else:
            currentOutdoorForecast4Temp = round( getItemState("Temperature_Garden_Forecast4").doubleValue(), 1 )
            currentOutdoorForecast8Temp = round( getItemState("Temperature_Garden_Forecast8").doubleValue(), 1 )
            
        heatingTarget = round( getItemState("Temperature_Room_Target").doubleValue(), 1 )
        heatingTargetLivingroomTemp = round( heatingTarget, 1 )
        heatingTargetBedroomTemp = round( heatingTarget - BEDROOM_REDUCTION, 1 )

        totalChargeLevel = round( getItemState("Heating_Charged").doubleValue(), 1 )
        
        lastHeatingChange = getItemLastUpdate("Heating_Demand")

        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        isHeatingActive = currentOperatingMode == 2

        currentLivingRoomCircuit = getItemState("Heating_Livingroom_Circuit")
        isLivingRoomCircuitActive = currentLivingRoomCircuit == ON
        activeRooms = { "livingroom": isLivingRoomCircuitActive }

        # Get current open windows and the ones during the last 15 min
        openWindow = self.getOpenWindows( True )
        longOpenWindow = self.getLongOpenWindows()
        
        # Calculate cooling power in 8h
        currentForecast8CoolingPowerPerMinute, maxForecast8CoolingPowerPerMinute = self.getCurrentForecastCoolingPowerPerMinute( 8, activeRooms, now, currentOutdoorTemp, currentOutdoorForecast8Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, longOpenWindow)

        # Calculate cooling power in 4h
        currentForecast4CoolingPowerPerMinute, maxForecast4CoolingPowerPerMinute = self.getCurrentForecastCoolingPowerPerMinute( 4, activeRooms, now, currentOutdoorTemp, currentOutdoorForecast4Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, longOpenWindow)

        # Calculate current cooling power per minute, based on temperature differences, sun power and open windows
        currentCoolingPowerPerMinute, _, _, _, maxCoolingPowerPerMinute = self.getCurrentCoolingPowerPerMinute( activeRooms, now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, openWindow )

        # Get Needed energy to warmup the house by one degrees
        baseHeatingPower, maxHeatingPower = self.getNeededEnergyForOneDegrees( activeRooms, currentLivingroomTemp, currentBedroomTemp )

        # Calculate the "real" heating power based on the pump speed.
        currentHeatingPowerPerMinute, currentPumpSpeedInPercent, maxHeatingPowerPerMinute = self.getCurrentHeatingPowerPerMinute( activeRooms )
        if currentHeatingPowerPerMinute == 0:
            currentHeatingPowerPerMinute, currentPumpSpeedInPercent, maxHeatingPowerPerMinute = self.getPossibleHeatingPowerPerMinute( activeRooms, now, currentLivingroomTemp, currentBedroomTemp, currentOutdoorTemp, lastHeatingChange )
            _currentPumpSpeedMsg = u"FC"
        else:
            _currentPumpSpeedMsg = u"{}%".format(currentPumpSpeedInPercent)
        
        self.logPowerAdjustments( currentCoolingPowerPerMinute, maxCoolingPowerPerMinute, currentHeatingPowerPerMinute, maxHeatingPowerPerMinute, baseHeatingPower, maxHeatingPower )

        # some logs
        self.log.info(u"        : CD {} W/min. ({}°C) ⇩ • HU {} W/min. ({}) ⇧".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp,currentHeatingPowerPerMinute,_currentPumpSpeedMsg) )

        # Calculate reduction based on the current sun heating or the expected (forecast based) sun heating
        outdoorReduction = self.calculateOutdoorReduction( currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, currentForecast8CoolingPowerPerMinute)

        slotHeatingPower = round( baseHeatingPower * 0.1, 1 )
        maxSlotHeatingPower = round( maxHeatingPower * 0.1, 1 )

        # Calculate "available" heating power. Thats means current or possible heating power - current cooling power
        # This is the leftover to warmup the house
        availableHeatingPowerPerMinute = round( currentHeatingPowerPerMinute - currentCoolingPowerPerMinute, 1 )

        # Calculate the charge level adjusted by possible heated up 0.1°C levels
        # currentChargeLevel - the current house charge level
        # targetChargeLevelDiff - target releated charge difference
        #   - positive value means we have more energy than needed to reach our target temperature
        #   - negavive value means we still need more energy to reach our target temperature
        currentChargeLevel, targetChargeLevelDiff, useLivingroomReference = self.calculcateCurrentChargeLevel(totalChargeLevel, baseHeatingPower, heatingTargetLivingroomTemp, currentLivingroomTemp, heatingTargetBedroomTemp, currentBedroomTemp, outdoorReduction)
    
        # Zone Level (BUFFER LEVEL) to stop buffer heating. Is based on cooling power.
        maxBufferChargeLevel = self.calculateMaxBufferChargeLevel( currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, slotHeatingPower )

        if targetChargeLevelDiff >= 0:
            heatingUpMinutes = 0
            coolingDownMinutes = int( round( targetChargeLevelDiff / currentCoolingPowerPerMinute ) ) if currentCoolingPowerPerMinute > 0 else 0
        else:
            heatingUpMinutes = int( round( targetChargeLevelDiff * -1 / availableHeatingPowerPerMinute ) ) if availableHeatingPowerPerMinute > 0 else 0
            coolingDownMinutes = 0

        # Some log messages about charge values
        _timeToHeatSlot = int( round( slotHeatingPower / availableHeatingPowerPerMinute ) ) if availableHeatingPowerPerMinute > 0 else 0
        _baseHeatingPowerInKW = round( baseHeatingPower / 1000.0, 1 )
        self.log.info(u"Slot    : {} KW/K • {} W/0.1K • {} min. ⇧".format(_baseHeatingPowerInKW,slotHeatingPower,_timeToHeatSlot ) )

        _timeToHeatBuffer = int( round( maxBufferChargeLevel / availableHeatingPowerPerMinute ) ) if availableHeatingPowerPerMinute > 0 else 0
        _bufferFilledInPercent = int( round( targetChargeLevelDiff * 100 / maxBufferChargeLevel, 0 ) ) if targetChargeLevelDiff > 0 and maxBufferChargeLevel > 0 else 0
        self.log.info(u"Buffer  : {}% filled • {} W ... {} W • {} min. ⇧".format( _bufferFilledInPercent, minBufferChargeLevel, maxBufferChargeLevel, _timeToHeatBuffer) )

        _totalLazyChargeMsg = u" ({} W)".format(totalChargeLevel) if currentChargeLevel != totalChargeLevel else u""
        if heatingUpMinutes > 0:
            chargeMsg = u"{} min. ⇧".format(heatingUpMinutes)
        else:
            chargeMsg = u"{} min. ⇩".format(coolingDownMinutes)
        self.log.info(u"Charged : {} W{} total incl. buffer • {}".format( currentChargeLevel, _totalLazyChargeMsg, chargeMsg) )
        
        # Calculate reduction based on available energy (=> Calculation of currentChargeLevel) to lazy warmup the house later
        # EXPECTED WARMUP TO REACH TARGET.
        # Here we calculate lazy reduction to reach 'referenceTargetDiff == 0' earlier        
        # Then we are able to check with 'isBufferHeating' if targetChargeLevelDiff is enough to stop heating 
        # + 0.005 to avoid issues based on rounded values like for 0.09999910401 or 0.198695885991 (4433.7 , 2231.4 base )
        # can happen because currentChargeLevel and targetChargeLevelDiff are already rounded values and baseHeatingPower not
        _lazyChargedLevel = currentChargeLevel - ( targetChargeLevelDiff if targetChargeLevelDiff > 0 else 0 )
        #self.log.info(u"{} {} {}".format(_lazyChargedLevel,(_lazyChargedLevel / slotHeatingPower * 0.1),(_lazyChargedLevel / baseHeatingPower)))
        lazyReduction = math.floor( ( ( _lazyChargedLevel / baseHeatingPower ) + 0.005 ) * 10.0 ) / 10.0
        #lazyReduction = 0.0 if isBufferHeatingNeeded else math.floor( _possibleLazyReduction * 10.0 ) / 10.0
        
        # Calculate night reduction
        # Night reduction start is earlier on higher coolingDownMinutes
        # and night reduction stops earlier on higher heatingUpMinutes
        nightReduction = self.calculateNightReduction( now, isHeatingActive, coolingDownMinutes, heatingUpMinutes)

        # Calculate wanted target temperatures in livingroom and bedroom based on night reduction and bedroom/livingroom offset
        _heatingTargetLivingroomTemp = heatingTargetLivingroomTemp
        
        heatingTargetLivingroomTemp -= nightReduction
        heatingTargetBedroomTemp -= nightReduction
        postUpdateIfChanged("Heating_Temperature_Livingroom_Target", heatingTargetLivingroomTemp )
        postUpdateIfChanged("Heating_Temperature_Bedroom_Target", heatingTargetBedroomTemp )

        # Some logs
        self.log.info(u"Effects : LR {}° ⇩ • OR {}°C ⇩ • NR {}°C ⇩ • LRC {}".format(lazyReduction,outdoorReduction,nightReduction,currentLivingRoomCircuit ))
        self.log.info(u"Rooms   : Living {}°C (⇒ {}°C) • Sleeping {}°C (⇒ {}°C)".format(currentLivingroomTemp,heatingTargetLivingroomTemp,currentBedroomTemp,heatingTargetBedroomTemp))
               
        # prepare for wakeup. is needed to calculate correct night end time and force buffer time in the morning
        # use possible night mode reduced temp if night mode is not ending during the next 4 hours 
        # otherwise use normal temp
        referenceTarget = heatingTargetLivingroomTemp if self.isNightModeTime(now.plusMinutes(240)) else _heatingTargetLivingroomTemp
        newLivingRoomCircuit = currentLivingRoomCircuit
        # Switch livingroom circuit off if it is too warm
        if isLivingRoomCircuitActive:
            if currentLivingroomTemp >= referenceTarget + 0.2:
                newLivingRoomCircuit = OFF
                #newLivingRoomCircuit = ON
        elif currentLivingroomTemp <= referenceTarget:
            newLivingRoomCircuit = ON
            
        ### Analyse result
        if getItemState("Heating_Auto_Mode").intValue() == 1:
            heatingDemand = 0
            heatingType = ""
            
            ### Check heating demand
            if longOpenWindow["ffCount"] + longOpenWindow["sfCount"] < 2:

                # Calculate missing degrees to reach target temperature
                heatingTargetDiff = self.getHeatingTargetDiff( currentLivingroomTemp, heatingTargetLivingroomTemp, currentBedroomTemp, heatingTargetBedroomTemp, useLivingroomReference )
                
                referenceTargetDiff = round( heatingTargetDiff - lazyReduction - outdoorReduction, 1 )
                
                if referenceTargetDiff > 0:
                    heatingDemand = 1
                    heatingType = u"HEATING NEEDED"
                else:
                    # it is too warm inside, but outside it is very cold, so we need some buffer heating to avoid cold floors
                    # should always be calculated with all rooms ON and maxSlotHeatingPower
                    forceBufferHeating = self.forcedBufferHeatingCheck( now, isHeatingActive, lastHeatingChange, maxSlotHeatingPower, availableHeatingPowerPerMinute, targetChargeLevelDiff, currentLivingroomTemp, currentCoolingPowerPerMinute )
                
                    if forceBufferHeating:
                        heatingDemand = 1
                        heatingType = u"FORCED BUFFER HEATING NEEDED"
                        # should always be calculated with all rooms ON
                        newLivingRoomCircuit = ON
                    elif referenceTargetDiff == 0.0:
                        # Check if buffer heating is needed
                        isBufferHeatingNeeded = self.isBufferHeating( isHeatingActive, targetChargeLevelDiff, minBufferChargeLevel, maxBufferChargeLevel )
        
                        if isBufferHeatingNeeded:
                            heatingDemand = 1
                            heatingType = u"BUFFER HEATING NEEDED"
                        else:
                            heatingType = u"NO HEATING NEEDED • BUFFER FULL"
                    else:
                        heatingType = u"NO HEATING NEEDED • TOO WARM"
                
                if lazyReduction > 0 or outdoorReduction > 0:
                    heatingType = u"{} • REDUCED {}°".format(heatingType,( lazyReduction + outdoorReduction ))
            else:
                heatingType = u"NO HEATING NEEDED • TOO MANY OPEN WINDOWS"

            self.log.info(u"Demand  : {}".format(heatingType) )

            postUpdateIfChanged("Heating_Demand", heatingDemand )

            if currentLivingRoomCircuit != newLivingRoomCircuit:
                self.log.info(u"Switch  : Livingroom circuit {}".format(newLivingRoomCircuit))
                sendCommand("Heating_Livingroom_Circuit",newLivingRoomCircuit)
        
            ### Call heating control
            self.controlHeating(now, currentOperatingMode, heatingDemand, lastHeatingChange, currentOutdoorTemp)
        else:
            self.log.info(u"Demand  : SKIPPED • MANUAL MODE ACTIVE")
            postUpdateIfChanged("Heating_Demand", 0 )

        self.log.info(u"<<<")

    def getHeatingTargetDiff( self, currentLivingroomTemp, targetLivingroomTemp, currentBedroomTemp, targetBedroomTemp, useLivingroomReference ):
        livingroomDifference = targetLivingroomTemp - currentLivingroomTemp
        bedroomDifference = targetBedroomTemp - currentBedroomTemp
        difference = livingroomDifference if useLivingroomReference else bedroomDifference
        return round( difference, 1 )

    def getOutdoorDependingReduction( self, coolingPowerPerMinute ):
        # more than zeor means cooling => no reduction
        if coolingPowerPerMinute >= 0: return 0.0

        # less than zero means - sun heating
        # -300 => max reduction
        if coolingPowerPerMinute <= -300: return 2.0

        return ( coolingPowerPerMinute * 2.0 ) / -300.0

    def calculateOutdoorReduction(self, currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, currentForecast8CoolingPowerPerMinute):
        # Current cooling should count full
        _currentOutdoorReduction = self.getOutdoorDependingReduction(currentCoolingPowerPerMinute)
        # Closed cooling forecast should count 90%
        _forecast4outdoorReduction = self.getOutdoorDependingReduction(currentForecast4CoolingPowerPerMinute) * 0.8
        # Cooling forecast in 8 hours should count 80%
        _forecast8outdoorReduction = self.getOutdoorDependingReduction(currentForecast8CoolingPowerPerMinute) * 0.6
        
        _outdoorReduction = _currentOutdoorReduction + _forecast4outdoorReduction + _forecast8outdoorReduction
        
        if _outdoorReduction > 0.0: _outdoorReduction = _outdoorReduction + 0.1
        
        return round( _outdoorReduction, 1 )
              
    def isNightModeTime(self,reference):
        day    = reference.getDayOfWeek()
        hour   = reference.getHourOfDay()
        minute = reference.getMinuteOfHour()

        _nightModeActive = False
        
        _isMorning = True if hour < 12 else False
        
        # Wakeup
        if _isMorning:
            # Monday - Friday
            if day <= 5:
                if hour < 5 or ( hour == 5 and minute <= 30 ):
                    _nightModeActive = True
            # Saturday and Sunday
            else:
                if hour < 8 or ( hour == 8 and minute <= 30 ):
                    _nightModeActive = True
        # Evening
        else:
            # Monday - Thursday and Sunday
            if day <= 4 or day == 7:
                if hour >= 23 or ( hour == 22 and minute >= 30 ):
                    _nightModeActive = True
            # Friday and Saturday
            else:
                if hour >= 24:
                    _nightModeActive = True

        return _nightModeActive

    def isNightMode( self, now, isHeatingActive, coolingDownMinutes, heatingUpMinutes, nightModeActive ):
        hourOfTheDay = now.getHourOfDay()
        reference = now
        
        # check night mode end only in the morning, 6 hours before wakeup
        if hourOfTheDay < 12 and not self.isNightModeTime(now.plusMinutes(360)):
            if nightModeActive:
                endOffset = heatingUpMinutes if heatingUpMinutes > 0 else 0
                lazyTime = 0

                # check early enough to have enough time for lazy warming up
                # add time offset for lazy warming up after heating
                if not isHeatingActive and endOffset > 0:
                    endOffset = endOffset + LAZY_OFFSET

                reference = reference.plusMinutes( endOffset )
                _isNightMode = self.isNightModeTime(reference)
                msg = u"end check at {} • {} min. • {} min. lazy".format(OFFSET_FORMATTER.print(reference),endOffset,lazyTime)
            else:
                _isNightMode = nightModeActive
                msg = u"ended"
        else:
            if not nightModeActive:
                startOffset = coolingDownMinutes if coolingDownMinutes > 0 else 0
                
                #minStartOffset = int( round( MIN_HEATING_TIME / 3.0 ) ) + LAZY_OFFSET
                
                # if heating not active, check if the night mode is far enough for a new heating cycle
                if not isHeatingActive and startOffset < LAZY_OFFSET:
                    startOffset = LAZY_OFFSET

                reference = reference.plusMinutes( startOffset )
                _isNightMode = self.isNightModeTime(reference)
                msg = u"start check at {} • {} min.".format(OFFSET_FORMATTER.print(reference),startOffset)
            else:
                _isNightMode = nightModeActive
                msg = u"started"
            
        self.log.info(u"        : Night mode {}".format(msg))

        return _isNightMode

    def calculateNightReduction(self, now, isHeatingActive, coolingDownMinutes, heatingUpMinutes):
        self.nightModeActive = self.isNightMode(  now, isHeatingActive, coolingDownMinutes, heatingUpMinutes, self.nightModeActive )
        return NIGHT_REDUCTION if self.nightModeActive else 0.0
      
    def calculateMaxBufferChargeLevel(self, currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute,slotHeatingPower):
        if currentCoolingPowerPerMinute > 0.0 and currentForecast4CoolingPowerPerMinute > 0.0:
            # calculate max charge level for 45 min
            #neededLazyChargeLevel = round( LAZY_OFFSET * ( currentCoolingPowerPerMinute + currentForecast4CoolingPowerPerMinute ) / 2.0, 1 )
            neededLazyChargeLevel = round( slotHeatingPower * 0.75, 1 )
            #stopZoneLevel = int( round( neededLazyChargeLevel * 100.0 / slotHeatingPower ) )
            
            return neededLazyChargeLevel
        return 0

    def isBufferHeating( self, isHeatingActive, currentBufferChargeLevel, minBufferChargeLevel, maxBufferChargeLevel ):
        # Currently no buffer heating
        if not isHeatingActive:
            # No heating needed if buffer is changed more than minBufferChargeLevel
            if currentBufferChargeLevel > minBufferChargeLevel:
                return False
        # Stop buffer heating if buffer more than 70% charged
        elif currentBufferChargeLevel > maxBufferChargeLevel:
            return False

        return maxBufferChargeLevel > 0

    def calculateForcedBufferHeatingTime(self, now, lastUpdate, slotHeatingPower, currentCoolingPowerPerMinute ):
      
        # when was the last heating job
        lastUpdateBeforeInMinutes = int( round( ( now.getMillis() - lastUpdate.getMillis() ) / 1000.0 / 60.0 ) )

        # 20W/min => 0
        # 60W/min => 4
        
        maxFactor = currentCoolingPowerPerMinute * 4.0 / 60.0
        if maxFactor < 0.0:
          maxFactor = 0.0

        # 0 hours => 0
        # 24 hours => factor
        factor = ( lastUpdateBeforeInMinutes / 60.0 ) * maxFactor / 24.0

        if factor > maxFactor: factor = maxFactor

        targetBufferChargeLevel = round( slotHeatingPower * factor, 1 )

        return round( targetBufferChargeLevel, 1 ), lastUpdateBeforeInMinutes

    def forcedBufferHeatingCheck( self, now, isHeatingActive, lastHeatingChange, slotHeatingPower, availableHeatingPowerPerMinute, currentBufferChargeLevel, currentLivingroomTemp, currentCoolingPowerPerMinute ):

        if isHeatingActive:
            if self.forcedBufferReferenceTemperature != None:
                # Room is warming up, so we have to stop previously forced checks
                if self.forcedBufferReferenceTemperature < currentLivingroomTemp:
                    self.log.info(u"        : Stop forced buffer • room is warming up" )
                    self.forcedBufferReferenceTemperature = None
                else:
                    if self.forcedBufferReferenceDate != -1:
                        targetBufferChargeLevel, lastUpdateBeforeInMinutes = self.calculateForcedBufferHeatingTime( now, self.forcedBufferReferenceDate, slotHeatingPower, currentCoolingPowerPerMinute )
                    else:
                        targetBufferChargeLevel = slotHeatingPower
                    
                    # Too much forced heating > 90 minutes
                    if currentBufferChargeLevel > targetBufferChargeLevel:
                        self.log.info(u"        : Stop forced buffer • buffer limit reached" )
                        self.forcedBufferReferenceTemperature = None
                    else:
                        self.log.info(u"        : Continue forced heating • until {} W".format( targetBufferChargeLevel ) )
            else:
                # Keep everything like it is. This leaves the forcedBufferCheckActive untouched
                self.log.info(u"        : No forced buffer • is heating" )
        else:
            targetBufferChargeLevel, lastUpdateBeforeInMinutes = self.calculateForcedBufferHeatingTime( now, lastHeatingChange, slotHeatingPower, currentCoolingPowerPerMinute )

            heatingMinutes = int( round( ( targetBufferChargeLevel / availableHeatingPowerPerMinute ) ) )
        
            if heatingMinutes > MIN_HEATING_TIME:              
                # Is not the right time. Only in the morning
                if not self.isNightModeTime(now):
                    self.log.info(u"        : No forced buffer • {} W in {} min. • day".format(targetBufferChargeLevel,heatingMinutes))
                    self.forcedBufferReferenceTemperature = None
                # Is still in the night
                elif self.isNightModeTime(now.plusMinutes( heatingMinutes + LAZY_OFFSET )):
                    self.log.info(u"        : No forced buffer • {} W in {} min. • night".format(targetBufferChargeLevel,heatingMinutes) )
                    self.forcedBufferReferenceTemperature = None
                # heating was active in the past 20 hours
                else:
                    self.log.info(u"        : Force buffer • {} W in {} min. • prevent cold floors".format(targetBufferChargeLevel,heatingMinutes))
                    self.forcedBufferReferenceTemperature = currentLivingroomTemp
                    self.forcedBufferReferenceDate = lastHeatingChange
            else:
                # Last heating older then 24 hours, but still no heating needed. Maybe maxBuffer low.
                if lastUpdateBeforeInMinutes > 1440:
                    self.log.info(u"        : No forced buffer • not needed" )
                    self.forcedBufferReferenceTemperature = None
                else:
                    self.log.info(u"        : No forced buffer • {} W in {} min.".format(targetBufferChargeLevel,heatingMinutes) )
                    self.forcedBufferReferenceTemperature = None

        return self.forcedBufferReferenceTemperature != None

    def controlHeating( self, now, currentOperatingMode, heatingDemand, lastHeatingChange, currentOutdoorTemp ):

        # 0 - Abschalten
        # 1 - Nur WW
        # 2 - Heizen mit WW
        # 3 - Reduziert
        # 4 - Normal
        
        isHeatingRequested = heatingDemand == 1
        if self.activeHeatingOperatingMode == -1:
            self.activeHeatingOperatingMode = currentOperatingMode
        
        forceRetry = self.activeHeatingOperatingMode != currentOperatingMode
        forceRetryMsg = u" • RETRY" if forceRetry else u""
        
        
        lastUpdateBeforeInMinutes = int( round( ( now.getMillis() - lastHeatingChange.getMillis() ) / 1000.0 / 60.0 ) )
        lastHeatingChangeFormatted = OFFSET_FORMATTER.print(lastHeatingChange)
        lastUpdateBeforeFormatted = lastUpdateBeforeInMinutes if lastUpdateBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastUpdateBeforeInMinutes, 60));
        
        self.log.info(u"Active  : {} • since {} • {} min. ago".format(Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) ),lastHeatingChangeFormatted,lastUpdateBeforeFormatted) )
        
        # Nur WW
        if currentOperatingMode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if isHeatingRequested:
                isRunningLongEnough = itemLastUpdateOlderThen("Heating_Operating_Mode", now.minusMinutes(MIN_ONLY_WW_TIME))
                
                if forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode", self.activeHeatingOperatingMode)
                elif not isRunningLongEnough:
                    runtimeInMinutes = int( round( ( now.getMillis() - getItemLastUpdate("Heating_Operating_Mode").getMillis() ) / 1000.0 / 60.0 ) )
                    forceRetryMsg = u" • SKIPPED • offtime is {} min.".format(runtimeInMinutes)

                self.log.info(u"Switch  : Nur WW => Heizen mit WW{}".format(forceRetryMsg))

        # Heizen mit WW
        elif currentOperatingMode == 2:
            currentPowerState = getItemState("Heating_Power").intValue()
            
            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not isHeatingRequested:
                isRunningLongEnough = itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(MIN_HEATING_TIME))
                
                if currentPowerState == 0 or forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 1
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                elif not isRunningLongEnough:
                    runtimeInMinutes = int( round( ( now.getMillis() - getItemLastUpdate("Heating_Operating_Mode").getMillis() ) / 1000.0 / 60.0 ) )
                    forceRetryMsg = u" • SKIPPED • runtime is {} min.".format(runtimeInMinutes)

                self.log.info(u"Switch  : Heizen mit WW => Nur WW{}".format(forceRetryMsg))
                  
            # Brenner läuft nicht
            elif currentPowerState == 0:
                # max 5 min.
                minTimestamp = getHistoricItemEntry("Heating_Operating_Mode",now).getTimestamp().getTime()
                _minTimestamp = now.minusMinutes(5).getMillis()
                if minTimestamp < _minTimestamp:
                    minTimestamp = _minTimestamp

                currentTime = now
                lastItemEntry = None
                burnerStarts = 0

                # check for new burner starts during this time periode
                while currentTime.getMillis() > minTimestamp:
                    currentItemEntry = getHistoricItemEntry("Heating_Power", currentTime)
                    if lastItemEntry is not None:
                        currentHeating = ( currentItemEntry.getState().doubleValue() != 0.0 )
                        lastHeating = ( lastItemEntry.getState().doubleValue() != 0.0 )
                        
                        if currentHeating != lastHeating:
                            burnerStarts = burnerStarts + 1
                    
                    currentTime = DateTime( currentItemEntry.getTimestamp().getTime() - 1 )
                    lastItemEntry = currentItemEntry
            
                if burnerStarts > 1:
                    self.activeHeatingOperatingMode = 3
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"Switch  : Heizen mit WW => Reduziert{}".format(forceRetryMsg))
        
        # Reduziert
        elif currentOperatingMode == 3:
            # Wenn Temperatur seit XX min OK ist und der brenner sowieso aus ist kann gleich in 'Nur WW' gewechselt werden
            if not isHeatingRequested:
                self.activeHeatingOperatingMode = 1
                sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                self.log.info(u"Switch  : Reduziert => Nur WW. Temperature reached max value{}".format(forceRetryMsg))
            else:
                # 'timeInterval' ist zwischen 10 und 60 min, je nach Aussentemperatur
                
                timeInterval = 10
                if currentOutdoorTemp > 0:
                    timeInterval = int( math.floor( ( ( currentOutdoorTemp * 50.0 ) / 20.0 ) + 10.0 ) )
                    if timeInterval > 60: timeInterval = 60
                
                # Dauernd reduziert läuft seit mindestens XX Minuten
                if forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(timeInterval) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"Switch  : Reduziert => Heizen mit WW • after {} min.{}".format(timeInterval,forceRetryMsg))
