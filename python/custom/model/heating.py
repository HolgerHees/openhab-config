# -*- coding: utf-8 -*-

from custom.helper import getNow, getItemState, getItemLastUpdate, itemLastUpdateOlderThen, getStableItemState
from custom.model.sun import SunRadiation

from org.eclipse.smarthome.core.library.types import OnOffType
from org.eclipse.smarthome.core.library.types import OpenClosedType
from org.eclipse.smarthome.core.library.types import PercentType
from org.eclipse.smarthome.core.library.types import DecimalType

from custom.model.house import Window
from custom.model.state import RoomState, HouseState, RoomHeatingState, HouseHeatingState

class Heating(object):
    defaultNightReduction = 2.0
    lazyOffset = 90 # Offset time until any heating has an effect
    minHeatingTime = 15 # 'Heizen mit WW' should be active at least for 15 min.
    #MIN_ONLY_WW_TIME = 15 # 'Nur WW' should be active at least for 15 min.
    #MIN_REDUCED_TIME = 5
    #MAX_REDUCED_TIME = 60

    densitiyAir = 1.2041
    cAir = 1.005

    # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
    leaking_n50 = 1.0
    leaking_e = 0.07
    leaking_f = 15.0
    
    # To warmup 1 liter of wather you need 4,182 Kilojoule
    # 1 Wh == 3,6 kJ
    # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
    heatingReferencePower = 1162 # per Watt je m³/K

    cloudCoverFC8Item = None
    cloudCoverFC4Item = None
    cloudCoverItem = None
    
    temperatureGardenFC8Item = None
    temperatureGardenFC4Item = None
    temperatureGardenItem = None
    temperatureGarageItem = None
    temperatureAtticItem = None
    
    ventilationFilterRuntimeItem = None
    ventilationLevelItem = None
    ventilationOutgoingTemperatureItem = None
    ventilationIncommingTemperatureItem = None
    
    heatingCircuitPumpSpeedItem = None
    heatingTemperaturePipeOutItem = None
    heatingTemperaturePipeInItem = None
    
    holidayStatusItem = None
    
    maxHeatingVolume = None
    
    radiatedThermalStorageType = None
    
    rooms = []
            
    totalVolume = 0
    
    
    _stableTemperatureReferences = {}

    # static status variables
    _forcedHeatings = {}
    
    @staticmethod
    def init():
        Heating.totalVolume = reduce( lambda x,y: x+y, map( lambda x: x.getVolume(), Heating.rooms ) )
    
    def __init__(self,log):
        self.log = log
        self.cache = {}
        self.now = getNow()

        #Heating_Auto_Mode
        #=>Heating_Charged
        #=>Heating_Demand
        #Heating_Operating_Mode
        #=>Heating_Temperature_Livingroom_Target
        #=>Heating_Temperature_Bedroom_Target
        
    def getCachedStableItemKey(self,itemName,stableSince=10):
        return u"stable-{}-{}".format(itemName,stableSince)
    
    def getCachedStableItemFloat(self,itemName,stableSince=10):
        return self.getCachedStableItemState(itemName,stableSince).floatValue()

    def getCachedStableItemState(self,itemName,stableSince=10):
        key = self.getCachedStableItemKey(itemName,stableSince)
        if key not in self.cache:
            self.cache[key] = DecimalType(getStableItemState(self.now,itemName, stableSince))
        return self.cache[key]

    def getCachedItemFloat(self,itemName):
        return self.getCachedItemState(itemName).floatValue()

    def getCachedItemState(self,itemName):
        if itemName not in self.cache:
            self.cache[itemName] = getItemState(itemName)
        return self.cache[itemName]
      
    def cachedItemLastUpdateOlderThen(self,itemName,minutes):
        key = u"update-{}-{}".format(itemName,minutes)
        if key not in self.cache:
            self.cache[key] = itemLastUpdateOlderThen( itemName, self.now.minusMinutes(minutes) )
        return self.cache[key]

    def getVentilationPower(self,tempDiffOffset):
        # *** Calculate power loss by ventilation ***
        _ventilationLevel = self.getCachedItemState(self.ventilationLevelItem).intValue()
        _ventilationTempDiff = self.getCachedItemFloat(self.ventilationOutgoingTemperatureItem) - self.getCachedItemFloat(self.ventilationIncommingTemperatureItem)
        
        # apply outdoor temperature changes to ventilation in / out difference
        if tempDiffOffset != 0:
            ventilationOffset = tempDiffOffset / 4
            if _ventilationTempDiff + ventilationOffset > 0:
                _ventilationTempDiff = _ventilationTempDiff + ventilationOffset
                    
        # Ventilation Power
        # 15% => 40m/h		XX => ?
        # 100% => 350m/h		85 => 310
        _ventilationVolume = ( ( ( _ventilationLevel - 15.0 ) * 310.0 ) / 85.0 ) + 40.0
        _ventilationUValue = _ventilationVolume * self.densitiyAir * self.cAir
        _ventilationPowerInKJ = _ventilationUValue * _ventilationTempDiff
        return _ventilationPowerInKJ * -1 if _ventilationPowerInKJ != 0 else 0.0
    
    def getLeakingPower(self,volume, currentTemperature, outdoorTemperature):
        _leakingTemperatureDiff = currentTemperature - outdoorTemperature
        _leakingVolume = ( volume * self.leaking_n50 * self.leaking_e ) / ( 1 + ( self.leaking_f / self.leaking_e ) * ( ( ( 0.1 * 0.4 ) / self.leaking_n50 ) * ( ( 0.1 * 0.4 ) / self.leaking_n50 ) ) )
        _leakingUValue = _leakingVolume * self.densitiyAir * self.cAir
        _leakingPowerInKJ = _leakingUValue * _leakingTemperatureDiff
        return _leakingPowerInKJ * -1 if _leakingPowerInKJ != 0 else 0.0

    def getCoolingPower(self ,area, currentTemperature, type):
        if type.getUValue() != None:
            referenceTemperature = self.getCachedStableItemFloat(type.getReferenceTemperatureItem())
            temperatureDifference = currentTemperature - referenceTemperature
            coolingPerKelvin =( type.getUValue() + type.getUOffset() ) * area * type.getFactor()
            coolingTotal = coolingPerKelvin * temperatureDifference
            return coolingTotal * -1 if coolingTotal != 0 else 0.0
        else:
            return 0.0
        
    def calculateWallCoolingAndRadiations(self,currentTemperature,sunSouthRadiation,sunWestRadiation,walls):
        wallCooling = wallRadiation = roomCapacity = 0
        for wall in walls:
            cooling = self.getCoolingPower(wall.getArea(),currentTemperature,wall.getType())
            wallCooling = wallCooling + cooling
            
            if wall.getType() == self.radiatedThermalStorageType:
                if wall.getDirection() == 'south':
                    wallRadiation = wallRadiation + SunRadiation.getWallSunPowerPerMinute(wall.getArea(),sunSouthRadiation)
                elif wall.getDirection() == 'west':
                    wallRadiation = wallRadiation + SunRadiation.getWallSunPowerPerMinute(wall.getArea(),sunWestRadiation)

            capacity = ( wall.getArea() * wall.getType().getCapacity() ) / 3.6 # converting kj into watt
            roomCapacity = roomCapacity + capacity

        return wallCooling, wallRadiation, roomCapacity
        
    def calculateWindowCoolingAndRadiations(self,currentTemperature,sunSouthRadiation,sunWestRadiation,transitions,wallCooling,isForecast):
        closedWindowCooling = windowRadiation = openWindowCount = 0
        for transition in transitions:
            cooling = self.getCoolingPower(transition.getArea(),currentTemperature,transition.getType())
            closedWindowCooling = closedWindowCooling + cooling

            if transition.getContactItem() != None and self.getCachedItemState(transition.getContactItem()) == OpenClosedType.OPEN:
                if self.cachedItemLastUpdateOlderThen(transition.getContactItem(), 10 if isForecast else 2):
                    openWindowCount = openWindowCount + 1

            if isinstance(transition,Window) and transition.getGlasArea() != None:
                _shutterOpen = (isForecast or transition.getShutterItem() == None or self.getCachedItemState(transition.getShutterItem()) == PercentType.ZERO)
                if _shutterOpen:
                    if transition.getDirection() == 'south':
                        windowRadiation = windowRadiation + SunRadiation.getWindowSunPowerPerMinute(transition.getGlasArea(),sunSouthRadiation)
                    elif transition.getDirection() == 'west':
                        windowRadiation = windowRadiation + SunRadiation.getWindowSunPowerPerMinute(transition.getGlasArea(),sunWestRadiation)
        
        openWindowCooling = 0 if isForecast else wallCooling * openWindowCount
            
        return closedWindowCooling, openWindowCooling, windowRadiation, openWindowCount
          
    def calculateHeatingEnergy( self, isForecast, lastHeatingChange ):
        pumpSpeed = self.getCachedItemState(self.heatingCircuitPumpSpeedItem).intValue()
        if pumpSpeed == 0 or isForecast: 
            temperatures = []
            for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
                if isForecast or self.getCachedItemState( room.getHeatingCircuitItem() ) == OnOffType.ON:
                    temperatures.append( self.getCachedStableItemFloat( room.getTemperatureSensorItem() ) )
            
            if len(temperatures) == 0:
                # Fallback is avg of all target temperatures
                for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
                    temperatures.append( self.getCachedItemFloat( room.getTemperatureTargetItem() ) )
                
            temperature_Pipe_In = reduce( lambda x,y: x+y, temperatures ) / len(temperatures)
            
            if lastHeatingChange.getMillis() < self.now.minusHours(12).getMillis():
                # 0.3 steilheit
                # niveau 12k
                # 20° => 36°                => 0 => 0°
                # -20^ => 47°               => 40 => 11°
                
                currentOutdoorTemp = self.getCachedItemFloat( self.temperatureGardenItem )
                
                if currentOutdoorTemp > 20.0: 
                    maxVL = 36.0 * 0.95
                elif currentOutdoorTemp < -20.0:
                    maxVL = 47.0 * 0.95 
                else:
                    maxVL = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.95
                    #test = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.9
                    #self.log.info(u"-----> {}".format(test))
                    #test = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.95
                    #self.log.info(u"-----> {}".format(test))
            else:
                maxVL = temperature_Pipe_In + 11.5
                    
            circulationDiff = maxVL - temperature_Pipe_In
                
            pumpSpeed = 100.0
            debugInfo = ""
            isForecast = True
        else:
            temperature_Pipe_Out = self.getCachedItemFloat(self.heatingTemperaturePipeOutItem)
            temperature_Pipe_In = self.getCachedItemFloat(self.heatingTemperaturePipeInItem)
            circulationDiff = temperature_Pipe_Out - temperature_Pipe_In
            
            debugInfo = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulationDiff,1),round(temperature_Pipe_Out,1),round(temperature_Pipe_In,1),pumpSpeed)

        return circulationDiff, pumpSpeed, isForecast, debugInfo

    def calculateHeatingRadiation( self, activeHeatingVolume, activeHeatingArea, roomHeatingArea, circulationDiff, pumpSpeed ):

        if roomHeatingArea != None:
            roomHeatingVolume = roomHeatingArea * activeHeatingVolume / activeHeatingArea
        
            pumpVolume = round( ( roomHeatingVolume * pumpSpeed ) / 100.0, 2 )
            heatingPower = self.heatingReferencePower * pumpVolume * circulationDiff
            
            return pumpVolume, heatingPower
        else:
            return 0.0, 0.0
          
    def calculateActiveHeatingArea(self,isForecast):
        maxHeatingArea = 0
        activeHeatingArea = 0
        
        for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
            if isForecast or self.getCachedItemState( room.getHeatingCircuitItem() ) == OnOffType.ON:
                activeHeatingArea = activeHeatingArea + room.getHeatingArea()

            maxHeatingArea = maxHeatingArea + room.getHeatingArea()
                
        # if all circuits are active => then 100% of self.maxHeatingVolume are possible
        # if 1% of the circuits area is active then 60.4% of self.maxHeatingVolume at 100%
        # if 10% of the circuits area is active then 64.0% of self.maxHeatingVolume at 100%
        # if 50% of the circuits area is active then 80.0% of self.maxHeatingVolume at 100%
        activeHeatingVolumeInPercent = ( activeHeatingArea * 40.0 / maxHeatingArea ) + 60.0
        activeHeatingVolume = activeHeatingVolumeInPercent * self.maxHeatingVolume / 100.0
        
        return activeHeatingArea, activeHeatingVolume, maxHeatingArea, self.maxHeatingVolume
    
    def getOutdoorDependingReduction( self, coolingPower ):
        # more than zeor means cooling => no reduction
        if coolingPower <= 0: return 0.0

        # less than zero means - sun heating
        # 18000 Watt => 300 W/min => max reduction
        if coolingPower > 18000: return 2.0

        return ( coolingPower * 2.0 ) / 18000.0

    def calculateOutdoorReduction(self, coolingPower, coolingPowerFC4, coolingPowerFC8):
        # Current cooling should count full
        _outdoorReduction = self.getOutdoorDependingReduction(coolingPower)
        # Closed cooling forecast should count 90%
        _outdoorReductionFC4 = self.getOutdoorDependingReduction(coolingPowerFC4) * 0.8
        # Cooling forecast in 8 hours should count 80%
        _outdoorReductionFC8 = self.getOutdoorDependingReduction(coolingPowerFC8) * 0.6
        
        _outdoorReduction = _outdoorReduction + _outdoorReductionFC4 + _outdoorReductionFC8
        
        if _outdoorReduction > 0.0: _outdoorReduction = _outdoorReduction + 0.1
        
        return round( _outdoorReduction, 1 )
      
    def isNightModeTime(self,reference):
        day    = reference.getDayOfWeek()
        hour   = reference.getHourOfDay()
        minute = reference.getMinuteOfHour()

        _nightModeActive = False
        
        _holidaysActive = self.getCachedItemState(self.holidayStatusItem) == OnOffType.ON
        
        _isMorning = True if hour < 12 else False
        
        # Wakeup
        if _isMorning:
            # Monday - Friday
            if not _holidaysActive and day <= 5:
                if hour < 5:
                #if hour < 5 or ( hour == 5 and minute <= 30 ):
                    _nightModeActive = True
            # Saturday and Sunday
            else:
                if hour < 8:
                #if hour < 8 or ( hour == 8 and minute <= 30 ):
                    _nightModeActive = True
        # Evening
        else:
            # Monday - Thursday and Sunday
            if not _holidaysActive and day <= 4 or day == 7:
                if hour >= 22:
                #if hour >= 23 or ( hour == 22 and minute >= 30 ):
                    _nightModeActive = True
            # Friday and Saturday
            else:
                if hour >= 24:
                    _nightModeActive = True

        return _nightModeActive
      
    def isNightMode(self,isHeatingActive):
        if self.now.getHourOfDay() > 19:
            offset = self.lazyOffset
            if not isHeatingActive: 
                offset = offset + self.minHeatingTime
            return self.isNightModeTime( self.now.plusMinutes( offset ) )
        
        if self.now.getHourOfDay() < 10:
            return self.isNightModeTime( self.now )
          
        return False
      
    def getCoolingAndRadiations(self,hours,lastHeatingChange):
        isForecast = hours != 0
        
        time = self.now
        tempDiffOffset = 0
        
        if hours == 4:
            time = time.plusMinutes(240)
            # fill cache with forecast values
            self.cache[self.cloudCoverItem] = self.getCachedItemState(self.cloudCoverFC4Item)
            self.cache[self.temperatureGardenItem] = self.getCachedItemState(self.temperatureGardenFC4Item)
            tempDiffOffset = self.cache[u"org_{}".format(self.temperatureGardenItem)].floatValue() - self.getCachedItemFloat(self.temperatureGardenFC4Item)
        elif hours == 8:
            time = time.plusMinutes(480)
            # fill cache with forecast values
            self.cache[self.cloudCoverItem] = self.getCachedItemState(self.cloudCoverFC8Item)
            self.cache[self.temperatureGardenItem] = self.getCachedItemState(self.temperatureGardenFC8Item)
            tempDiffOffset = self.cache[u"org_{}".format(self.temperatureGardenItem)].floatValue() - self.getCachedItemFloat(self.temperatureGardenFC8Item)
        else:
            # fill cache with real values
            self.cache[self.cloudCoverItem] = self.cache[u"org_{}".format(self.cloudCoverItem)]
            self.cache[self.temperatureGardenItem] = self.cache[u"org_{}".format(self.temperatureGardenItem)]

        self.cache[self.getCachedStableItemKey(self.temperatureGardenItem)] = self.cache[self.temperatureGardenItem]
            
        heatingCirculationDiff, heatingPumpSpeed, heatingForecast, heatingDebugInfo = self.calculateHeatingEnergy(isForecast,lastHeatingChange)
        activeHeatingArea, activeHeatingVolume, maxHeatingArea, maxHeatingVolume = self.calculateActiveHeatingArea(isForecast)
        
        currentTotalVentilationCooling = self.getVentilationPower(tempDiffOffset) / 3.6 # converting kj into watt
        sunSouthRadiation, sunWestRadiation, sunDebugInfo = SunRadiation.getSunPowerPerMinute(time,round(self.getCachedItemFloat(self.cloudCoverItem),1))
        
        totalWallCooling = 0
        totalWallRadiation = 0
        totalVentilationCooling = 0
        totalLeakCooling = 0
        totalWindowCooling = 0
        totalWindowRadiation = 0
        
        totalHeatingVolume = 0
        totalHeatingRadiation = 0
        totalPossibleHeatingVolume = 0
        totalPossibleHeatingRadiation = 0
        
        totalBufferCapacity = 0
        
        states = {}

        for room in self.rooms:            
            currentTemperature = self.getCachedStableItemFloat(room.getTemperatureSensorItem())
                          
            # *** WALL COOLING AND RADIATION ***
            wallCooling, wallRadiation, roomCapacity = self.calculateWallCoolingAndRadiations(currentTemperature,sunSouthRadiation,sunWestRadiation,room.getWalls())

            # *** WINDOW COOLING AND RADIATION ***
            closedWindowCooling, openWindowCooling, windowRadiation, openWindowCount = self.calculateWindowCoolingAndRadiations(currentTemperature,sunSouthRadiation,sunWestRadiation,room.getTransitions(),wallCooling,isForecast)
            wallCooling = wallCooling + closedWindowCooling
            
            if room.getHeatingCircuitItem() != None:
                # *** HEATING RADIATION ***
                if heatingForecast or self.getCachedItemState( room.getHeatingCircuitItem() ) != OnOffType.ON:
                    heatingVolume, heatingRadiation = 0.0, 0.0
                else:
                    heatingVolume, heatingRadiation = self.calculateHeatingRadiation(activeHeatingVolume, activeHeatingArea, room.getHeatingArea(), heatingCirculationDiff, heatingPumpSpeed)
                
                possibleHeatingVolume, possibleHeatingRadiation = self.calculateHeatingRadiation(maxHeatingVolume, maxHeatingArea, room.getHeatingArea(), heatingCirculationDiff, heatingPumpSpeed)
                
                #self.log.info(u"{} {} {} {} {}".format(maxHeatingVolume, maxHeatingArea, room.getHeatingArea(), heatingCirculationDiff, heatingPumpSpeed))
                #self.log.info(u"{} {}".format(room.getName(),possibleHeatingRadiation))
            else:
                heatingVolume, heatingRadiation = 0.0, 0.0
                possibleHeatingVolume, possibleHeatingRadiation = 0.0, 0.0

            # *** VENTILATION COOLING ***
            ventilationCooling = room.getVolume() * currentTotalVentilationCooling / self.totalVolume
            leakCooling = self.getLeakingPower(room.getVolume(),currentTemperature,self.getCachedItemFloat(self.temperatureGardenItem)) / 3.6 # converting kj into watt
                
            # summarize room values
            totalBufferCapacity = totalBufferCapacity + roomCapacity
            totalWallCooling = totalWallCooling + wallCooling
            totalWallRadiation = totalWallRadiation + wallRadiation
            totalVentilationCooling = totalVentilationCooling + ventilationCooling
            totalLeakCooling = totalLeakCooling + leakCooling
            totalWindowCooling = totalWindowCooling + openWindowCooling
            totalWindowRadiation = totalWindowRadiation + windowRadiation
            totalHeatingVolume = totalHeatingVolume + heatingVolume
            totalHeatingRadiation = totalHeatingRadiation + heatingRadiation
            totalPossibleHeatingVolume = totalPossibleHeatingVolume + possibleHeatingVolume
            totalPossibleHeatingRadiation = totalPossibleHeatingRadiation + possibleHeatingRadiation

            # set room values
            roomState = RoomState()
            roomState.setName(room.getName())
            #roomIsActive = True#room.getHeatingCircuitItem() != None and ( isForecast or self.getCachedItemState( room.getHeatingCircuitItem() ) == OnOffType.ON )
            #roomState.setActive(roomIsActive)
            roomState.setOpenWindowCount(openWindowCount)

            roomState.setBufferCapacity(roomCapacity)

            roomState.setWallCooling(wallCooling)
            roomState.setWallRadiation(wallRadiation)
            roomState.setVentilationCooling(ventilationCooling)
            roomState.setLeakCooling(leakCooling)
            roomState.setWindowCooling(openWindowCooling)
            roomState.setWindowRadiation(windowRadiation)

            roomState.setPassiveSaldo(wallCooling+wallRadiation+ventilationCooling+leakCooling+openWindowCooling+windowRadiation)

            roomState.setHeatingVolume(heatingVolume)
            roomState.setHeatingRadiation(heatingRadiation)
            roomState.setPossibleHeatingVolume(possibleHeatingVolume)
            roomState.setPossibleHeatingRadiation(possibleHeatingRadiation)

            states[room.getName()] = roomState

        # set house values
        houseState = HouseState()
        houseState.setRoomStates(states)
        houseState.setReferenceTemperature(self.getCachedItemFloat(self.temperatureGardenItem))

        houseState.setBufferCapacity(totalBufferCapacity)

        houseState.setWallCooling(totalWallCooling)
        houseState.setWallRadiation(totalWallRadiation)
        houseState.setVentilationCooling(totalVentilationCooling)
        houseState.setLeakCooling(totalLeakCooling)
        houseState.setWindowCooling(totalWindowCooling)
        houseState.setWindowRadiation(totalWindowRadiation)

        houseState.setPassiveSaldo(totalWallCooling+totalWallRadiation+totalVentilationCooling+totalLeakCooling+totalWindowCooling+totalWindowRadiation)

        houseState.setHeatingPumpSpeed(heatingPumpSpeed)
        houseState.setHeatingVolume(totalHeatingVolume)
        houseState.setHeatingRadiation(totalHeatingRadiation)
        houseState.setPossibleHeatingVolume(totalPossibleHeatingVolume)
        houseState.setPossibleHeatingRadiation(totalPossibleHeatingRadiation)
        
        houseState.setHeatingDebugInfo(heatingDebugInfo)
        houseState.setSunDebugInfo(sunDebugInfo)

        return houseState
        
    def getHeatingDemand(self,cr,cr4,cr8,outdoorReduction,nightReduction,isHeatingActive):
      
        states = {}
        for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
            
            hs = RoomHeatingState()
            
            for transition in room.transitions:
                if transition.getContactItem() != None and self.getCachedItemState(transition.getContactItem()) == OpenClosedType.OPEN:
                    if self.cachedItemLastUpdateOlderThen(transition.getContactItem(), 10):
                        hs.setHeatingDemandEnergy(-1)
                        break
                    
            states[room.getName()] = hs
        
        hhs = HouseHeatingState()
        hhs.setHeatingStates(states)

        bufferHeatingEnabled = cr.getPassiveSaldo() < 0 and cr4.getPassiveSaldo() < 0

        for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
            
            hs = hhs.getHeatingState(room.getName())

            if hs.getHeatingDemandEnergy() == -1:
                hs.setInfo("OPEN WINDOW")
                continue
            
            hs.setNightReduction(nightReduction)
            
            currentTemperature = round( self.getCachedStableItemFloat(room.getTemperatureSensorItem()), 1)
            targetTemperature = self.getCachedItemFloat(room.getTemperatureTargetItem()) - outdoorReduction - nightReduction
            
            charged = self.getCachedItemFloat(room.getHeatingBufferItem())
            
            # check for upcoming charge level changes => see "charge level changes" for the final one
            if room.getName() in Heating._stableTemperatureReferences:
                _lastTemp = Heating._stableTemperatureReferences[room.getName()]
                if currentTemperature > _lastTemp:
                    charged = self.adjustChargeLevel(cr.getRoomState(room.getName()),currentTemperature,_lastTemp,charged)
                    if charged < 0.0: charged = 0.0
                    self.log.info(u"\t        : {:10s} • Charging to {} adjusted".format(room.getName(),charged) )
                
            missingDegrees = targetTemperature - currentTemperature

            if missingDegrees < 0:
                hs.setInfo("WARM")
            else:
                rs = cr.getRoomState(room.getName())
                
                if missingDegrees > 0:
                    hs.setInfo("COLD")
                    
                    possibleDegrees = charged / rs.getBufferCapacity()
                    if possibleDegrees - missingDegrees > 0:
                        lazyReduction = missingDegrees
                        charged = charged - ( missingDegrees * rs.getBufferCapacity() )
                        missingDegrees = 0
                    else:
                        lazyReduction = possibleDegrees
                        neededEnergy = ( missingDegrees - possibleDegrees ) * rs.getBufferCapacity()
                        #self.log.info(u"{} {} {}".format(rs.getName(),neededEnergy,temperatureDifference))
                        neededTime = neededEnergy / rs.getPossibleHeatingRadiation()
                        hs.setHeatingDemandEnergy(neededEnergy)
                        hs.setHeatingDemandTime(neededTime)
                        
                    hs.setLazyReduction(lazyReduction)

                if missingDegrees == 0:
                    if bufferHeatingEnabled:
                        #self.log.info(u"{} {} {}".format(room.getName(),missingDegrees,bufferHeatingEnabled))

                        # 75% of 0.1°C
                        maxBuffer = rs.getBufferCapacity() * 0.1 * 0.75
                        
                        # Stop buffer heating if buffer more than 75% charged
                        if charged > maxBuffer:
                            hs.setInfo("LOADED")
                        # No heating needed if buffer is changed more than minBufferChargeLevel
                        elif not isHeatingActive and charged > 0:
                            hs.setInfo("UNLOAD")
                        # Currently no buffer heating
                        else:
                            hs.setInfo("CHARGE")
                            #self.log.info(u"3")
                            neededEnergy = maxBuffer - charged
                            neededTime = neededEnergy / rs.getPossibleHeatingRadiation()
                            hs.setHeatingDemandEnergy(neededEnergy)
                            hs.setHeatingDemandTime(neededTime)
                    else:
                        hs.setInfo("SKIP")

            hs.setChargedBuffer(charged)
            
        return hhs
                
    def adjustChargeLevel(self,rs,currentTemp,lastTemp,chargeLevel):
        heatedUpTempDiff = currentTemp - lastTemp
        chargeLevel = chargeLevel - ( rs.getBufferCapacity() * heatedUpTempDiff )
        return chargeLevel
        
    def calculateChargeLevel(self,room,cr):
        totalChargeLevel = self.getCachedItemFloat(room.getHeatingBufferItem())
        
        rs = cr.getRoomState(room.getName())

        _currentTemp = round(self.getCachedStableItemFloat(room.getTemperatureSensorItem(),20),1)
        if room.getName() in Heating._stableTemperatureReferences:
            _lastTemp = Heating._stableTemperatureReferences[room.getName()]
            if _currentTemp < _lastTemp:
                self.log.info(u"Cleanup : {:10s} • Reference to {} adjusted".format(room.getName(),_currentTemp) )
            elif _currentTemp > _lastTemp:
                totalChargeLevel = self.adjustChargeLevel(rs,_currentTemp,_lastTemp,totalChargeLevel)
                self.log.info(u"Cleanup : {:10s} • Reference to {} and Charged to {} adjusted".format(room.getName(),_currentTemp,totalChargeLevel) )
        Heating._stableTemperatureReferences[room.getName()]=_currentTemp
      
        totalChargeLevel = totalChargeLevel + rs.getPassiveSaldo() + rs.getHeatingRadiation()
        totalChargeLevel = round( totalChargeLevel, 1 )
        if totalChargeLevel < 0.0: totalChargeLevel = 0.0

        return totalChargeLevel
      



        
        
        
        
        
        
        
        
    def formatEnergy(self,energy,precision=1):
        return round(energy/60.0,precision)
    
    def logCoolingAndRadiations(self,prefix,cr):
        self.log.info(u"\t{}: {}".format(prefix,cr.getSunDebugInfo()))
        self.log.info(u"\t        : Wall {} (☀{}) W/min • Air {} W/min • Leak {} W/min • Window {} (☀{}) W/min".format(
            self.formatEnergy(cr.getWallCooling()),
            self.formatEnergy(cr.getWallRadiation()),
            self.formatEnergy(cr.getVentilationCooling()),
            self.formatEnergy(cr.getLeakCooling()),
            self.formatEnergy(cr.getWindowCooling()),
            self.formatEnergy(cr.getWindowRadiation())
        ))
        msg = u"{} W/min".format(self.formatEnergy(cr.getHeatingRadiation())) if cr.getHeatingRadiation() > 0 else u"{} W/min (FC)".format(self.formatEnergy(cr.getPossibleHeatingRadiation()))
        self.log.info(u"\t        : CD {} W/min ({}°C) • HU {}".format(self.formatEnergy(cr.getPassiveSaldo()),round(cr.getReferenceTemperature(),1), msg ))
                  
    def logHeatingState(self,room, cr, hhs, outdoorReduction, nightReduction ):
        target = self.getCachedItemFloat(room.getTemperatureTargetItem()) - outdoorReduction - nightReduction
        
        rs = cr.getRoomState(room.getName())
        rhs = hhs.getHeatingState(room.getName())
        
        reductionMsg = u""
        if outdoorReduction > 0:
            reductionMsg = u"{}, OR {}".format(reductionMsg,outdoorReduction)
        if nightReduction > 0:
            reductionMsg = u"{}, NR {}".format(reductionMsg,nightReduction)
                
        infoMsg = u""
        
        percent = int(round(rhs.getChargedBuffer() * 100 / rs.getBufferCapacity()))
        infoMsg = u"{} • {:6s} {:3d}%".format(infoMsg,rhs.getInfo(),percent)

        infoMsg = u"{} • CD {:4.1f} W/min".format(infoMsg, round(self.formatEnergy(rs.getPassiveSaldo()),1))

        infoMsg = u"{} • HU {:3.1f} W/min".format(infoMsg, round(self.formatEnergy(rs.getHeatingRadiation()),1))

        infoMsg = u"{} • LR {}°C".format(infoMsg, round(rhs.getLazyReduction(),1)) if rhs.getLazyReduction() > 0 else infoMsg
        
        if room.getName() in Heating._forcedHeatings:
            infoMsg = u"{} • FH {}".format(infoMsg, Heating._forcedHeatings[room.getName()])
            
        if rhs.getHeatingDemandEnergy() > 0:
            infoMsg = u"{} • HU {} W in {} min".format(
                infoMsg,
                round(rhs.getHeatingDemandEnergy(),1),
                round(rhs.getHeatingDemandTime()*60)
            )
            self.log.info(u"\t     ON : {:15s} • {}°C ({}{}){}".format(room.getName(),round(self.getCachedStableItemFloat(room.getTemperatureSensorItem()),1),target,reductionMsg,infoMsg))
        elif rhs.getHeatingDemandEnergy() == 0:
            self.log.info(u"\t    OFF : {:15s} • {}°C ({}{}){}".format(room.getName(),round(self.getCachedStableItemFloat(room.getTemperatureSensorItem()),1),target,reductionMsg,infoMsg))
        else:
            self.log.info(u"\tSKIPPED : {:15s} • {}°C ({}) • OPEN WINDOWS".format(room.getName(),round(self.getCachedStableItemFloat(room.getTemperatureSensorItem()),1),target))
                
    def calculate(self):
        # handle outdated ventilation values
        if itemLastUpdateOlderThen(self.ventilationFilterRuntimeItem, self.now.minusMinutes(120)):
            self.cache[self.ventilationLevelItem] = DecimalType(1)
            self.cache[self.ventilationOutgoingTemperatureItem] = DecimalType(0.0)
            self.cache[self.ventilationIncommingTemperatureItem] = DecimalType(0.0)

        # handle outdated forecast values
        if itemLastUpdateOlderThen(self.temperatureGardenFC4Item, self.now.minusMinutes(360) ):
            self.cache[self.temperatureGardenFC4Item] = getCachedItemState(self.temperatureGardenItem)
            self.cache[self.temperatureGardenFC8Item] = getCachedItemState(self.temperatureGardenItem)
            self.cache[self.cloudCoverFC4Item] = DecimalType(9)
            self.cache[self.cloudCoverFC8Item] = DecimalType(9)
            self.cache[self.cloudCoverItem] = DecimalType(9)

        lastHeatingChange = getItemLastUpdate("Heating_Demand")
        
        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        isHeatingActive = currentOperatingMode == 2

        self.cache[u"org_{}".format(self.cloudCoverItem)] = self.getCachedItemState(self.cloudCoverItem)
        self.cache[u"org_{}".format(self.temperatureGardenItem)] = self.getCachedStableItemState(self.temperatureGardenItem)

        # *** 8 HOUR FORECAST ***
        cr8 = self.getCoolingAndRadiations(8,lastHeatingChange)
        self.logCoolingAndRadiations("FC8     ",cr8)

        # *** 4 HOUR FORECAST ***
        cr4 = self.getCoolingAndRadiations(4,lastHeatingChange)
        self.logCoolingAndRadiations("FC4     ",cr4)

        # *** CURRENT ***
        cr = self.getCoolingAndRadiations(0,lastHeatingChange)
        self.logCoolingAndRadiations("Current ",cr)

        if cr.getHeatingVolume() > 0:
            self.log.info(u"\t        : {} ({} m³)".format(cr.getHeatingDebugInfo(),cr.getHeatingVolume()))

        #self.log.info(u"\tSlot    : {} KW/K • {} W/0.1K".format(round(cr.getBufferCapacity()/1000,1),round(cr.getBufferCapacity()/10,1)))
        



        # *** NIGHT MODE DETECTION ***
        nightModeActive = self.isNightMode(isHeatingActive)
        nightReduction = self.defaultNightReduction if nightModeActive else 0.0


        # *** OUTDOOR REDUCTION ***
        outdoorReduction = self.calculateOutdoorReduction(cr.getPassiveSaldo(),cr4.getPassiveSaldo(),cr8.getPassiveSaldo())



        
        # *** HEATING DEMAND CALCULATION ***
        hhs = self.getHeatingDemand(cr,cr4,cr8,outdoorReduction,nightReduction,isHeatingActive)

        # *** CHECK FOR PRE HEATING IN THE MORNING ***
        if nightModeActive and self.now.getHourOfDay() < 12:
            day_hhs = self.getHeatingDemand(cr,cr4,cr8,outdoorReduction,0,isHeatingActive)
            
            for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
                day_rhs = day_hhs.getHeatingState(room.getName())
                if not self.isNightModeTime( self.now.plusMinutes( int( round( day_rhs.getHeatingDemandTime() * 60, 0 ) ) ) ):
                    Heating._forcedHeatings[room.getName()] = "PRE"
                elif room.getName() not in Heating._forcedHeatings:
                    continue

                hhs.setHeatingState(room.getName(),day_rhs)
            
                




        # TODO add cold food heating in the morning and evening



        for room in filter( lambda room: room.getHeatingCircuitItem() != None,self.rooms):
          
            rhs = hhs.getHeatingState(room.getName())
            
            # clean forced heatings
            if rhs.getHeatingDemandEnergy() <= 0 and room.getName() in Heating._forcedHeatings:
                del Heating._forcedHeatings[room.getName()]

            # clean charge level
            totalChargeLevel = self.calculateChargeLevel(room,cr)
            rhs.setHeatingBuffer(totalChargeLevel)
            
            self.logHeatingState(room, cr, hhs, outdoorReduction, nightReduction )
            
            

     

        


        
        
        
        
        
        #Buffer  : 0% filled • 0 W ... 1222.7 W • 17 min. ⇧
        #Charged : 0.0 W total incl. buffer • 0 min. ⇩
        #        : Night mode start check at 13:38 • 90 min.
        #Effects : LR 0.0° ⇩ • OR 0.0°C ⇩ • NR 0.0°C ⇩ • LRC OFF
        #Rooms   : Living 22.3°C (⇒ 22.0°C) • Sleeping 20.4°C (⇒ 19.5°C)
        #        : No forced buffer • 3054.5 W in 43 min. • wrong time
        #Demand  : NO HEATING • TOO WARM • since 04:50 • 07:18 min. ago
        #Active  : Nur WW • since 04:50 • 07:18 min. ago
        
        return hhs


