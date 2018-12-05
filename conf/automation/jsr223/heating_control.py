import math
from org.joda.time import DateTime, DateTimeZone
from org.joda.time.format import DateTimeFormat

from marvin.helper import rule, getNow, getGroupMember, itemLastUpdateOlderThen, getItemLastUpdate, getHistoricItemState, getHistoricItemEntry, getItemState, getMaxItemState, getItem, postUpdate, postUpdateIfChanged, sendCommand
from openhab.triggers import CronTrigger, ItemStateChangeTrigger
from openhab.actions import Transformation

OFFSET_FORMATTER = DateTimeFormat.forPattern("HH:mm")

BEDROOM_REDUCTION = 3.0
MIN_HEATING_TIME = 30 # 'Heizen mit WW' should be active at least for 30 min.
MIN_ONLY_WW_TIME = 15 # 'Nur WW' should be active at least for 15 min.

outdatetForecast = None
openFFContacts = None
openSFContacts = None

class HeatingHelper:
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

    def _getCloudData( self, cloudCoverItem ):
        if not self.isOutdatetForecast(False):
            return getItemState(cloudCoverItem).doubleValue()

        self.log.info(u"Forecast: ERROR • Fall back to full cloud cover.")
        return 9.0

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

    def getSunPowerPerMinute( self, logPrefix, referenceTime, cloudCoverItem, isForecast ):

        cloudCover = self._getCloudData( cloudCoverItem )
        elevation, azimut = self._getSunData( referenceTime )

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
            
        sunElevationMsg = int( round( elevation, 0 ) )
        sunAzimutMsg = int( round( azimut, 0 ) )

        self.log.info(u"{} Azimut {}° • Elevation {}° • Clouds {} octas{}".format(logPrefix, sunAzimutMsg, sunElevationMsg, cloudCover, activeMsg) )

        return _activeRadiation, _effectiveSouthRadiation, _effectiveWestRadiation

    def getNeededEnergyForOneDegrees( self, livingroomTemperature, bedroomTemperature ):

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

        _lowerFloorPower = 10380.7042847222
        _upperFloorPower = 5876.25113611111

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

    def getHeatingPowerPerMinute( self, pumpSpeed, temperature_Pipe_Out, temperature_Pipe_In ):
        # To warmup 1 liter of wather you need 4,182 Kilojoule
        # 1 Wh == 3,6 kJ
        # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
        _referencePower = 1162 # per Watt je m³/K
        #_maxVolume = 1.2 # 1200l max Volumenstrom of a Vitodens 200-W Typ B2HA with 13kW
        _maxVolume = 0.584 # 584l Nenn-Umlaufwassermenge of a Vitodens 200-W Typ B2HA with 13kW

        circulationDiff = temperature_Pipe_Out - temperature_Pipe_In
        pumpVolume = round( ( _maxVolume * pumpSpeed ) / 100.0, 2 )
        currentHeatingPowerPerMinute = round( ( _referencePower * pumpVolume * circulationDiff ) / 60.0, 1 )
        return currentHeatingPowerPerMinute, pumpVolume
    
    def getCurrentHeatingPowerPerMinute( self ):
        pumpSpeed = getItemState("Heating_Circuit_Pump_Speed").intValue()
        if pumpSpeed == 0:
            return 0.0, pumpSpeed
        
        outValue = getItemState("Heating_Temperature_Pipe_Out").doubleValue()
        inValue = getItemState("Heating_Temperature_Pipe_In").doubleValue()

        currentHeatingPowerPerMinute, pumpVolume = self.getHeatingPowerPerMinute(pumpSpeed,outValue,inValue)

        self.log.info(u"Heating : Diff {}°C • VL {}°C • RL {}°C".format((outValue - inValue),outValue,inValue))
        self.log.info(u"        : Speed {}% • Volume {} m³ • HU {} W/min.⇧".format(pumpSpeed,pumpVolume,currentHeatingPowerPerMinute))

        return currentHeatingPowerPerMinute, pumpSpeed

    def getCoolingPowerPerMinute( self, logPrefix, outdoorTempReference, outdoorTemperature, livingroomTemperature, bedroomTemperature, atticTemperature, sunPower, ffOpenWindowCount, sfOpenWindowCount ):

        densitiyAir = 1.2041
        cAir = 1.005

        _lowerVolume = 231.8911
        _upperVolume = 216.5555

        # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
        _totalVolume = ( _lowerVolume + _upperVolume )
        _n50 = 1.0
        _e = 0.07
        _f = 15.0

        # https://www.ubakus.de/u-wert-rechner/
        _floorUValue = 24.0798636
        _egUValue = 56.78375865
        _ogUValue = 46.6798656
        _atticUValue = 15.6883174

        # https://www.u-wert.net
        floorPower = _floorUValue * ( livingroomTemperature - outdoorTemperature )
        #if floorPower < 0.0: floorPower = 0.0

        egPower = _egUValue * ( livingroomTemperature - outdoorTemperature )
        #if egPower < 0.0: egPower = 0.0

        ogPower = _ogUValue * ( bedroomTemperature - outdoorTemperature )
        #if ogPower < 0.0: ogPower = 0.0

        atticPower = _atticUValue * ( bedroomTemperature - atticTemperature )
        #if atticPower < 0.0: atticPower = 0.0

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

        self.log.info(u"{} Wall {} • Air {} • Leak {} • Window {} • Sun {}".format(logPrefix, baseMsg, ventilationMsg, leakingMsg, windowMsg, sunPower) )

        totalPower = ( floorPower + egPower + ogPower + atticPower ) + ventilationPowerInW + leakingPowerInW + egExchangePower + ogExchangePower

        coolingPower = round( ( totalPower / 60.0 ) - sunPower, 1 )

        return coolingPower

    def _calculateCurrentCoolingPowerPerMinute(self, now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, isChargeLevelCalculation ):
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = self.getSunPowerPerMinute( u"Current :", now, "Cloud_Cover_Current", False )
        _ffOpenWindowCount, _sfOpenWindowCount = self.getOpenWindows( None, isChargeLevelCalculation == True )
        _currentCoolingPowerPerMinute = self.getCoolingPowerPerMinute( u"        :", currentOutdoorTemp, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, _ffOpenWindowCount, _sfOpenWindowCount )
        return _currentCoolingPowerPerMinute, _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation

    def _cleanupChargeLevel( self, totalChargeLevel, _cleanableChargeDiff ):

        _totalChargeLevel = totalChargeLevel - _cleanableChargeDiff

        return round( _totalChargeLevel, 1 ) if _totalChargeLevel > 0.0 else 0.0

    def calculcateCurrentChargeLevel(self, totalChargeLevel, currentLivingroomTemp, baseHeatingPower, heatingTarget, outdoorReduction ):        
        # We have to calculate with cleaned values also if the "CalculateChargeLevelRule" was not cleaning it right now
        _referenceTemp = getItemState("Heating_Reference").doubleValue()
        _currentChargeLevel = totalChargeLevel
        if currentLivingroomTemp > _referenceTemp:
            _heatedUpTempDiff = currentLivingroomTemp - _referenceTemp
            _currentChargeLevel = self._cleanupChargeLevel( _currentChargeLevel, baseHeatingPower * _heatedUpTempDiff )
        _heatingTargetDiff = heatingTarget - currentLivingroomTemp - outdoorReduction
        if _heatingTargetDiff < 0.0:
            _heatingTargetDiff = 0.0
        _neededHeatingPower = round( baseHeatingPower * _heatingTargetDiff, 1 )

        ### Energy available after lazy charge calculation 
        _additionalChargeLevel = round( _currentChargeLevel - _neededHeatingPower, 1 )
        if _additionalChargeLevel < 0.0:
            _additionalChargeLevel = 0.0

        ### Needed energy to reach target
        _missingChargeLevel = round( _neededHeatingPower - _currentChargeLevel, 1 )
        if _missingChargeLevel < 0.0:
            _missingChargeLevel = 0.0
        
        return _currentChargeLevel, _additionalChargeLevel, _missingChargeLevel

    def calculateAdjustedTotalChargeLevel(self, currentLivingroomTemp, currentBedroomTemp):
        _totalChargeLevel = getItemState("Heating_Charged").doubleValue()
        _referenceTemp = getItemState("Heating_Reference").doubleValue()
        _referenceLivingroomTemp = self.getStableValue( "Temperature_FF_Livingroom", 30 )
        if _referenceLivingroomTemp != _referenceTemp:
            if _referenceLivingroomTemp < _referenceTemp:
                self.log.info(u"Cleanup : Reference {} adjusted".format(_referenceLivingroomTemp) )
            elif _referenceLivingroomTemp > _referenceTemp:
                _baseHeatingPower = self.getNeededEnergyForOneDegrees( currentLivingroomTemp,currentBedroomTemp)
                _heatedUpTempDiff = _referenceLivingroomTemp - _referenceTemp
                _totalChargeLevel = self._cleanupChargeLevel( _totalChargeLevel, _baseHeatingPower * _heatedUpTempDiff )
                self.log.info(u"Cleanup : Reference {} and Charged {} adjusted".format(_referenceLivingroomTemp,_totalChargeLevel) )
            postUpdate("Heating_Reference", _referenceLivingroomTemp )
        return _totalChargeLevel
 
@rule("heating_control.py")
class CalculateChargeLevelRule(HeatingHelper):
    def __init__(self):
        self.triggers = [CronTrigger("15 * * * * ?")]

    def execute(self, module, input):
        now = getNow()
        
        self.log.info(u">>>")

        currentLivingroomTemp = self.getStableValue( "Temperature_FF_Livingroom", 10 )
        currentBedroomTemp = self.getStableValue( "Temperature_SF_Bedroom", 10 )
        currentAtticTemp = self.getStableValue( "Temperature_SF_Attic", 10 )
        currentOutdoorTemp = self.getStableValue( "Temperature_Garden", 10 )

        # Calculate the "real" heating power based on the pump speed.
        currentHeatingPowerPerMinute, currentPumpSpeedInPercent = self.getCurrentHeatingPowerPerMinute()

        # Get the house charge level. If we detect a house warmup, we remove "adjust" the needed amount energy for heating up in 0.1°C levels
        totalChargeLevel = self.calculateAdjustedTotalChargeLevel(currentLivingroomTemp, currentBedroomTemp)
    
        # Calculate current cooling power per minute, based on temperature differences, sun power and open windows
        currentCoolingPowerPerMinute = self.calculateCurrentCoolingPowerPerMinuteAndSetSunStates( now, currentOutdoorTemp, currentAtticTemp, currentBedroomTemp, currentLivingroomTemp)
                 
        # Apply difference between heating power and cooling power to the chage level
        totalChargeLevel = totalChargeLevel - currentCoolingPowerPerMinute + currentHeatingPowerPerMinute
        totalChargeLevel = round( totalChargeLevel, 1 )
        if totalChargeLevel < 0.0:
            totalChargeLevel = 0.0
        postUpdateIfChanged("Heating_Charged", totalChargeLevel )

        # some logs
        self.log.info(u"        : CD {} W/min. ({}°C) ⇧ • HU {} W/min. ({}%) ⇩".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp,currentHeatingPowerPerMinute,currentPumpSpeedInPercent) )
        self.log.info(u"Charged : {} W total incl. buffer".format(totalChargeLevel) )

        self.log.info(u"<<<")

    def calculateCurrentCoolingPowerPerMinuteAndSetSunStates(self, now, currentOutdoorTemp, currentAtticTemp, currentBedroomTemp, currentLivingroomTemp ):
      
        _currentCoolingPowerPerMinute, _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = self._calculateCurrentCoolingPowerPerMinute(now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, True)
        
        postUpdateIfChanged( "Solar_Power", _sunPower )

        if _effectiveSouthRadiation > 0.0 or _effectiveWestRadiation > 0.0:
          
            heatingLivingroomTarget = round( getItemState("Heating_Temperature_Livingroom_Target").doubleValue(), 1 )
            heatingBedroomTarget = round( getItemState("Heating_Temperature_Bedroom_Target").doubleValue(), 1 )

            atticRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Attic") == ON:
                if _effectiveSouthRadiation < 3.7 or currentAtticTemp < atticRef or currentOutdoorTemp < atticRef:
                    postUpdate("State_Sunprotection_Attic", OFF )
            elif _effectiveSouthRadiation > 3.8 and currentAtticTemp >= atticRef and currentOutdoorTemp >= atticRef:
                postUpdate("State_Sunprotection_Attic", ON )

            bathroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Bathroom") == ON:
                if _effectiveSouthRadiation < 3.7 or currentBedroomTemp < bathroomRef or currentOutdoorTemp < bathroomRef:
                    postUpdate("State_Sunprotection_Bathroom", OFF )
            elif _effectiveSouthRadiation > 3.8 and currentBedroomTemp >= bathroomRef and currentOutdoorTemp >= bathroomRef:
                postUpdate("State_Sunprotection_Bathroom", ON )

            dressingroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Dressingroom") == ON:
                if _effectiveSouthRadiation < 3.7 or currentBedroomTemp < dressingroomRef or currentOutdoorTemp < dressingroomRef:
                    postUpdate("State_Sunprotection_Dressingroom", OFF )
            elif _effectiveSouthRadiation > 3.8 and currentBedroomTemp >= dressingroomRef and currentOutdoorTemp >= dressingroomRef:
                postUpdate("State_Sunprotection_Dressingroom", ON )

            bedroomRef = heatingBedroomTarget - 1.0
            if getItemState("State_Sunprotection_Bedroom") == ON:
                if _effectiveWestRadiation < 3.7 or currentBedroomTemp < bedroomRef or currentOutdoorTemp < bedroomRef:
                    postUpdate("State_Sunprotection_Bedroom", OFF )
            elif _effectiveWestRadiation > 3.8 and currentBedroomTemp >= bedroomRef and currentOutdoorTemp >= bedroomRef:
                postUpdate("State_Sunprotection_Bedroom", ON )

            livingroomRef = heatingLivingroomTarget - 1.0
            if getItemState("State_Sunprotection_Livingroom") == ON:
                if _effectiveWestRadiation < 3.7 or currentLivingroomTemp < livingroomRef or currentOutdoorTemp < livingroomRef:
                    postUpdate("State_Sunprotection_Livingroom", OFF )
            elif _effectiveWestRadiation > 3.8 and currentLivingroomTemp >= livingroomRef and currentOutdoorTemp >= livingroomRef:
                postUpdate("State_Sunprotection_Livingroom", ON )
        
        return _currentCoolingPowerPerMinute

@rule("heating_control.py")
class HeatingCheckRule(HeatingHelper):
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Auto_Mode"),
            CronTrigger("30 */2 * * * ?")
        ]
        self.nightModeActive = False
        self.forcedBufferReferenceTemperature = None
        self.forcedBufferTime = -1
        self.activeHeatingOperatingMode = -1

    def execute(self, module, input):
        now = getNow()

        self.log.info(u">>>")
        
        minBufferChargeLevel = 0
        
        # not changed since 6 hours.
        forecast4Item = "Temperature_Garden_Forecast4"
        forecast8Item = "Temperature_Garden_Forecast8"
        if self.isOutdatetForecast(True):
            self.log.info(u"Forecast: ERROR • Fall back to current temperature.")
            forecast4Item = "Temperature_Garden"
            forecast8Item = "Temperature_Garden"

        currentLivingroomTemp = self.getStableValue( "Temperature_FF_Livingroom", 10 )
        currentBedroomTemp = self.getStableValue( "Temperature_SF_Bedroom", 10 )
        currentAtticTemp = self.getStableValue( "Temperature_SF_Attic", 10 )

        currentOutdoorTemp = self.getStableValue( "Temperature_Garden", 10 )
        currentOutdoorForecast4Temp = self.getStableValue( forecast4Item, 10 )
        currentOutdoorForecast8Temp = self.getStableValue( forecast8Item, 10 )	
            
        heatingTarget = round( getItemState("Temperature_Room_Target").doubleValue(), 1 )

        totalChargeLevel = round( getItemState("Heating_Charged").doubleValue(), 1 )
        
        isHeatingDemand = getItemState("Heating_Demand").intValue() == 1

        # Get open windows during the last 15 min
        ffOpenWindowCount15, sfOpenWindowCount15 = self.getOpenWindows( now.minusMinutes(15) )

        # Get Needed energy to warmup the house by one degrees
        baseHeatingPower = self.getNeededEnergyForOneDegrees( currentLivingroomTemp,currentBedroomTemp)
        # Get Heating power for 0.1 °C
        slotHeatingPower = round( baseHeatingPower * 0.1, 1 )

        # Calculate cooling power in 8h
        currentForecast8CoolingPowerPerMinute = self.calculateCurrentForecast8CoolingPowerPerMinute( now, currentOutdoorTemp, currentOutdoorForecast8Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, ffOpenWindowCount15, sfOpenWindowCount15)

        # Calculate cooling power in 4h
        currentForecast4CoolingPowerPerMinute = self.calculateCurrentForecast4CoolingPowerPerMinute( now, currentOutdoorTemp, currentOutdoorForecast4Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, ffOpenWindowCount15, sfOpenWindowCount15)

        # Calculate the "real" heating power based on the pump speed.
        currentHeatingPowerPerMinute, currentPumpSpeedInPercent = self.getCurrentHeatingPowerPerMinute()

        # Calculate current cooling power per minute, based on temperature differences, sun power and open windows
        currentCoolingPowerPerMinute = self.calculateCurrentCoolingPowerPerMinute( now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp)
        
        # Calculate "available" heating power. Thats means current or possible heating power - current cooling power
        # This is the leftover to warmup the house
        availableHeatingPowerPerMinute = self.calculateAvailableHeatingPowerPerMinute( currentOutdoorTemp, currentHeatingPowerPerMinute, currentCoolingPowerPerMinute, currentPumpSpeedInPercent,currentLivingroomTemp)

        # Calculate reduction based on the current sun heating or the expected (forecast based) sun heating
        # This reduces the target temperature by the expected sun warmup and stops heating earlier, because sun heating is lazy.
        # EXPECTED LAZY SUN WARMUP
        outdoorReduction = self.calculateOutdoorReduction( currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, currentForecast8CoolingPowerPerMinute)
        
        # Calculate the charge level adjusted by possible heated up 0.1°C levels
        # currentChargeLevel - means the current house charge level
        # additionalChargeLevel - Value higher than 0 means we have more energy than needed to reach our target temperature
        # missingChargeLevel - Value higher than 0 means we need more energy to reach our target temperature
        currentChargeLevel, additionalChargeLevel, missingChargeLevel = self.calculcateCurrentChargeLevel(totalChargeLevel, currentLivingroomTemp, baseHeatingPower, heatingTarget, outdoorReduction)
    
        # Zone Level (BUFFER LEVEL) to stop buffer heating. Is based on cooling power.
        maxBufferChargeLevel = self.calculateMaxBufferChargeLevel( currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, slotHeatingPower)

        # Some log messages about charge values
        _timeToHeatSlot = int( round( slotHeatingPower / availableHeatingPowerPerMinute ) )
        _baseHeatingPowerInKW = round( baseHeatingPower / 1000.0, 1 )
        self.log.info(u"Slot    : {} KW/K • {} W/0.1K • {} min. ⇧".format(_baseHeatingPowerInKW,slotHeatingPower,_timeToHeatSlot) )

        _timeToHeatBuffer = int( round( maxBufferChargeLevel / availableHeatingPowerPerMinute ) )
        _bufferFilledInPercent = int( round( additionalChargeLevel * 100 / maxBufferChargeLevel, 0 ) )
        self.log.info(u"Buffer  : {}% filled • {} W ... {} W • {} min. ⇧".format( _bufferFilledInPercent, minBufferChargeLevel, maxBufferChargeLevel, _timeToHeatBuffer) )

        _totalLazyChargeMsg = u" ({} W)".format(totalChargeLevel) if currentChargeLevel != totalChargeLevel else u""
        self.log.info(u"Charged : {} W{} total incl. buffer".format( currentChargeLevel, _totalLazyChargeMsg) )
          
        # Calculate reduction based on available energy (=> Calculation of currentChargeLevel) to lazy warmup the house later
        # EXPECTED WARMUP TO REACH TARGET.
        # Here we calculate lazy reduction to reach 'referenceTargetDiff == 0' earlier        
        # Then we are able to check with 'isBufferHeating' if additionalChargeLevel is enough to stop heating 
        lazyReduction = round( ( ( currentChargeLevel - additionalChargeLevel ) / baseHeatingPower ) * 10.0 ) / 10.0
        #lazyReduction = 0.0 if isBufferHeatingNeeded else math.floor( _possibleLazyReduction * 10.0 ) / 10.0
        
        # Calculate night reduction
        # Night reduction start is earlier on higher coolingDownMinutes
        # and night reduction stops earlier on higher heatingUpMinutes
        _heatingUpMinutes = int( round( missingChargeLevel / availableHeatingPowerPerMinute ) )
        _coolingDownMinutes = int( round( additionalChargeLevel / currentCoolingPowerPerMinute ) ) if currentCoolingPowerPerMinute > 0.0 else 0
        self.log.info(u"        : NHU {} min. ⇧ • NCD {} min. ⇩".format(_heatingUpMinutes,_coolingDownMinutes) )
        nightReduction = self.calculateNightReduction( now, isHeatingDemand, _coolingDownMinutes, _heatingUpMinutes)
        
        # Calculate wanted target temperatures in livingroom and bedroom based on night reduction and bedroom/livingroom offset
        targetLivingroomTemp, targetBedroomTemp = self.calculateTargetTemperatures( heatingTarget, nightReduction)
        
        # Calculate missing degrees to reach target temperature
        heatingTargetDiff = self.getHeatingTargetDiff( currentLivingroomTemp, targetLivingroomTemp, currentBedroomTemp, targetBedroomTemp )
        
        # Switch livingroom circuit off if it is too warm
        currentLivingRoomCircuit = getItemState("Heating_Livingroom_Circuit")
        livingRoomCircuit = currentLivingRoomCircuit
        if currentLivingRoomCircuit == ON:
            if currentLivingroomTemp > targetLivingroomTemp + 0.2:
                livingRoomCircuit = OFF
        elif currentLivingroomTemp <= targetLivingroomTemp:
            livingRoomCircuit = ON

        # Some logs
        self.log.info(u"Effects : LR {}° ⇩ • OR {}°C ⇩ • NR {}°C ⇩ • LRC {}".format(lazyReduction,outdoorReduction,nightReduction, livingRoomCircuit ))
        self.log.info(u"Rooms   : Livingroom {}°C (⇒ {}°C) • Bedroom {}°C (⇒ {}°)".format(currentLivingroomTemp,targetLivingroomTemp,currentBedroomTemp,targetBedroomTemp))
               
        ### Analyse result
        if getItemState("Heating_Auto_Mode").intValue() == 1:
            heatingDemand = 0
            heatingType = ""

            ### Check heating demand
            if ffOpenWindowCount15 + sfOpenWindowCount15 < 2:

                referenceTargetDiff = round( heatingTargetDiff - lazyReduction - outdoorReduction, 1 )
                
                if referenceTargetDiff > 0:
                    heatingDemand = 1
                    heatingType = u"HEATING NEEDED"
                else:
                    # it is too warm inside, but outside it is very cold, so we need some buffer heating to avoid cold floors
                    forceBufferHeating = self.forcedBufferHeatingCheck( now, isHeatingDemand, referenceTargetDiff, slotHeatingPower, availableHeatingPowerPerMinute, currentCoolingPowerPerMinute)
                
                    if forceBufferHeating:
                        heatingDemand = 1
                        heatingType = u"FORCED BUFFER HEATING NEEDED"
                    elif referenceTargetDiff == 0.0:
                        # Check if buffer heating is needed
                        isBufferHeatingNeeded = self.isBufferHeating( isHeatingDemand, additionalChargeLevel, minBufferChargeLevel, maxBufferChargeLevel )
        
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

            if currentLivingRoomCircuit != livingRoomCircuit:
                sendCommand("Heating_Livingroom_Circuit",livingRoomCircuit)
                self.log.info(u"Switch  : Livingroom circuit {}".format(livingRoomCircuit))
        
            ### Call heating control
            self.controlHeating(now,heatingDemand,heatingTarget,currentOutdoorTemp)
        else:
            self.log.info(u"Demand  : SKIPPED • MANUAL MODE ACTIVE")
            postUpdateIfChanged("Heating_Demand", 0 )

        self.log.info(u"<<<")

    # Time after heating to see the full effect
    def getLazyTimeOffset(self,heatingMinutes):
        minutes = int( round( heatingMinutes / 3.0 ) ) + 60
        return minutes if minutes < 120 else 120

    def getHeatingTargetDiff( self, currentLivingroomTemp, targetLivingroomTemp, currentBedroomTemp, targetBedroomTemp ):
        livingroomDifference = targetLivingroomTemp - currentLivingroomTemp
        bedroomDifference = targetBedroomTemp - currentBedroomTemp

        difference = livingroomDifference if livingroomDifference > bedroomDifference else bedroomDifference
        
        return round( difference, 1 )

    def calculateTargetTemperatures(self, heatingTarget, nightReduction):
        _targetLivingroomTemp = round( heatingTarget - nightReduction, 1 )
        _targetBedroomTemp = round( heatingTarget - nightReduction - BEDROOM_REDUCTION, 1 )
        postUpdateIfChanged("Heating_Temperature_Livingroom_Target", _targetLivingroomTemp )
        postUpdateIfChanged("Heating_Temperature_Bedroom_Target", _targetBedroomTemp )
        return _targetLivingroomTemp, _targetBedroomTemp

    def calculateCurrentForecast8CoolingPowerPerMinute(self, now, currentOutdoorTemp, currentOutdoorForecast8Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, ffOpenWindowCount15, sfOpenWindowCount15):
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = self.getSunPowerPerMinute( u"FC 8h   :", now.plusMinutes(480), "Cloud_Cover_Forecast8", True )
        _currentForecast8CoolingPowerPerMinute = self.getCoolingPowerPerMinute( u"        :", currentOutdoorTemp, currentOutdoorForecast8Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, ffOpenWindowCount15, sfOpenWindowCount15 )
        self.log.info(u"        : CD {} W/min. ({}°C) ⇩".format(( _currentForecast8CoolingPowerPerMinute * -1 ),currentOutdoorForecast8Temp) )
        return _currentForecast8CoolingPowerPerMinute

    def calculateCurrentForecast4CoolingPowerPerMinute(self, now, currentOutdoorTemp, currentOutdoorForecast4Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, ffOpenWindowCount15, sfOpenWindowCount15):
        _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = self.getSunPowerPerMinute( u"FC 4h   :", now.plusMinutes(240), "Cloud_Cover_Forecast4", True )
        _currentForecast4CoolingPowerPerMinute = self.getCoolingPowerPerMinute( u"        :", currentOutdoorTemp, currentOutdoorForecast4Temp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, _sunPower, ffOpenWindowCount15, sfOpenWindowCount15 )
        self.log.info(u"        : CD {} W/min. ({}°C) ⇩".format(( _currentForecast4CoolingPowerPerMinute * -1 ),currentOutdoorForecast4Temp) )
        return _currentForecast4CoolingPowerPerMinute

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

    def calculateOutdoorReduction(self, currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute, currentForecast8CoolingPowerPerMinute):
        # Current cooling should count full
        _currentOutdoorReduction = self.getOutdoorDependingReduction(currentCoolingPowerPerMinute)
        # Closed cooling forecast should count 90%
        _forecast4outdoorReduction = self.getOutdoorDependingReduction(currentForecast4CoolingPowerPerMinute) * 0.8
        # Cooling forecast in 8 hours should count 80%
        _forecast8outdoorReduction = self.getOutdoorDependingReduction(currentForecast8CoolingPowerPerMinute) * 0.6
        _outdoorReduction = _currentOutdoorReduction + _forecast4outdoorReduction + _forecast8outdoorReduction
        if _outdoorReduction > 0.0:
            _outdoorReduction = _outdoorReduction + 0.1
        return round( _outdoorReduction, 1 )

    def calculateCurrentCoolingPowerPerMinute(self, now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp ):
      
        _currentCoolingPowerPerMinute, _sunPower, _effectiveSouthRadiation, _effectiveWestRadiation = self._calculateCurrentCoolingPowerPerMinute( now, currentOutdoorTemp, currentLivingroomTemp, currentBedroomTemp, currentAtticTemp, False)
      
        return _currentCoolingPowerPerMinute
              
    def calculateAvailableHeatingPowerPerMinute(self, currentOutdoorTemp, currentHeatingPowerPerMinute, currentCoolingPowerPerMinute, currentPumpSpeedInPercent,currentLivingroomTemp):   

        _possiblePowerValue = 0.0
        _possibleHeatingPowerPerMinute = 0.0

        if currentHeatingPowerPerMinute > 0.0:
            _possibleHeatingPowerPerMinute = currentHeatingPowerPerMinute
            _possiblePumpSpeedMsg = u"{}%".format(currentPumpSpeedInPercent)
        else:
            # Estimation is based on 100% heating pump speed and a max heating water temperature of 32°C
            _possibleHeatingPowerPerMinute, _possiblePumpVolume = self.getHeatingPowerPerMinute( 100.0, 32.0, currentLivingroomTemp )
            _possiblePumpSpeedMsg = u"FC"
            
        self.log.info(u"        : CD {} W/min. ({}°C) ⇩ • HU {} W/min. ({}) ⇧".format(( currentCoolingPowerPerMinute * -1 ),currentOutdoorTemp,_possibleHeatingPowerPerMinute,_possiblePumpSpeedMsg) )

        return round( _possibleHeatingPowerPerMinute - currentCoolingPowerPerMinute, 1 )

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
                if hour < 6 or ( hour == 6 and minute <= 30 ):
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

    def isNightMode( self, now, isHeatingDemand, coolingDownMinutes, heatingUpMinutes, nightModeActive ):
      reference = now
      hourOfTheDay = reference.getHourOfDay()
      
      if not nightModeActive:
          startOffset = coolingDownMinutes if coolingDownMinutes > 0 else 0
          #minStartOffset = MIN_HEATING_TIME + self.getLazyTimeOffset(MIN_HEATING_TIME)
          minStartOffset = self.getLazyTimeOffset(MIN_HEATING_TIME)
          
          # if heating not active, check if the night mode is far enough for a new heating cycle
          if not isHeatingDemand and startOffset < minStartOffset:
              startOffset = minStartOffset

          if hourOfTheDay > 12:
              reference = reference.plusMinutes( startOffset )
              _isNightMode = self.isNightModeTime(reference)
          else:
              _isNightMode = nightModeActive
              
          msg = u"start check at {} • {} min.".format(OFFSET_FORMATTER.print(reference),startOffset)
          
      else:
          endOffset = heatingUpMinutes if heatingUpMinutes > 0 else 0
          lazyTime = 0

          # check early enough to have enough time for lazy warming up
          # add time offset for lazy warming up after heating
          if not isHeatingDemand and endOffset > 0:
              lazyTime = self.getLazyTimeOffset(endOffset)
              endOffset = endOffset + lazyTime

          if hourOfTheDay < 12:
              reference = reference.plusMinutes( endOffset )
              _isNightMode = self.isNightModeTime(reference)
          else:
              _isNightMode = nightModeActive
      
          msg = u"end check at {} • {} min. • {} min. lazy".format(OFFSET_FORMATTER.print(reference),endOffset,lazyTime)
          
      self.log.info(u"        : Night mode {}".format(msg))

      return _isNightMode

    def calculateNightReduction(self, now, isHeatingDemand, coolingDownMinutes, heatingUpMinutes):
        self.nightModeActive = self.isNightMode(  now, isHeatingDemand, coolingDownMinutes, heatingUpMinutes, self.nightModeActive )
        return 2.0 if self.nightModeActive else 0.0
      
    def calculateMaxBufferChargeLevel(self, currentCoolingPowerPerMinute, currentForecast4CoolingPowerPerMinute,slotHeatingPower):
        if currentCoolingPowerPerMinute > 0.0 and currentForecast4CoolingPowerPerMinute > 0.0:
            # calculate max charge level for 45 min
            neededLazyChargeLevel = round( ( MIN_HEATING_TIME + MIN_ONLY_WW_TIME ) * currentForecast4CoolingPowerPerMinute, 1 )
            #stopZoneLevel = int( round( neededLazyChargeLevel * 100.0 / slotHeatingPower ) )
            return neededLazyChargeLevel
        return 0

    def isBufferHeating( self, isHeatingDemand, currentBufferChargeLevel, minBufferChargeLevel, maxBufferChargeLevel ):
        # Currently no buffer heating
        if not isHeatingDemand:
            # No heating needed if buffer is changed more than minBufferChargeLevel
            if currentBufferChargeLevel > minBufferChargeLevel:
                return False
        # Stop buffer heating if buffer more than 70% charged
        elif currentBufferChargeLevel > maxBufferChargeLevel:
            return False

        return maxBufferChargeLevel > 0

    def calculateForcedBufferHeatingTime(self, now, lastUpdate, slotHeatingPower, availableHeatingPowerPerMinute):
      
        # when was the last heating job
        lastUpdateBeforeInMinutes = int( round( ( now.getMillis() - lastUpdate.getMillis() ) / 1000.0 / 60.0 ) )

        if lastUpdateBeforeInMinutes < 360:
            return 0, lastUpdateBeforeInMinutes
          
        # how long do we need to heat up 0.1°
        neededMinutesPerSlot = int( round( slotHeatingPower / availableHeatingPowerPerMinute ) )
        
        # 6 hours => 1
        # 12 hours => 2
        # 18 hours => 3
        # -------------
        # multiplied, depending how long ago the last heating job was running
        # 360 (0) => 1 (0)
        # 1080 (720) => 3 (2)
        factor = ( (lastUpdateBeforeInMinutes - 360.0) * 2.0 / 720.0 ) + 1.0
        
        # how long should the next heating job running
        minutes = int( round( neededMinutesPerSlot * ( factor if factor < 3.0 else 3.0 ) ) )

        return minutes, lastUpdateBeforeInMinutes

    def forcedBufferHeatingCheck( self, now, isHeatingDemand, referenceTargetDiff, slotHeatingPower, availableHeatingPowerPerMinute, currentCoolingPowerPerMinute ):
        if isHeatingDemand:
            if self.forcedBufferReferenceTemperature != None:
                # Room is warming up, so we have to stop previously forced checks
                if self.forcedBufferReferenceTemperature < getItemState("Heating_Reference").doubleValue():
                    self.log.info(u"        : Stop forced buffer • room is warming up" )
                    self.forcedBufferReferenceTemperature = None
                else:
                    # should never happen, ecept we reload the rule
                    maxRuntime = self.forcedBufferTime if self.forcedBufferTime > 0 else MIN_HEATING_TIME
                    
                    # Too much forced heating > 90 minutes
                    if itemLastUpdateOlderThen("Heating_Demand",now.minusMinutes( maxRuntime )):
                        self.log.info(u"        : Stop forced buffer • runtime limit exceeded" )
                        self.forcedBufferReferenceTemperature = None
                    else:
                        self.log.info(u"        : Continue forced heating • max {} min".format(maxRuntime) )
            else:
                # Keep everything like it is. This leaves the forcedBufferCheckActive untouched
                self.log.info(u"        : No forced buffer • is heating already" )
        else:
            # Not cold enough
            if currentCoolingPowerPerMinute < 20.0:
                self.log.info(u"        : No forced buffer • not cold enough • max -{} W/min".format(20.0) )
                self.forcedBufferReferenceTemperature = None
            else:
                lastHeating = getItemLastUpdate("Heating_Demand")
                heatingMinutes, lastUpdateBeforeInMinutes = self.calculateForcedBufferHeatingTime( now, lastHeating, slotHeatingPower, availableHeatingPowerPerMinute)
                
                if heatingMinutes > 0:              
                    # Is not the right time. Only in the morning
                    if not self.nightModeActive or now.getHourOfDay() > 12:
                        self.log.info(u"        : No forced buffer • not the right time to heat {} min.".format(heatingMinutes) )
                        self.forcedBufferReferenceTemperature = None
                    else:
                        # how much lazy time should we apply, depends on the amount of heated up energy
                        lazyMinutes = self.getLazyTimeOffset(heatingMinutes)
                        
                        #self.log.info(u"{} {}".format(heatingMinutes,lazyMinutes))

                        # Is still in the night
                        if self.isNightModeTime(now.plusMinutes( heatingMinutes + lazyMinutes )):
                            self.log.info(u"        : No forced buffer • morning check at {} • {} min. • {} min. lazy".format( OFFSET_FORMATTER.print(now.plusMinutes(heatingMinutes)), heatingMinutes + lazyMinutes, lazyMinutes ) )
                            self.forcedBufferReferenceTemperature = None
                        # heating was active in the past 20 hours
                        else:
                            self.log.info(u"        : Force buffer to prevent cold floors until {} • {} min.".format(OFFSET_FORMATTER.print(now.plusMinutes(heatingMinutes)),heatingMinutes) )
                            self.forcedBufferReferenceTemperature = getItemState("Heating_Reference").doubleValue()
                            self.forcedBufferTime = heatingMinutes
                else:
                    self.log.info(u"        : No forced buffer • was running at {} • {} min.".format(OFFSET_FORMATTER.print(lastHeating),lastUpdateBeforeInMinutes) )
                    self.forcedBufferReferenceTemperature = None

        return self.forcedBufferReferenceTemperature != None

    def controlHeating( self, now, heatingDemand, heatingTarget, currentOutdoorTemp ):

        # 0 - Abschalten
        # 1 - Nur WW
        # 2 - Heizen mit WW
        # 3 - Reduziert
        # 4 - Normal
        
        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        
        isHeatingRequested = heatingDemand == 1
        if self.activeHeatingOperatingMode == -1:
            self.activeHeatingOperatingMode = currentOperatingMode
        
        forceRetry = self.activeHeatingOperatingMode != currentOperatingMode
        forceRetryMsg = u" • RETRY" if forceRetry else u""
        
        self.log.info(u"Active  : {}".format(Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) )) )
        
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
                    if timeInterval > 60:
                        timeInterval = 60
                
                # Dauernd reduziert läuft seit mindestens XX Minuten
                if forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(timeInterval) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"Switch  : Reduziert => Heizen mit WW • after {} min.{}".format(timeInterval,forceRetryMsg))
