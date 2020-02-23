# -*- coding: utf-8 -*-
import math

from custom.helper import getNow, getItemState, itemLastUpdateOlderThen, getStableItemState
from custom.model.sun import SunRadiation

from org.eclipse.smarthome.core.library.types import OnOffType
from org.eclipse.smarthome.core.library.types import OpenClosedType
from org.eclipse.smarthome.core.library.types import PercentType
from org.eclipse.smarthome.core.library.types import DecimalType

from custom.model.house import Window
from custom.model.state import RoomState, HouseState, RoomHeatingState, HouseHeatingState

class Heating(object):
    allowedRooms = {}
    
    defaultNightReduction = 2.0
    lazyOffset = 90 # Offset time until any heating has an effect
    minHeatingTime = 15 # 'Heizen mit WW' should be active at least for 15 min.
    minOnlyWwTime = 15 # 'Nur WW' should be active at least for 15 min.
    minReducedTime = 5
    maxReducedTime = 60

    densitiyAir = 1.2041
    cAir = 1.005

    # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
    leaking_n50 = 1.0
    leaking_e = 0.07
    leaking_f = 15.0
    
    # To warmup 1 liter of wather you need 4,182 Kilojoule
    # 1 Wh == 3,6 kJ
    # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
    heatingReferenceEnergy = 1162 # per Watt je m³/K

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

    def getVentilationEnergy(self,tempDiffOffset):
        # *** Calculate power loss by ventilation ***
        _ventilationLevel = self.getCachedItemState(self.ventilationLevelItem).intValue()
        _ventilationTempDiff = self.getCachedItemFloat(self.ventilationOutgoingTemperatureItem) - self.getCachedItemFloat(self.ventilationIncommingTemperatureItem)
        
        # apply outdoor temperature changes to ventilation in / out difference
        if tempDiffOffset != 0:
            ventilationOffset = tempDiffOffset / 4
            if _ventilationTempDiff + ventilationOffset > 0:
                _ventilationTempDiff = _ventilationTempDiff + ventilationOffset
                    
        # Ventilation Energy
        # 15% => 40m/h		XX => ?
        # 100% => 350m/h		85 => 310
        _ventilationVolume = ( ( ( _ventilationLevel - 15.0 ) * 310.0 ) / 85.0 ) + 40.0
        _ventilationUValue = _ventilationVolume * self.densitiyAir * self.cAir
        _ventilationEnergyInKJ = _ventilationUValue * _ventilationTempDiff
        return _ventilationEnergyInKJ * -1 if _ventilationEnergyInKJ != 0 else 0.0
    
    def getLeakingEnergy(self,volume, currentTemperature, outdoorTemperature):
        _leakingTemperatureDiff = currentTemperature - outdoorTemperature
        _leakingVolume = ( volume * self.leaking_n50 * self.leaking_e ) / ( 1 + ( self.leaking_f / self.leaking_e ) * ( ( ( 0.1 * 0.4 ) / self.leaking_n50 ) * ( ( 0.1 * 0.4 ) / self.leaking_n50 ) ) )
        _leakingUValue = _leakingVolume * self.densitiyAir * self.cAir
        _leakingEnergyInKJ = _leakingUValue * _leakingTemperatureDiff
        return _leakingEnergyInKJ * -1 if _leakingEnergyInKJ != 0 else 0.0

    def getCoolingEnergy(self ,area, currentTemperature, type):
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
            cooling = self.getCoolingEnergy(wall.getArea(),currentTemperature,wall.getType())
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
            cooling = self.getCoolingEnergy(transition.getArea(),currentTemperature,transition.getType())
            closedWindowCooling = closedWindowCooling + cooling

            if transition.getContactItem() != None and self.getCachedItemState(transition.getContactItem()) == OpenClosedType.OPEN:
                if self.cachedItemLastUpdateOlderThen(transition.getContactItem(), 10 if isForecast else 2):
                    openWindowCount = openWindowCount + 1

            if isinstance(transition,Window) and transition.getRadiationArea() != None:
                _shutterOpen = (isForecast or transition.getShutterItem() == None or self.getCachedItemState(transition.getShutterItem()) == PercentType.ZERO)
                if _shutterOpen:
                    if transition.getDirection() == 'south':
                        windowRadiation = windowRadiation + SunRadiation.getWindowSunPowerPerMinute(transition.getRadiationArea(),sunSouthRadiation)
                    elif transition.getDirection() == 'west':
                        windowRadiation = windowRadiation + SunRadiation.getWindowSunPowerPerMinute(transition.getRadiationArea(),sunWestRadiation)
        
        openWindowCooling = 0 if isForecast else wallCooling * openWindowCount
            
        return closedWindowCooling, openWindowCooling, windowRadiation, openWindowCount
          
    def calculateHeatingEnergy( self, isForecast ):
        pumpSpeed = self.getCachedItemState(self.heatingCircuitPumpSpeedItem).intValue()
        if pumpSpeed == 0 or isForecast: 
            temperatures = []
            for room in filter( lambda room: room.getHeatingArea() != None,self.rooms):
                if isForecast or room.getHeatingCircuitItem() == None or self.getCachedItemState( room.getHeatingCircuitItem() ) == OnOffType.ON:
                    temperatures.append( self.getCachedStableItemFloat( room.getTemperatureSensorItem() ) )
            
            if len(temperatures) == 0:
                # Fallback is avg of all target temperatures
                for room in filter( lambda room: room.getHeatingArea() != None and room.getTemperatureTargetItem() != None,self.rooms):
                    temperatures.append( self.getCachedItemFloat( room.getTemperatureTargetItem() ) )
                
            temperature_Pipe_In = reduce( lambda x,y: x+y, temperatures ) / len(temperatures) + 7.0
            
            # 0.3 steilheit
            # niveau 12k
            # 20° => 36°                => 0 => 0°
            # -20^ => 47°               => 40 => 11°
            
            currentOutdoorTemp = self.getCachedItemFloat( self.temperatureGardenItem )
            
            if currentOutdoorTemp > 20.0: 
                temperature_Pipe_Out = 36.0 * 0.95
            elif currentOutdoorTemp < -20.0:
                temperature_Pipe_Out = 47.0 * 0.95 
            else:
                temperature_Pipe_Out = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.95
                #test = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.9
                #self.log.info(u"-----> {}".format(test))
                #test = ( ( ( ( currentOutdoorTemp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.95
                #self.log.info(u"-----> {}".format(test))
                    
            circulationDiff = temperature_Pipe_Out - temperature_Pipe_In
                
            pumpSpeed = 85.0
            debugInfo = ""
            isForecast = True

            #Diff 9.1°C • VL 37.5°C • RL 28.4°C • 85.0% (FC)
            #self.log.info( u"Diff {}°C • VL {}°C • RL {}°C • {}% (FC)".format(round(circulationDiff,1),round(temperature_Pipe_Out,1),round(temperature_Pipe_In,1),pumpSpeed))
        else:
            temperature_Pipe_Out = self.getCachedItemFloat(self.heatingTemperaturePipeOutItem)
            temperature_Pipe_In = self.getCachedItemFloat(self.heatingTemperaturePipeInItem)
            circulationDiff = temperature_Pipe_Out - temperature_Pipe_In
            
            #Diff 9.6°C • VL 38.9°C • RL 29.3°C • 85% (0.42 m³)
            debugInfo = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulationDiff,1),round(temperature_Pipe_Out,1),round(temperature_Pipe_In,1),pumpSpeed)

        return circulationDiff, pumpSpeed, isForecast, debugInfo

    def calculateHeatingRadiation( self, activeHeatingVolume, activeHeatingArea, roomHeatingArea, circulationDiff, pumpSpeed ):

        if roomHeatingArea != None:
            roomHeatingVolume = roomHeatingArea * activeHeatingVolume / activeHeatingArea
        
            pumpVolume = round( ( roomHeatingVolume * pumpSpeed ) / 100.0, 2 )
            heatingEnergy = self.heatingReferenceEnergy * pumpVolume * circulationDiff
            
            return pumpVolume, heatingEnergy
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
    
    def getOutdoorDependingReduction( self, coolingEnergy ):
        # more than zeor means cooling => no reduction
        if coolingEnergy <= 0: return 0.0

        # less than zero means - sun heating
        # 18000 Watt => 300 W/min => max reduction
        if coolingEnergy > 18000: return 2.0

        return ( coolingEnergy * 2.0 ) / 18000.0

    def calculateOutdoorReduction(self, coolingEnergy, coolingEnergyFC4, coolingEnergyFC8):
        # Current cooling should count full
        _outdoorReduction = self.getOutdoorDependingReduction(coolingEnergy)
        # Closed cooling forecast should count 90%
        _outdoorReductionFC4 = self.getOutdoorDependingReduction(coolingEnergyFC4) * 0.8
        # Cooling forecast in 8 hours should count 80%
        _outdoorReductionFC8 = self.getOutdoorDependingReduction(coolingEnergyFC8) * 0.6
        
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
      
    def possibleColdFloorHeating(self,nightModeActive,lastHeatingChange):
        day = self.now.getDayOfWeek()
        hour = self.now.getHourOfDay()
        
        hadTodayHeating = lastHeatingChange.getDayOfWeek() == day

        isMorning = hour < 12 and nightModeActive
        hadMorningHeating = hadTodayHeating
        
        holidaysInactive = self.getCachedItemState(Heating.holidayStatusItem) == OnOffType.OFF
        minEveningHour = 17 if holidaysInactive and day <= 5 else 16
        isEvening = hour >= minEveningHour
        hadEveningHeating = hadTodayHeating and lastHeatingChange.getHourOfDay() >= minEveningHour
        
        return (isMorning and not hadMorningHeating) or (isEvening and not hadEveningHeating)
      
    def getColdFloorHeatingEnergy(self, lastUpdate, slotHeatingEnergy ):
      
        # when was the last heating job
        lastUpdateBeforeInMinutes = ( self.now.getMillis() - lastUpdate.getMillis() ) / 1000.0 / 60.0
       
        booster = 2.0 if self.now.getHourOfDay() < 12 else 1.5
        
        # 0 => 0
        # 8 => 1
        factor = ( lastUpdateBeforeInMinutes / 60.0 ) / 8.0
        if factor > 1.0: factor = 1.0

        #https://rechneronline.de/funktionsgraphen/
        multiplier = ( math.pow( (factor-1), 2.0 ) * -1 ) + 1      #(x-1)^2*-1+1
        #multiplier = math.pow( (factor-1), 3.0 ) + 1              #(x-1)^3+1

        targetBufferChargeLevel = round( slotHeatingEnergy * factor * booster, 1 )

        return round( targetBufferChargeLevel, 1 )

    def getCoolingAndRadiations(self,hours):
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
            
        heatingCirculationDiff, heatingPumpSpeed, heatingForecast, heatingDebugInfo = self.calculateHeatingEnergy(isForecast)
        activeHeatingArea, activeHeatingVolume, maxHeatingArea, maxHeatingVolume = self.calculateActiveHeatingArea(isForecast)
        
        currentTotalVentilationCooling = self.getVentilationEnergy(tempDiffOffset) / 3.6 # converting kj into watt
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
            leakCooling = self.getLeakingEnergy(room.getVolume(),currentTemperature,self.getCachedItemFloat(self.temperatureGardenItem)) / 3.6 # converting kj into watt
                
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
            roomState.setOpenWindowCount(openWindowCount)

            roomState.setBufferCapacity(roomCapacity)

            roomState.setWallCooling(wallCooling)
            roomState.setWallRadiation(wallRadiation)
            roomState.setVentilationCooling(ventilationCooling)
            roomState.setLeakCooling(leakCooling)
            roomState.setWindowCooling(openWindowCooling)
            roomState.setWindowRadiation(windowRadiation)

            roomState.setHeatingVolume(heatingVolume)
            roomState.setHeatingRadiation(heatingRadiation)
            roomState.setPossibleHeatingVolume(possibleHeatingVolume)
            roomState.setPossibleHeatingRadiation(possibleHeatingRadiation)
            
            roomState.setCurrentTemperature(currentTemperature)

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

        houseState.setHeatingPumpSpeed(heatingPumpSpeed)
        houseState.setHeatingVolume(totalHeatingVolume)
        houseState.setHeatingRadiation(totalHeatingRadiation)
        houseState.setPossibleHeatingVolume(totalPossibleHeatingVolume)
        houseState.setPossibleHeatingRadiation(totalPossibleHeatingRadiation)
        houseState.setHeatingDebugInfo(heatingDebugInfo)

        houseState.setSunSouthRadiation(sunSouthRadiation)
        houseState.setSunWestRadiation(sunWestRadiation)
        houseState.setSunDebugInfo(sunDebugInfo)

        return houseState
        
    def getHeatingDemand(self,room,cr,cr4,cr8,outdoorReduction,nightReduction,isHeatingActive):
      
        hs = RoomHeatingState()
        hs.setName(room.getName())

        for transition in room.transitions:
            if transition.getContactItem() != None and self.getCachedItemState(transition.getContactItem()) == OpenClosedType.OPEN:
                if self.cachedItemLastUpdateOlderThen(transition.getContactItem(), 10):
                    hs.setHeatingDemandEnergy(-1)
                    break
        
        bufferHeatingEnabled = cr.getPassiveSaldo() < 0 and cr4.getPassiveSaldo() < 0

        hs.setNightReduction(nightReduction)
        hs.setOutdoorReduction(outdoorReduction)
        
        rs = cr.getRoomState(room.getName())

        currentTemperature = round( self.getCachedStableItemFloat(room.getTemperatureSensorItem()), 1)

        # set active target temperature to room state
        targetTemperature = self.getCachedItemFloat(room.getTemperatureTargetItem()) -  nightReduction
        rs.setTargetTemperature(targetTemperature)

        charged = rs.getHeatingBuffer()
        
        # check for upcoming charge level changes => see "charge level changes" for the final one
        if room.getName() in Heating._stableTemperatureReferences:
            _lastTemp = Heating._stableTemperatureReferences[room.getName()]
            if currentTemperature > _lastTemp:
                charged = self.adjustChargeLevel(rs,currentTemperature,_lastTemp,charged)
                if charged < 0.0: charged = 0.0
                hs.setAdjustedHeatingBuffer(charged)
            
        if hs.getHeatingDemandEnergy() == -1:
            hs.setInfo("WINDOW")
        else:
            missingDegrees = targetTemperature - outdoorReduction - currentTemperature

            if missingDegrees < 0:
                hs.setInfo("WARM")
            else:                
                if missingDegrees > 0:
                    hs.setInfo("COLD")
                    
                    possibleDegrees = charged / rs.getBufferCapacity()
                    #self.log.info(u"{} {} {}".format(room.getName(),possibleDegrees,missingDegrees))
                    if possibleDegrees - missingDegrees > 0:
                        #self.log.info(u"A")
                        lazyReduction = missingDegrees
                        charged = charged - ( missingDegrees * rs.getBufferCapacity() )
                        missingDegrees = 0
                    else:
                        #self.log.info(u"B")
                        lazyReduction = possibleDegrees
                        charged = 0
                        neededEnergy = ( missingDegrees - possibleDegrees ) * rs.getBufferCapacity()
                        #self.log.info(u"{} {} {}".format(rs.getName(),neededEnergy,temperatureDifference))
                        neededTime = neededEnergy / rs.getActivePossibleSaldo()
                        hs.setHeatingDemandEnergy(neededEnergy)
                        hs.setHeatingDemandTime(neededTime)
                        
                    hs.setLazyReduction(lazyReduction)

                if missingDegrees == 0:
                    if bufferHeatingEnabled:
                        #self.log.info(u"{} {} {}".format(room.getName(),missingDegrees,bufferHeatingEnabled))

                        # 75% of 0.1°C
                        maxBuffer = rs.getBufferSlotCapacity() * 0.75
                        #self.log.info(u"{} {} {}".format(room.getName(),charged,maxBuffer))
                        
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
                            neededTime = neededEnergy / rs.getActivePossibleSaldo()
                            hs.setHeatingDemandEnergy(neededEnergy)
                            hs.setHeatingDemandTime(neededTime)
                    else:
                        hs.setInfo("SKIP")

        hs.setChargedBuffer(charged)
            
        return hs
                
    def adjustChargeLevel(self,rs,currentTemp,lastTemp,chargeLevel):
        heatedUpTempDiff = currentTemp - lastTemp
        chargeLevel = chargeLevel - ( rs.getBufferCapacity() * heatedUpTempDiff )
        return chargeLevel
        
    def calculateChargeLevel(self,room,rs,devider):
        totalChargeLevel = self.getCachedItemFloat(room.getHeatingBufferItem())
        
        _currentTemp = round(self.getCachedStableItemFloat(room.getTemperatureSensorItem(),20),1)
        if room.getName() in Heating._stableTemperatureReferences:
            _lastTemp = Heating._stableTemperatureReferences[room.getName()]
            if _currentTemp < _lastTemp:
                self.log.info(u"\tCleanup : {:10s} • Reference to {} adjusted".format(room.getName(),_currentTemp) )
            elif _currentTemp > _lastTemp:
                totalChargeLevel = self.adjustChargeLevel(rs,_currentTemp,_lastTemp,totalChargeLevel)
                if totalChargeLevel < 0.0: totalChargeLevel = 0.0
                self.log.info(u"\tCleanup : {:10s} • Reference to {} and Charged to {} adjusted".format(room.getName(),_currentTemp,round(totalChargeLevel,1)) )
        Heating._stableTemperatureReferences[room.getName()]=_currentTemp
      
        totalChargeLevel = totalChargeLevel + ( rs.getActiveSaldo() / 60.0 / devider )
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
                  
    def logHeatingState(self,room, cr, hhs ):
        
        rs = cr.getRoomState(room.getName())
        rhs = hhs.getHeatingState(room.getName()) if room.getTemperatureTargetItem() != None else None
                        
        infoMsg = u"{:15s} • {}°C".format(room.getName(),round(self.getCachedStableItemFloat(room.getTemperatureSensorItem()),1))
        
        if rhs != None:
            reductionMsg = u""
            if rhs.getHeatingDemandEnergy() >= 0:
                if rhs.getOutdoorReduction() > 0:
                    reductionMsg = u"{}, OR {}".format(reductionMsg,rhs.getOutdoorReduction())
                if rhs.getNightReduction() > 0:
                    reductionMsg = u"{}, NR {}".format(reductionMsg,rhs.getNightReduction())

            target = self.getCachedItemFloat(room.getTemperatureTargetItem()) - rhs.getOutdoorReduction() - rhs.getNightReduction()
            infoMsg = u"{} ({}{})".format(infoMsg,target,reductionMsg)

            infoValue = rhs.getInfo()
            if rhs.getForcedInfo() != None:
                infoValue = u"{} ({})".format(infoValue, rhs.getForcedInfo())
            infoMsg = u"{} • {:6s}".format(infoMsg,infoValue)

        infoMsg = u"{} • CD {:4.1f}".format(infoMsg, round(self.formatEnergy(rs.getPassiveSaldo()),1))

        # **** DEBUG ****
        #infoMsg = u"{} • DEBUG {} {}".format(infoMsg, rs.getPossibleHeatingRadiation(), rs.getPossibleHeatingVolume())

        if rhs != None:
            if rs.getHeatingRadiation() >= 0:
                infoMsg = u"{}, HU {:3.1f} W/min".format(infoMsg, round(self.formatEnergy(rs.getHeatingRadiation()),1))
                
            adjustedBuffer = u""
            if rhs.getChargedBuffer() != rs.getHeatingBuffer() or rhs.getAdjustedHeatingBuffer() > 0:
                if rhs.getChargedBuffer() != rs.getHeatingBuffer():
                    adjustedBuffer = u"{}{}".format(adjustedBuffer,round(rs.getHeatingBuffer(),1),adjustedBuffer)
                if rhs.getAdjustedHeatingBuffer() > 0:
                    adjustedBuffer = u"{} => {}".format(adjustedBuffer,round(rhs.getAdjustedHeatingBuffer(),1))
                adjustedBuffer = u" ({})".format(adjustedBuffer)
            
            percent = int(round(rhs.getChargedBuffer() * 100 / rs.getBufferSlotCapacity() ))
            infoMsg = u"{} • BF {}%, {}{} W".format(infoMsg, percent, round(rhs.getChargedBuffer(),1), adjustedBuffer)

            lr = round(rhs.getLazyReduction(),1)
            infoMsg = u"{} • LR {}°C".format(infoMsg, lr) if lr > 0 else infoMsg
      
            if rhs.getHeatingDemandEnergy() > 0:
                infoMsg = u"{} • HU {} W in {} min".format(
                    infoMsg,
                    round(rhs.getHeatingDemandEnergy(),1),
                    round(rhs.getHeatingDemandTime()*60)
                )
                self.log.info(u"\t     ON : {}".format(infoMsg))
            elif rhs.getHeatingDemandEnergy() == 0:
                self.log.info(u"\t    OFF : {}".format(infoMsg))
            else:
                self.log.info(u"\tSKIPPED : {}".format(infoMsg))
        else:
            self.log.info(u"\t        : {}".format(infoMsg))

                
    def calculate(self,isHeatingActive,lastHeatingChange,devider):
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

        self.cache[u"org_{}".format(self.cloudCoverItem)] = self.getCachedItemState(self.cloudCoverItem)
        self.cache[u"org_{}".format(self.temperatureGardenItem)] = self.getCachedStableItemState(self.temperatureGardenItem)

        # *** 8 HOUR FORECAST ***
        cr8 = self.getCoolingAndRadiations(8)
        self.logCoolingAndRadiations("FC8     ",cr8)

        # *** 4 HOUR FORECAST ***
        cr4 = self.getCoolingAndRadiations(4)
        self.logCoolingAndRadiations("FC4     ",cr4)

        # *** CURRENT ***
        cr = self.getCoolingAndRadiations(0)
        self.logCoolingAndRadiations("Current ",cr)

        if cr.getHeatingVolume() > 0:
            self.log.info(u"\t        : {} ({} m³)".format(cr.getHeatingDebugInfo(),cr.getHeatingVolume()))

        # CLEAN CHARGE LEVEL
        for room in filter( lambda room: room.getTemperatureTargetItem() != None,self.rooms):
            rs = cr.getRoomState(room.getName())
            totalChargeLevel = self.calculateChargeLevel(room,rs,devider)
            rs.setHeatingBuffer(totalChargeLevel)

            rs = cr4.getRoomState(room.getName())
            rs.setHeatingBuffer(totalChargeLevel)

            rs = cr8.getRoomState(room.getName())
            rs.setHeatingBuffer(totalChargeLevel)

        # *** NIGHT MODE DETECTION ***
        nightModeActive = self.isNightMode(isHeatingActive)
        nightReduction = self.defaultNightReduction if nightModeActive else 0.0
        # *** OUTDOOR REDUCTION ***
        outdoorReduction = self.calculateOutdoorReduction(cr.getPassiveSaldo(),cr4.getPassiveSaldo(),cr8.getPassiveSaldo())
            
        # *** HEATING STATE ***
        heatingNeeded = False
        
        hhs = HouseHeatingState()
        coldFloorHeatingPossible = not isHeatingActive and self.possibleColdFloorHeating(nightModeActive,lastHeatingChange)
        for room in filter( lambda room: room.getTemperatureTargetItem() != None,self.rooms):
            rs = cr.getRoomState(room.getName())

            # *** CLEAN OR RESTORE FORCED HEATING ***
            if room.getName() in Heating._forcedHeatings:
                rhs = Heating._forcedHeatings[room.getName()][0]
                neededEnergy = Heating._forcedHeatings[room.getName()][1] - rs.getHeatingBuffer()
                if neededEnergy < 0:
                    del Heating._forcedHeatings[room.getName()]
                else:
                    rs = cr.getRoomState(room.getName())
                    neededTime = neededEnergy / rs.getActivePossibleSaldo()
                    rhs.setHeatingDemandEnergy(neededEnergy)
                    rhs.setHeatingDemandTime(neededTime)
                    hhs.setHeatingState(room.getName(),rhs)
                    continue
  
            # *** HEATING DEMAND CALCULATION ***
            rhs = self.getHeatingDemand(room,cr,cr4,cr8,outdoorReduction,nightReduction,isHeatingActive)
         
            # *** CHECK FOR PRE HEATING IN THE MORNING ***
            if nightModeActive and self.now.getHourOfDay() < 12 and rhs.getHeatingDemandEnergy() == 0:
                day_rhs = self.getHeatingDemand(room,cr,cr4,cr8,outdoorReduction,0,isHeatingActive)
                if not self.isNightModeTime( self.now.plusMinutes( int( round( day_rhs.getHeatingDemandTime() * 60, 0 ) ) ) ):
                    rhs = day_rhs
                    rhs.setForcedInfo('PRE')
            
            # *** CHECK FOR COLD FLOOR HEATING ***
            if coldFloorHeatingPossible and rhs.getHeatingDemandEnergy() == 0:
                neededEnergy = self.getColdFloorHeatingEnergy(lastHeatingChange, rs.getBufferSlotCapacity())
                neededTime = neededEnergy / rs.getActivePossibleSaldo()
                if rhs.getHeatingDemandEnergy() < neededEnergy:
                    rhs.setHeatingDemandEnergy(neededEnergy)
                    rhs.setHeatingDemandTime(neededTime)
                    rhs.setForcedInfo('CF')

            if room.getName() in Heating.allowedRooms and rhs.getHeatingDemandTime() * 60 > Heating.minHeatingTime:
                heatingNeeded = True

            hhs.setHeatingState(room.getName(),rhs)
            
        hhs.setHeatingNeeded(heatingNeeded)

        # *** REGISTER FORCED HEATINGS IF HEATING IS POSSIBLE
        if heatingNeeded:
            for room in filter( lambda room: room.getTemperatureTargetItem() != None,self.rooms):
                rhs = hhs.getHeatingState(room.getName())
                if rhs.getForcedInfo() != None and room.getName() not in Heating._forcedHeatings:
                    Heating._forcedHeatings[room.getName()] = [ rhs, rhs.getHeatingDemandEnergy() ]

        # *** LOGGING ***
        for room in self.rooms:
            self.logHeatingState(room, cr, hhs )
            
        #        : No forced buffer • 3054.5 W in 43 min. • wrong time

        return cr, hhs
