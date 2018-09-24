import math
from org.joda.time import DateTime, DateTimeZone

from marvin.helper import rule, getNow, getGroupMember, itemLastUpdateOlderThen, getHistoricItemState, getHistoricItemEntry, getItemState, getItem, postUpdate, postUpdateIfChanged, sendCommand
from openhab.triggers import CronTrigger, ItemStateChangeTrigger
from openhab.actions import Transformation

activeHeatingOperatingMode = -1
outdatetForecast = None
openFFContacts = None
openSFContacts = None

def isOutdatetForecast(self, recheck = False):
    global outdatetForecast
    if recheck or outdatetForecast is None:
        outdatetForecast = itemLastUpdateOlderThen("Temperature_Garden_Forecast4", getNow().minusMinutes(360) )
    return outdatetForecast


def getOpenWindows( self, reference, recheck = False ):
    global openFFContacts
    global openSFContacts
    
    if recheck or openSFContacts is None:
        # should be at least 2 minutes open
        initialReference = getNow().minusMinutes(2)

        openFFContacts = []
        door = getItem("Door_FF_Floor")
        if door.getState() == OPEN and itemLastUpdateOlderThen(door,initialReference):
            openFFContacts.append(door)
        for sensor in getGroupMember("Sensor_Window_FF"):
            if sensor.getName() != "Window_FF_Garage" and sensor.getState() == OPEN and itemLastUpdateOlderThen(sensor,initialReference):
                openFFContacts.append(sensor)

        openSFContacts = []
        for sensor in getGroupMember("Sensor_Window_SF"):
            if sensor.getName() != "Window_SF_Attic" and sensor.getState() == OPEN and itemLastUpdateOlderThen(sensor,initialReference):
                openSFContacts.append(sensor)

    if reference is not None:
        _ffOpenWindowCount = len(filter(lambda window: itemLastUpdateOlderThen(window,reference), openFFContacts))
        _sfOpenWindowCount = len(filter(lambda window: itemLastUpdateOlderThen(window,reference), openSFContacts))
        return _ffOpenWindowCount, _sfOpenWindowCount
        
    return len(openFFContacts), len(openSFContacts)


def getCloudData( self, cloudCoverItem ):
    cloudCover = 0.0
    if not isOutdatetForecast(self,False):
        cloudCover = getItemState(cloudCoverItem).doubleValue()
    else:
        self.log.info("Forecast: ERROR • Fall back to full cloud cover.")
        cloudCover = 9.0

    return cloudCover


def getSunData( self, time ):

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
    if isBreak:
        azimut = math.acos(y) / K
    else:
        azimut = 360.0 - math.acos(y) / K

    #_elevation = getItemState("Sun_Elevation")
    #_azimut = getItemState("Sun_Azimuth")

    #self.log.info("ELEVATION: " + str(elevation) )
    #self.log.info("ELEVATION: " + str(_elevation) )
    #self.log.info("AZIMUT: " + str(azimut) )
    #self.log.info("AZIMUT: " + str(_azimut) )

    return elevation, azimut


def cleanupChargeLevel( self, totalChargeLevel, _cleanableChargeDiff ):

    _totalChargeLevel = totalChargeLevel - _cleanableChargeDiff
    if _totalChargeLevel < 0.0:
        _totalChargeLevel = 0.0

    return round( _totalChargeLevel, 1 )


def getStableValue( self, item, checkTimeRange ):

    currentEndTime = getNow()
    currentEndTimeMillis = currentEndTime.getMillis()
    minTimeMillis = currentEndTimeMillis - ( checkTimeRange * 60 * 1000 )

    value = 0.0
    duration = 0
    
    #self.log.info("test",""+now.minusMinutes(checkTimeRange) + " " + minTimestamp)

    while True:
        entry = getHistoricItemEntry(item, currentEndTime )

        currentStartMillis = entry.getTimestamp().getTime()
        _value = entry.getState().doubleValue()

        if currentStartMillis < minTimeMillis:
            currentStartMillis = minTimeMillis

        _duration = currentEndTimeMillis - currentStartMillis

        duration = duration + _duration
        value = value + ( _value * _duration )

        currentEndTimeMillis = currentStartMillis -1

        if currentEndTimeMillis < minTimeMillis:
            break

        currentEndTime = DateTime(currentEndTimeMillis)

    value = ( value / duration )

    # round to 1 decimal point like all "final" temperatures
    return round( value, 1 )


def getCurrentHeatingPowerPerMinute( self, maxHeatingPowerPerMinute ):
    pumpSpeed = getItemState("Heating_Circuit_Pump_Speed").doubleValue()
    if pumpSpeed == 0.0:
        return 0.0
    
    _referencePower = 1143 # per Watt je m³/K
    _maxVolume = 0.54

    outValue = getItemState("Heating_Temperature_Pipe_Out").doubleValue()
    inValue = getItemState("Heating_Temperature_Pipe_In").doubleValue()
    circulationDiff = outValue - inValue
    pumpVolume = round( ( _maxVolume * pumpSpeed ) / 100.0, 2 )
    currentHeatingPowerPerMinute = round( ( _referencePower * pumpVolume * circulationDiff ) / 60.0, 1 )

    #self.log.info("hc_inf","Heating : Diff "+circulationDiff+"°C • VL " + outValue + "°C • RL " + inValue + "°C")
    #self.log.info("hc_dbg","        : Speed "+pumpSpeed+"% • Volume "+pumpVolume+" m³ • HU " + currentHeatingPowerPerMinute + " W/min. (" + calculatedHeatingPowerPerMinute + " W/min.) ⇧")

    return currentHeatingPowerPerMinute


def getMaxHeatingPowerPerMinute( self ):

    #Leistung
    #2016-02-22 17:59:05		25.00 ... 26.50			26.5
    #2016-02-22 19:20:05		25.00 ... 26.50			25.0

    #Ticks
    #2016-02-22 17:59:05		305331
    #2016-02-22 19:20:05		305409

    #78 ticks	=> 0,78 m³

    # 71 min => 0,78
    # 60 min => 0,66

    # 0,66 m³ * 10,08 => 6,65 KW

    #6,65kw 	=>	25.7%
    #25,87kw	=>	100%

    # ??? 19 KW / h (Product ID => CE-0085CN0050)
    # 26KW is reduced to 19KW because there is no 100% efficiency
    # But it is a Vitodens 200-W Typ B2HA mit 13kW ???

    # max heating power is 69% => 13KW
    # that means 100% => 19KW

    # * 0.88 to adapt inaccurate messured heating power
    #return round( ( 19000.0 * 0.88 / 60.0 ), 1 )
    return round( 19000.0 / 60.0, 1 )


def getPossiblePowerValue( self, maxHeatingPowerPerMinute, outdoorTemperature, currentHeatingPowerPerMinute ):

    _possiblePowerValue = 0.0
    _possibleHeatingPowerPerMinute = 0.0

    if currentHeatingPowerPerMinute > 0.0:
        _possiblePowerValue = getItemState("Heating_Circuit_Pump_Speed").doubleValue()
        _possibleHeatingPowerPerMinute = currentHeatingPowerPerMinute
    else:
        # -20 => 40%
        # 20 => 20%
        
        # XX => ??
        # 40 => -20
        
        # 20°C 	=> 30°C			=> 20%
        # 10°C 	=> 33°C
        # 0°C 		=> 36°C			=> 32%
        # -10°C 	=> 39°C
        # -20 		=> 42°C			=> 37%
        
        _possiblePowerValue = 0.0
        if outdoorTemperature < -20.0:
            _possiblePowerValue = 40.0
        elif outdoorTemperature > 20.0:
            _possiblePowerValue = 20.0
        else:
            _possiblePowerValue = round( ( ( ( outdoorTemperature + 20.0 ) * -20.0 ) / 40.0 ) + 40.0, 1 )

        _possibleHeatingPowerPerMinute = round( ( maxHeatingPowerPerMinute * _possiblePowerValue ) / 100.0, 1 )
        
    return _possiblePowerValue, _possibleHeatingPowerPerMinute


def getNeededEnergy( self, livingroomTemperature, bedroomTemperature ):

    # 15°C => 1.2250
    # 30°C => 1.1644

    # 0°C  => 0
    # 15°C => -0.0606

    _minDensity = 1.1644
    maxDensity = 1.2250
    _cAir = 1.005 # KJ / KG
    _jouleKWRatio = 3.6

    _lowerVolume = 231.8911
    _upperVolume = 216.5555

    _lowerFloorPower = 8840.2507013889
    _upperFloorPower = 5821.6669694445

    _lowerDensity = ( ( livingroomTemperature - 15.0 ) * ( _minDensity - maxDensity ) / 15.0 ) + maxDensity
    if _lowerDensity < _minDensity:
        _lowerDensity = _minDensity
    elif _lowerDensity > maxDensity:
        _lowerDensity = maxDensity

    _upperDensity = ( ( bedroomTemperature - 15.0 ) * ( _minDensity - maxDensity ) / 15.0 ) + maxDensity
    if _upperDensity < _minDensity:
        _upperDensity = _minDensity
    elif _upperDensity > maxDensity:
        _upperDensity = maxDensity

    _lowerAirPower = _lowerVolume * _cAir / _jouleKWRatio
    _upperAirPower = _upperVolume * _cAir / _jouleKWRatio

    lowerPower = _lowerFloorPower + _lowerAirPower
    upperPower = _upperFloorPower + _upperAirPower

    return lowerPower + upperPower


def getSunPowerPerMinute( self, referenceTime, cloudCoverItem, isForecast ):

    cloudCover = getCloudData( self, cloudCoverItem )
    elevation, azimut = getSunData( self, referenceTime )

    # 125° 1/2 der Hauswand	
    southMultiplier = 0
    if azimut >= 100 and azimut <= 260 and elevation >= 12.0:
        # 100° => -1
        # 260° => 1
        
        # 0° => 0
        # 160° => 2
        
        southX = ( ( azimut - 100.0 ) * 2.0 / 160.0 ) - 1.0
        southMultiplier = ( math.pow( southX, 10.0 ) * -1.0 ) + 1.0
        #logInfo("hc_inf"," "+southX+" " +southMultiplier)

    westMultiplier = 0
    if azimut >= 190 and azimut <= 350 and elevation >= 8.0:
        # 190° => -1
        # 350° => 1
        
        # 0° => 0
        # 160° => 2
        
        westX = ( ( azimut - 190.0 ) * 2.0 / 160.0 ) - 1.0
        westMultiplier = ( math.pow( westX, 10.0 ) * -1.0 ) + 1.0
        #logInfo("hc_inf"," "+westX+" " +westMultiplier)

    southActive = southMultiplier > 0.0
    westActive  = westMultiplier > 0.0

    # in the morning the sun must be above 20°
    # and in the evening the sun must be above 10°
    if southActive or westActive:
        _usedRadians = math.radians(elevation)
        if _usedRadians < 0.0:
            _usedRadians = 0.0
        
        # Cloud Cover is between 0 and 9 - but converting to 0 and 8
        # https://en.wikipedia.org/wiki/Okta
        _cloudCover = cloudCover
        if _cloudCover > 8.0:
            _cloudCover = 8.0
        _cloudCoverFactor = _cloudCover / 8.0
        
        # http://www.shodor.org/os411/courses/_master/tools/calculators/solarrad/
        _maxRadiation = 990.0 * math.sin( _usedRadians ) - 30.0
        if _maxRadiation < 0.0:
            _maxRadiation = 0.0
        _currentRadiation = _maxRadiation * ( 1.0 - 0.75 * math.pow( _cloudCoverFactor, 3.4 ) )

        # http://scool.larc.nasa.gov/lesson_plans/CloudCoverSolarRadiation.pdf
        #__maxRadiation = ( 990.0 * Math::sin( _usedRadians ) )
        #if( __maxRadiation < 0.0 ) __maxRadiation = 0.0
        #__currentRadiation = ( __maxRadiation * ( 1.0 - 0.75 * Math::pow( _cloudCoverFactor, 3.4 ) ) )
        
        #logInfo("hc_inf","OLD: "+_maxRadiation+" "+_currentRadiation)
        #logInfo("hc_inf","NEW: "+__maxRadiation+" "+__currentRadiation)
        
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
            if isForecast or getItemState("Shutters_FF_Livingroom_Terrace") == PercentType.ZERO:
                    _activeRadiation = _activeRadiation + ( ( 0.625 * 2.13 * 3.0 ) * _effectiveWestRadiation )
            if isForecast or getItemState("Shutters_FF_Livingroom_Couch") == PercentType.ZERO:
                    _activeRadiation = _activeRadiation + ( ( 0.655 * 2.13 * 2.0 ) * _effectiveWestRadiation )
        
        # NEW: 11,65195
        # OLD: 18,0814
        #logInfo("hc_inf","bathroom "+( 0.86 * 1.00 )+" "+( 1.135 * 1.25 ))
        #logInfo("hc_inf","dressingroom "+( 0.86 * 1.00 )+" "+( 1.135 * 1.25 ))
        #logInfo("hc_inf","bedroom "+( 0.615 * 1.00 * 3.0 )+" "+( 2.51 * 1.25 ))
        #logInfo("hc_inf","kitchen "+( 0.645 * 1.01 * 2.0 )+" "+( 1.76 * 1.25 ))
        #logInfo("hc_inf","terasse "+( 0.625 * 2.13 * 3.0 )+" "+( 2.51 * 2.32 ))
        #logInfo("hc_inf","couch "+( 0.655 * 2.13 * 2.0 )+" "+( 1.76 * 2.32 ))
        
        _activeRadiation = round( _activeRadiation / 60.0, 1 )
        _effectiveSouthRadiation = round( _effectiveSouthRadiation / 60.0, 1 )
        _effectiveWestRadiation = round( _effectiveWestRadiation / 60.0, 1 )

        activeDirections = []
        if southActive:
            activeDirections.append("S")
        if westActive:
            activeDirections.append("W")
        activeMsg = u" • {}".format("+".join(activeDirections))
    else:
        _activeRadiation = 0.0
        _effectiveSouthRadiation = 0.0
        _effectiveWestRadiation = 0.0

        activeMsg = u""
        
    sunElevationMsg = round( elevation, 3 )
    sunAzimutMsg = round( azimut, 3 )

    self.log.info(u"        : Elevation {}° • Azimut {}° • Clouds {} octas{}".format(sunElevationMsg,sunAzimutMsg,cloudCover,activeMsg) )

    return _activeRadiation, _effectiveSouthRadiation, _effectiveWestRadiation


def getCoolingPowerPerMinute( self, outdoorTemperature, livingroomTemperature, bedroomTemperature, atticTemperature, sunPower, ffOpenWindowCount, sfOpenWindowCount ):

    densitiyAir = 1.2041
    cAir = 1.005

    _lowerVolume = 231.8911
    _upperVolume = 216.5555

    # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
    _totalVolume = ( _lowerVolume + _upperVolume )
    _n50 = 1.0
    _e = 0.07
    _f = 15.0

    _floorUValue = 17.1337491
    _egUValue = 53.28108965
    _ogUValue = 43.8325976
    _atticUValue = 14.3699714

    # https://www.u-wert.net
    floorPower = _floorUValue * ( livingroomTemperature - outdoorTemperature )
    if floorPower < 0.0:
        floorPower = 0.0

    egPower = _egUValue * ( livingroomTemperature - outdoorTemperature )
    #if egPower < 0.0: egPower = 0.0

    ogPower = _ogUValue * ( bedroomTemperature - outdoorTemperature )
    #if ogPower < 0.0: ogPower = 0.0

    atticPower = _atticUValue * ( bedroomTemperature - atticTemperature )
    #if atticPower < 0.0: atticPower = 0.0

    # *** Calculate power loss by ventilation ***
    _ventilationLevel = getItemState("Ventilation_Incoming").intValue()
    _ventilationTempDiff = getItemState("Ventilation_Indoor_Outgoing_Temperature").doubleValue() - getItemState("Ventilation_Indoor_Incoming_Temperature").doubleValue()
    if _ventilationTempDiff < 0.0:
        _ventilationTempDiff = 0.0

    # Ventilation Power
    # 15% => 40m³/h		XX => ?
    # 100% => 350m³/h		85 => 310
    _ventilationVolume = ( ( ( _ventilationLevel - 15.0 ) * 310.0 ) / 85.0 ) + 40.0
    _ventilationUValue = _ventilationVolume * densitiyAir * cAir
    _ventilationPowerInKJ = _ventilationUValue * _ventilationTempDiff
    ventilationPowerInW = _ventilationPowerInKJ / 3.6

    # Leaking Power
    _leakingTemperatureDiff = bedroomTemperature - outdoorTemperature
    #if( _leakingTemperatureDiff < 0.0 ) _leakingTemperatureDiff = 0.0
    _leakingVolume = ( _totalVolume * _n50 * _e ) / ( 1 + ( _f / _e ) * ( ( ( 0.1 * 0.4 ) / _n50 ) * ( ( 0.1 * 0.4 ) / _n50 ) ) )
    _leakingUValue = _leakingVolume * densitiyAir * cAir
    _leakingPowerInKJ = _leakingUValue * _leakingTemperatureDiff
    leakingPowerInW = _leakingPowerInKJ / 3.6

    # Open Window Power
    _maxEgOpenWindow = 6.0
    _maxOgOpenWindow = 5.0

    egExchangePower = ( ( egPower * ffOpenWindowCount ) / _maxEgOpenWindow ) * 2.0
    ogExchangePower = ( ( ogPower * sfOpenWindowCount ) / _maxOgOpenWindow ) * 2.0

    baseMsg = round( ( ( floorPower + egPower + ogPower + atticPower ) / 60.0 ) * -10.0 ) / 10.0
    ventilationMsg = round( ( ( ventilationPowerInW / 60.0 ) * -10.0 ) ) / 10.0
    leakingMsg = round( ( leakingPowerInW / 60.0 ) * -10.0 ) / 10.0
    windowMsg = round( ( ( egExchangePower + ogExchangePower ) / 60.0 ) * -10.0 ) / 10.0

    self.log.info(u"        : Building {} • Air {} • Leak {} • Window {} • Sun {}".format(baseMsg,ventilationMsg,leakingMsg,windowMsg,sunPower) )

    totalPower = ( floorPower + egPower + ogPower + atticPower ) + ventilationPowerInW + leakingPowerInW + egExchangePower + ogExchangePower

    coolingPower = round( ( totalPower / 60.0 ) - sunPower, 1 )

    return coolingPower


def getOutdoorDependingReduction( self, coolingPowerPerMinute ):
    # more than zeor means cooling => no reduction
    if coolingPowerPerMinute >= 0:
        return 0.0

    # less than zero means - sun heating
    # -300 => max reduction
    if coolingPowerPerMinute <= -300:
        return 2.0

    # 0 => 0.0
    # 300 => 2.0
    value = ( coolingPowerPerMinute * 2.0 ) / -300.0

    #logInfo("hc_inf","" + value + " " + ( Math::round( ( value * 10.0 ).doubleValue ) / 10.0 ).doubleValue )

    return value


def getLazyReduction( self, zoneLevel, startZoneLevel, stopZoneLevel, possibleLazyReduction ):
    if startZoneLevel < stopZoneLevel:
        # Temp OK (No heating demand)
        if getItemState("Heating_Demand").intValue() == 0:
            # No lazy reduction possible if charge level is too low
            if zoneLevel <= startZoneLevel:
                self.log.info("        : No lazy reduction [ZONE LOW]")		
                return 0.0
        # Temp Not OK
        else:
            # No lazy reduction possible if charge level is too low
            if zoneLevel <= stopZoneLevel:
                self.log.info("        : No lazy reduction [ZONE LOW]")		
                return 0.0

    # round to 1 decimal point like all "final" temperatures
    #newLazyReduction = ( Math::round( ( possibleLazyReduction * 10.0 ).doubleValue ) / 10.0 ).doubleValue
    newLazyReduction = math.floor( possibleLazyReduction * 10.0 ) / 10.0
    #logInfo("hc_dbg","        : Lazy reduction [CALC]")		

    return newLazyReduction


def isBufferHeating( self, zoneLevel, startZoneLevel, stopZoneLevel ):
    # Currently no buffer heating
    if getItemState("Heating_Demand").intValue() == 0:
        # No heating needed if buffer is changed more than startZoneLevel
        if zoneLevel > startZoneLevel:
            return False
    # Stop buffer heating if buffer more than 70% charged
    elif zoneLevel > stopZoneLevel:
        return False

    return stopZoneLevel > 0


def isNightMode( self, coolingDownMinutes, heatingUpMinutes, nightModeActive ):
    reference = getNow()
    hourOfTheDay = reference.getHourOfDay()

    if not nightModeActive:
        if hourOfTheDay < 2 or hourOfTheDay > 12:
            startOffset = coolingDownMinutes
            if startOffset <= 0:
                startOffset = 0

            # add 30 min offset to avoid falling below min heating time
            if getItemState("Heating_Demand").intValue() == 0 and startOffset < 60:
                startOffset = 60
                self.log.info(u"        : Night mode start offset is {} min ({} min. => 60 min.)".format(startOffset,coolingDownMinutes))
            else:
                self.log.info(u"        : Night mode start offset is {} min.".format(startOffset))
            
            reference = reference.plusMinutes( startOffset )
        else:
            self.log.info(u"        : Night mode is OFF")
            return False
    else:
        if hourOfTheDay >= 2 and hourOfTheDay < 12:
            endOffset = heatingUpMinutes
            if endOffset <= 0:
                endOffset = 0

            # add 1 hours offset because of lazy heating
            if getItemState("Heating_Demand").intValue() == 0 and endOffset > 0:
                lazyOffset = endOffset * 3
                if lazyOffset > 120:
                    lazyOffset = 120
                
                endOffset = endOffset + lazyOffset

                self.log.info(u"        : Night mode end offset is {} min ({} min. + {} min.)".format(endOffset,heatingUpMinutes,lazyOffset))
            else:
                self.log.info(u"        : Night mode end offset is {} min.".format(endOffset))
            
            reference = reference.plusMinutes( endOffset )
        else:
            self.log.info(u"        : Night mode is ON")
            return True

    day    = reference.getDayOfWeek()
    hour   = reference.getHourOfDay()
    minute = reference.getMinuteOfHour()

    _nightModeActive = False

    #Freitag
    if day == 5:
        if hour < 6 or ( hour == 6 and minute >= 30 ) or hour >= 24:
            _nightModeActive = True
    # Samstag
    elif day == 6:
        if hour < 9 or hour >= 24:
            _nightModeActive = True
    # Sonntag
    elif day == 7:
        if hour < 9 or hour >= 23 or ( hour == 22 and minute >= 30 ):
            _nightModeActive = True
    else:
        if hour < 6 or ( hour == 6 and minute >= 30 ) or hour >= 23 or ( hour == 22 and minute >= 30 ):
            _nightModeActive = True

    return _nightModeActive


def getHeatingTargetDiff( self, currentLivingroomTemp, targetLivingroomTemp, currentBedroomTemp, targetBedroomTemp ):
    livingroomDifference = targetLivingroomTemp - currentLivingroomTemp
    bedroomDifference = targetBedroomTemp - currentBedroomTemp

    difference = livingroomDifference
    if bedroomDifference > difference:
        difference = bedroomDifference

    return round( difference, 1 )


@rule("heating_control.py")
class CalculateChargeLevelRule:
    def __init__(self):
        self.triggers = [CronTrigger("15 * * * * ?")]

    def execute(self, module, input):
        self.log.info(u">>>")

        now = getNow()
        
        heatingLivingroomTarget = round( getItemState("Heating_Temperature_Livingroom_Target").doubleValue(), 1 )
        heatingBedroomTarget = round( getItemState("Heating_Temperature_Bedroom_Target").doubleValue(), 1 )

        currentLivingroomTemp = getStableValue( self, "Temperature_FF_Livingroom", 10 )
        currentBedroomTemp = getStableValue( self, "Temperature_SF_Bedroom", 10 )
        currentAtticTemp = getStableValue( self, "Temperature_SF_Attic", 10 )
        currentOutdoorTemp = getStableValue( self, "Temperature_Garden", 10 )

        maxHeatingPowerPerMinute = getMaxHeatingPowerPerMinute(self)

        currentHeatingPowerPerMinute = getCurrentHeatingPowerPerMinute(self, maxHeatingPowerPerMinute)

        totalChargeLevel = getItemState("Heating_Charged").doubleValue()

        referenceTemp = getItemState("Heating_Reference").doubleValue()

        referenceLivingroomTemp = getStableValue( self, "Temperature_FF_Livingroom", 30 )

        if referenceLivingroomTemp != referenceTemp:
            if referenceLivingroomTemp < referenceTemp:
                self.log.info(u"Cleanup : Reference {} adjusted".format(referenceLivingroomTemp) )
            elif referenceLivingroomTemp > referenceTemp:
                _baseHeatingPower = getNeededEnergy(self, currentLivingroomTemp,currentBedroomTemp)
                _heatedUpTempDiff = referenceLivingroomTemp - referenceTemp
                totalChargeLevel = cleanupChargeLevel( self, totalChargeLevel, _baseHeatingPower * _heatedUpTempDiff )
                self.log.info(u"Cleanup : Reference {} and Charged {} adjusted".format(referenceLivingroomTemp,totalChargeLevel) )
            postUpdate("Heating_Reference", referenceLivingroomTemp )

        # *** Calculate cooling power per minute ***
        _sunPower, effectiveSouthRadiation, effectiveWestRadiation = getSunPowerPerMinute( self, now, "Cloud_Cover_Current", False )
        postUpdateIfChanged( "Solar_Power", _sunPower )
        #logInfo("hc_dbg","effectiveSouthRadiation: "+effectiveSouthRadiation )
        #logInfo("hc_dbg","effectiveWestRadiation: "+effectiveWestRadiation )
        
        if effectiveSouthRadiation > 0.0 || effectiveWestRadiation > 0.0:
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
            # ******************************************

        _ffOpenWindowCount, _sfOpenWindowCount = getOpenWindows( self, None, True )
        currentCoolingPowerPerMinute = getCoolingPowerPerMinute( self, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _ffOpenWindowCount, _sfOpenWindowCount )
        #currentCoolingPowerPerMinuteWithoutSunEffect = currentCoolingPowerPerMinute + sunPower
        #logInfo("hc_dbg","currentCoolingPowerPerMinuteWithoutSunEffect: "+currentCoolingPowerPerMinuteWithoutSunEffect )

        totalChargeLevel = totalChargeLevel - currentCoolingPowerPerMinute + currentHeatingPowerPerMinute
        totalChargeLevel = round( totalChargeLevel, 1 )
        if totalChargeLevel < 0.0:
            totalChargeLevel = 0.0

        postUpdateIfChanged("Heating_Charged", totalChargeLevel )

        currentHUMessage = u"{} W/min. ⇧".format(currentHeatingPowerPerMinute)
        currentCDMessage = u"{} W/min. ⇩ • {}°C".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp)
        self.log.info(u"Current : CD {} • HU {} • {} W".format(currentCDMessage,currentHUMessage,totalChargeLevel) )
        postUpdateIfChanged("Heating_Current_HU_Message", currentHUMessage )
        postUpdateIfChanged("Heating_Current_CD_Message", currentCDMessage )

        self.log.info(u"<<<")


@rule("heating_control.py")
class TemperatureCheckRule:
    def __init__(self):
        self.triggers = [CronTrigger("30 */2 * * * ?")]
        self.nightModeActive = False

    def execute(self, module, input):
        self.log.info(u">>>")
        
        startZoneLevel = 0
        referenceLazyTimeSlot = 35.0
        bedroomReduction = 3.0
        
        now = getNow()

        # not changed since 6 hours.
        forecast4Item = "Temperature_Garden_Forecast4"
        forecast8Item = "Temperature_Garden_Forecast8"
        if isOutdatetForecast(self,True):
            self.log.info(u"Forecast: ERROR • Fall back to current temperature.")
            forecast4Item = "Temperature_Garden"
            forecast8Item = "Temperature_Garden"

        currentLivingroomTemp = getStableValue( self, "Temperature_FF_Livingroom", 10 )
        currentBedroomTemp = getStableValue( self, "Temperature_SF_Bedroom", 10 )
        currentAtticTemp = getStableValue( self, "Temperature_SF_Attic", 10 )

        currentOutdoorTemp = getStableValue( self, "Temperature_Garden", 10 )
        currentOutdoorForecast4Temp = getStableValue( self, forecast4Item, 10 )
        currentOutdoorForecast8Temp = getStableValue( self, forecast8Item, 10 )	
            
        heatingTarget = round( getItemState("Temperature_Room_Target").doubleValue(), 1 )

        totalChargeLevel = round( getItemState("Heating_Charged").doubleValue(), 1 )
        
        baseHeatingPower = getNeededEnergy( self, currentLivingroomTemp,currentBedroomTemp)
        # heating power per 0.1 °C
        slotHeatingPower = round( baseHeatingPower * 0.1, 1 )

        maxHeatingPowerPerMinute = getMaxHeatingPowerPerMinute(self)

        currentHeatingPowerPerMinute = getCurrentHeatingPowerPerMinute(self,maxHeatingPowerPerMinute)

        # *** Calculate cooling power per minute ***
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = getSunPowerPerMinute( self, now, "Cloud_Cover_Current", False )
        _ffOpenWindowCount, _sfOpenWindowCount = getOpenWindows( self, None )
        currentCoolingPowerPerMinute = getCoolingPowerPerMinute( self, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _ffOpenWindowCount, _sfOpenWindowCount )
        # ******************************************

        # *** calculate available heating power ***
        _possiblePowerValue, _possibleHeatingPowerPerMinute = getPossiblePowerValue( self, maxHeatingPowerPerMinute,currentOutdoorTemp,currentHeatingPowerPerMinute)

        availableHeatingPowerPerMinute = round( _possibleHeatingPowerPerMinute - currentCoolingPowerPerMinute, 1 )
        _currentCDMessage = u"CD {} W/min. ⇩ • {}°C".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp)
        _possibleHUMessage = u"HU {} W/min. ⇧ • {}%".format(_possibleHeatingPowerPerMinute,_possiblePowerValue)
        self.log.info(u"Current : {} • {}".format(_currentCDMessage,_possibleHUMessage) )
        postUpdateIfChanged("Heating_Forecast_HU_Message", _possibleHUMessage )
        # *****************************************
        
        # 15min range is used for forecast
        _ffOpenWindowCount15, _sfOpenWindowCount15 = getOpenWindows( self, now.minusMinutes(15) )
        
        # *** 4Std FORECAST ***
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = getSunPowerPerMinute( self, now.plusMinutes(240), "Cloud_Cover_Forecast4", True )
        currentForecast4CoolingPowerPerMinute = getCoolingPowerPerMinute( self, currentOutdoorForecast4Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _ffOpenWindowCount15, _sfOpenWindowCount15 )
        forecast4CDMessage = u"CD {} W/min. ⇩ • {}°C".format(( currentForecast4CoolingPowerPerMinute * -1 ),currentOutdoorForecast4Temp)
        self.log.info(u"Forecast: 4h • {}".format(forecast4CDMessage) )
        postUpdateIfChanged("Heating_Forecast4_CD_Message", forecast4CDMessage )
        # ****************

        # *** 8Std FORECAST ***
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = getSunPowerPerMinute( self, now.plusMinutes(480), "Cloud_Cover_Forecast8", True )
        currentForecast8CoolingPowerPerMinute = getCoolingPowerPerMinute( self, currentOutdoorForecast8Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _ffOpenWindowCount15, _sfOpenWindowCount15 )
        forecast8CDMessage = u"CD {} W/min. ⇩ • {}°C".format(( currentForecast8CoolingPowerPerMinute * -1 ),currentOutdoorForecast8Temp)
        self.log.info(u"Forecast: 8h • {}".format(forecast8CDMessage) )
        postUpdateIfChanged("Heating_Forecast8_CD_Message", forecast8CDMessage )
        # ****************

        # *** Outdoor depending reductions ***
        # current cooling should count full
        currentOutdoorReduction = getOutdoorDependingReduction(self,currentCoolingPowerPerMinute)
        # closed cooling forecast should count 90%
        forecast4outdoorReduction = getOutdoorDependingReduction(self,currentForecast4CoolingPowerPerMinute) * 0.8
        # cooling forecast in 8 hours should count 80%
        forecast8outdoorReduction = getOutdoorDependingReduction(self,currentForecast8CoolingPowerPerMinute) * 0.6
        
        outdoorReduction = currentOutdoorReduction + forecast4outdoorReduction + forecast8outdoorReduction
        if outdoorReduction > 0.0:
            outdoorReduction = outdoorReduction + 0.1

        #logInfo("test",""+currentOutdoorReduction+" "+forecast4outdoorReduction+" "+forecast8outdoorReduction)
        
        outdoorReduction = round( outdoorReduction, 1 )
        # ************************************
        
        # *** Cleanup chargeLevel to reflect real available energy ***
        referenceTemp = getItemState("Heating_Reference").doubleValue()
        currentChargeLevel = totalChargeLevel
        
        if currentLivingroomTemp > referenceTemp:
            _heatedUpTempDiff = currentLivingroomTemp - referenceTemp
            currentChargeLevel = cleanupChargeLevel( self, currentChargeLevel, baseHeatingPower * _heatedUpTempDiff )
        
        _heatingTargetDiff = heatingTarget - currentLivingroomTemp - outdoorReduction
        if _heatingTargetDiff < 0.0:
            _heatingTargetDiff = 0.0
        _neededHeatingPower = round( baseHeatingPower * _heatingTargetDiff, 1 )

        # Energy available after lazy charge calculation 
        additionalChargeLevel = round( currentChargeLevel - _neededHeatingPower, 1 )
        if additionalChargeLevel < 0.0:
            additionalChargeLevel = 0.0

        # Needed energy to reach target
        missingChargeLevel = round( _neededHeatingPower - currentChargeLevel, 1 )
        if missingChargeLevel < 0.0:
            missingChargeLevel = 0.0
        # ************************************************************
        
        #logInfo("hc inf","1 "+currentChargeLevel)
        #logInfo("hc inf","2 "+_neededHeatingPower)
        #logInfo("hc inf","3 "+additionalChargeLevel)
        #logInfo("hc inf","4 "+missingChargeLevel)
        #logInfo("hc inf","5 "+slotHeatingPower)
        #logInfo("hc inf","6 "+baseHeatingPower)
        
        # *** Calculate "zoneLevelInPercent" ***	
        timeToHeatSlot = int( round( slotHeatingPower / availableHeatingPowerPerMinute ) )
        _baseHeatingPowerInKW = round( baseHeatingPower / 1000.0, 1 )

        self.log.info(u"Slot    : {} KW/K • {} W/0.1K • {} min. ⇧".format(_baseHeatingPowerInKW,slotHeatingPower,timeToHeatSlot) )

        # max lazy charge level depends on cooling powering during 45 min.
        stopZoneLevel = 0
        zoneMessage = ""
        if currentCoolingPowerPerMinute > 0.0 and currentForecast4CoolingPowerPerMinute > 0.0:
            maxLazyChargeLevel = round( referenceLazyTimeSlot * currentForecast4CoolingPowerPerMinute, 1 )
            if maxLazyChargeLevel < slotHeatingPower:
                maxLazyChargeLevel = slotHeatingPower
            stopZoneLevel = int( round( maxLazyChargeLevel * 100.0 / slotHeatingPower ) )
            zoneMessage = u"{} W • {}% ... {}%".format(maxLazyChargeLevel,startZoneLevel,stopZoneLevel)
        else:
            zoneMessage = u"{}% • too warm outside".format(stopZoneLevel)
        
        self.log.info(u"Zone    : {}".format(zoneMessage) )
        postUpdateIfChanged("Heating_Zone_Message", zoneMessage )

        zoneLevelInPercent = int( round( ( additionalChargeLevel * 100.0 ) / slotHeatingPower ) )

        chargeLevelMessage = u"{} W • {} W ({} W)".format(additionalChargeLevel,currentChargeLevel,totalChargeLevel) 
        postUpdateIfChanged("Heating_Max_LR_Message", chargeLevelMessage )

        self.log.info(u"Charged : {} • {}%".format(chargeLevelMessage,zoneLevelInPercent) )

        currentChargedMessage = u"{} W • {}%".format(additionalChargeLevel,zoneLevelInPercent)
        postUpdateIfChanged("Heating_Charged_Message", currentChargedMessage )
        # ****************************************

        # *** Calculate "possibleLazyReduction" ***	
        # must use "currentChargeLevel - additionalChargeLevel" to reflect the full possible range
        possibleLazyReduction = round( ( additionalChargeLevel / baseHeatingPower ) * 100.0 ) / 100.0

        #logInfo("hc inf","a "+possibleLazyReduction)
        #logInfo("hc inf","b "+additionalChargeLevel)
        #logInfo("hc inf","c "+baseHeatingPower)
        # *****************************************

        # *** Calculate "nightModeHeatingUpMinutes" ***	
        _nightModeHeatingUpPower = missingChargeLevel
        if _nightModeHeatingUpPower < 0.0:
            _nightModeHeatingUpPower = 0.0
        nightModeHeatingUpMinutes = int( round( _nightModeHeatingUpPower / availableHeatingPowerPerMinute ) )
        # *********************************************

        # *** Calculate "nightModeCoolingDownMinutes" ***
        _nightModeCoolingDownPower = additionalChargeLevel
        if _nightModeCoolingDownPower < 0.0:
            _nightModeCoolingDownPower = 0.0
        nightModeCoolingDownMinutes = 120
        if currentCoolingPowerPerMinute > 0.0:
            nightModeCoolingDownMinutes = int( round( _nightModeCoolingDownPower / currentCoolingPowerPerMinute ) )
        if nightModeCoolingDownMinutes > 120:
            nightModeCoolingDownMinutes = 120
        # **************************

        nightOffsetMessage = u"NHU {} min. ⇧ • NCD {} min. ⇩".format(nightModeHeatingUpMinutes,nightModeCoolingDownMinutes)
        self.log.info(u"        : Max. LR {}°C • {}".format(possibleLazyReduction,nightOffsetMessage) )
        postUpdateIfChanged("Heating_Night_Offset_Message", nightOffsetMessage )

        # *** Calculate "NR" night mode: reduction start and end depends on the buffered energy ***
        self.nightModeActive = isNightMode( self, nightModeCoolingDownMinutes, nightModeHeatingUpMinutes, self.nightModeActive )
        nightReduction = 0.0
        if self.nightModeActive:
            nightReduction = 2.0
        # ************************************************************************************

        # *** Define target temperatures ***
        targetLivingroomTemp = round( heatingTarget - nightReduction, 1 )
        targetBedroomTemp = round( heatingTarget - nightReduction - bedroomReduction, 1 )
        postUpdateIfChanged("Heating_Temperature_Livingroom_Target", targetLivingroomTemp )
        postUpdateIfChanged("Heating_Temperature_Bedroom_Target", targetBedroomTemp )
        # **********************************

        # *** Calculate missing degrees ***
        heatingTargetDiff = getHeatingTargetDiff( self, currentLivingroomTemp, targetLivingroomTemp, currentBedroomTemp, targetBedroomTemp )
        # *********************************

        # *** Calculate "LR" lazy heating ***
        lazyReduction = getLazyReduction( self, zoneLevelInPercent, startZoneLevel, stopZoneLevel, possibleLazyReduction)
        # ******************************

        heatingReductionsMessage = u"LR {}° ⇩ • OR {}°C ⇩".format(lazyReduction,outdoorReduction)
        self.log.info(u"Effects : {}".format(heatingReductionsMessage) )
        postUpdateIfChanged("Heating_Reduction_Message", heatingReductionsMessage )

        self.log.info(u"Rooms   : Livingroom {}°C (⇒ {}°C) • Bedroom {}°C (⇒ {}°)".format(currentLivingroomTemp,targetLivingroomTemp,currentBedroomTemp,targetBedroomTemp))
        
        # *** Analyse result ***
        heatingDemand = 0
        heatingType = ""

        if _ffOpenWindowCount15 + _sfOpenWindowCount15 < 2:
            #logInfo("hc inf","d "+heatingTargetDiff)
            #logInfo("hc inf","e "+lazyReduction)
            #logInfo("hc inf","f "+outdoorReduction)

            referenceTargetDiff = round( heatingTargetDiff - lazyReduction - outdoorReduction, 1 )

            #logInfo("hc inf","g "+referenceTargetDiff)
            
            if referenceTargetDiff > 0:
                heatingDemand = 1
                heatingType = u"HEATING NEEDED"
            elif referenceTargetDiff == 0.0:
                if isBufferHeating( self, zoneLevelInPercent, startZoneLevel, stopZoneLevel ):
                    heatingDemand = 1
                    heatingType = u"BUFFER HEATING NEEDED"
                else:
                    heatingType = u"NO HEATING NEEDED • TARGET REACHED"
            else:
                heatingType = u"NO HEATING NEEDED • TOO WARM"
            
            if lazyReduction > 0 or outdoorReduction > 0:
                heatingType = u"{} • REDUCED {}°".format(heatingType,( lazyReduction + outdoorReduction ))
        else:
            heatingType = u"NO HEATING NEEDED • TOO MANY OPEN WINDOWS"
        self.log.info(u"Demand  : {}".format(heatingType) )
        # **********************

        postUpdateIfChanged("Heating_Demand", heatingDemand )

        self.log.info(u"<<<")


@rule("heating_control.py")
class HeatingModeCheckRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Auto_Mode"),
            CronTrigger("45 */2 * * * ?")
        ]
        self.activeHeatingOperatingMode = -1

    def execute(self, module, input):
        if getItemState("Heating_Auto_Mode").intValue() != 1:
            return
        
        self.log.info(u">>>")
        
        now = getNow()

        # 0 - Abschalten
        # 1 - Nur WW
        # 2 - Heizen mit WW
        # 3 - Reduziert
        # 4 - Normal
        
        minNurWWChangeMinutes = 15 # 'Nur WW' sollte mindestens 15 min aktiv sein
        minMitWWChangeMinutes = 30 # 'Heizen mit WW' sollte mindestens 30 min aktiv sein
        
        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        
        isHeatingRequested = getItemState("Heating_Demand").intValue() == 1
        if self.activeHeatingOperatingMode == -1:
            self.activeHeatingOperatingMode = currentOperatingMode
        
        forceRetry = self.activeHeatingOperatingMode != currentOperatingMode
        if forceRetry:
            forceRetryMsg = " (RETRY)"
        else:
            forceRetryMsg = ""
        
        self.log.info(u"Demand  : {} • Mode: {}".format(isHeatingRequested,Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) )) )
        
        # Nur WW
        if currentOperatingMode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if isHeatingRequested and ( forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode", now.minusMinutes(minNurWWChangeMinutes)) ):
                self.activeHeatingOperatingMode = 2
                sendCommand("Heating_Operating_Mode", self.activeHeatingOperatingMode)
                self.log.info(u"       : Switch to 'Heizung mit WW' after 'Nur WW'{}".format(forceRetryMsg))

        # Heizen mit WW
        elif currentOperatingMode == 2:
            currentPowerState = getItemState("Heating_Power").intValue()
            
            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not isHeatingRequested and (currentPowerState == 0 or forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(minMitWWChangeMinutes)) ):
                self.activeHeatingOperatingMode = 1
                sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                sendCommand("Heating_Livingroom_Circuit",ON)
                self.log.info(u"       : Switch to 'Nur WW' after 'Heizung mit WW'{}".format(forceRetryMsg))
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
                    sendCommand("Heating_Livingroom_Circuit",ON)
                    self.log.info(u"       : Switch to 'Reduziert' after 'Heizung mit WW'{}".format(forceRetryMsg))
            else:
                livingroomTemperature = getItemState("Temperature_FF_Livingroom").doubleValue()
                targetTemperature = getItemState("Temperature_Room_Target").doubleValue() + 0.2
                
                #// Wenn Kreis an... Überprüfe ob es im WZ zu warm ist
                if getItemState("Heating_Livingroom_Circuit") == ON:
                    if livingroomTemperature > targetTemperature and itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(10)):
                        sendCommand("Heating_Livingroom_Circuit",OFF)
                        self.log.info(u"       : Switch Wohnzimmerkreis OFF{}".format(forceRetryMsg))
                # Wenn Kreis aus... überprüfe ob es im WZ zu kalt ist
                elif livingroomTemperature < targetTemperature:
                    sendCommand("Heating_Livingroom_Circuit",ON)
                    self.log.info(u"       : Switch Wohnzimmerkreis ON{}".format(forceRetryMsg))
        
        # Reduziert
        elif currentOperatingMode == 3:
            # Wenn Temperatur seit XX min OK ist und der brenner sowieso aus ist kann gleich in 'Nur WW' gewechselt werden
            if not isHeatingRequested:
                self.activeHeatingOperatingMode = 1
                sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                self.log.info(u"       : Switch to 'Nur WW' after 'Reduziert'. Temperature reached max value{}".format(forceRetryMsg))
            else:
                # 'timeInterval' ist zwischen 10 und 60 min, je nach Aussentemperatur
                
                timeInterval = 10
                if getItemState("Heating_Temperature_Outdoor").doubleValue() > 0:
                    timeInterval = int( math.floor( ( ( getItemState("Heating_Temperature_Outdoor").doubleValue() * 50.0 ) / 20.0 ) + 10.0 ) )
                    if timeInterval > 60:
                        timeInterval = 60
                
                # Dauernd reduziert läuft seit mindestens XX Minuten
                if forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(timeInterval) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"       : Switch to 'Heizung mit WW' after {} minutes 'Reduziert'{}".format(timeInterval,forceRetryMsg))

        self.log.info(u"<<<")
