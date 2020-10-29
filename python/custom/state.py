# -*- coding: utf-8 -*-

class State(object):
    def setBufferCapacity(self,value):
        self.bufferCapacity = value

    def getBufferCapacity(self):
        return self.bufferCapacity

    def getBufferSlotCapacity(self):
        return self.bufferCapacity * 0.1

    def setOutdoorWallEnergy(self,value):
        self.outdoorWallEnergy = value
        
    def getOutdoorWallEnergy(self):
        return self.outdoorWallEnergy
        
    def setIndoorWallEnergy(self,value):
        self.indoorWallEnergy = value
        
    def getIndoorWallEnergy(self):
        return self.indoorWallEnergy

    def getWallEnergy(self):
        return self.outdoorWallEnergy + self.indoorWallEnergy

    def setOutdoorWallRadiation(self,value):
        self.wallRadiation = value
        
    def getOutdoorWallRadiation(self):
        return self.wallRadiation

    def getWallRadiation(self):
        return self.wallRadiation

    def setVentilationEnergy(self,value):
        self.ventilationEnergy = value
        
    def getVentilationEnergy(self):
        return self.ventilationEnergy

    def setLeakEnergy(self,value):
        self.leakEnergy = value
        
    def getLeakEnergy(self):
        return self.leakEnergy

    def setWindowEnergy(self,value):
        self.windowEnergy = value
        
    def getWindowEnergy(self):
        return self.windowEnergy

    def setWindowRadiation(self,value):
        self.windowRadiation = value

    def getWindowRadiation(self):
        return self.windowRadiation

    def setOpenWindowCount(self,count):
        self.openWindowCount = count

    def getOpenWindowCount(self):
        return self.openWindowCount

    def getPassiveSaldo(self):
        return self.outdoorWallEnergy+self.indoorWallEnergy+self.wallRadiation+self.ventilationEnergy+self.leakEnergy+self.windowEnergy+self.windowRadiation
      
    def getActiveSaldo(self):
        return self.getPassiveSaldo() + self.getHeatingRadiation()
      
    def getActivePossibleSaldo(self):
        return self.getPassiveSaldo() + self.getPossibleHeatingRadiation()

    def setHeatingRadiation(self,value):
        self.heatingRadiation = value

    def getHeatingRadiation(self):
        return self.heatingRadiation

    def setHeatingVolume(self,value):
        self.heatingVolume = value

    def getHeatingVolume(self):
        return self.heatingVolume

    def setPossibleHeatingRadiation(self,value):
        self.possibleHeatingRadiation = value

    def getPossibleHeatingRadiation(self):
        return self.possibleHeatingRadiation

    def setPossibleHeatingVolume(self,value):
        self.possibleHeatingVolume = value

    def getPossibleHeatingVolume(self):
        return self.possibleHeatingVolume

class RoomState(State):
    def __init__(self):
        self.targetTemperature = None
    
    def setName(self,name):
        self.name = name

    def getName(self):
        return self.name

    def setCurrentTemperature(self,value):
        self.temperature = value

    def getCurrentTemperature(self):
        return self.temperature

    def setChargedBuffer(self,value):
        self.chargedBuffer = value

    def getChargedBuffer(self):
        return self.chargedBuffer

class HouseState(State):
    def setRoomStates(self,values):
        self.roomStates = values
        
    def getRoomStates(self):
        return self.roomStates

    def getRoomState(self,roomName):
        return self.roomStates[roomName]

    def setHeatingPumpSpeed(self,value):
        self.heatingPumpSpeed = value
        
    def getHeatingPumpSpeed(self):
        return self.heatingPumpSpeed

    def setHeatingVolumeFactor(self,value):
        self.heatingVolumeFactor = value
        
    def getHeatingVolumeFactor(self):
        return self.heatingVolumeFactor

    def setHeatingDebugInfo(self,value):
        self.heatingDebugInfo = value
        
    def getHeatingDebugInfo(self):
        return self.heatingDebugInfo

    def setReferenceTemperature(self,value):
        self.referenceTemperature = value

    def getReferenceTemperature(self):
        return self.referenceTemperature
      
    def setCloudCover(self,value):
        self.cloudCover = value

    def getCloudCover(self):
        return self.cloudCover

    def setSunSouthRadiation(self,value):
        self.sunSouthRadiation = value
        
    def getSunSouthRadiation(self):
        return self.sunSouthRadiation

    def setSunWestRadiation(self,value):
        self.sunWestRadiation = value

    def getSunWestRadiation(self):
        return self.sunWestRadiation

    def setSunSouthRadiationMax(self,value):
        self.sunSouthRadiationMax = value
        
    def getSunSouthRadiationMax(self):
        return self.sunSouthRadiationMax

    def setSunWestRadiationMax(self,value):
        self.sunWestRadiationMax = value

    def getSunWestRadiationMax(self):
        return self.sunWestRadiationMax

    def setSunDebugInfo(self,value):
        self.sunDebugInfo = value
        
    def getSunDebugInfo(self):
        return self.sunDebugInfo

class RoomHeatingState():
    def __init__(self):
        self.lazyReduction = 0
        self.outdoorReduction = 0
        self.nightReduction = 0
        self.heatingDemandEnergy = 0
        self.heatingDemandTime = 0
        self.reserveBuffer = 0
        self.adjustedChargedBuffer = None
        self.forcedInfo = None
        self.debugInfo = None
        self.openWindowState = 0

    def setName(self,name):
        self.name = name

    def getName(self):
        return self.name

    def setLazyReduction(self,value):
        self.lazyReduction = value

    def getLazyReduction(self):
        return self.lazyReduction

    def setOutdoorReduction(self,value):
        self.outdoorReduction = value

    def getOutdoorReduction(self):
        return self.outdoorReduction

    def setNightReduction(self,value):
        self.nightReduction = value

    def getNightReduction(self):
        return self.nightReduction

    def setHeatingTargetTemperature(self,value):
        self.heatingTargetTemperature = value

    def getHeatingTargetTemperature(self):
        return self.heatingTargetTemperature

    def setHeatingDemandEnergy(self,value):
        self.heatingDemandEnergy = value

    def getHeatingDemandEnergy(self):
        return self.heatingDemandEnergy

    def setHeatingDemandTime(self,value):
        self.heatingDemandTime = value

    def getHeatingDemandTime(self):
        return self.heatingDemandTime

    def setAdjustedChargedBuffer(self,value):
        self.adjustedChargedBuffer = value

    def getAdjustedChargedBuffer(self):
        return self.adjustedChargedBuffer

    def setChargedReserveBuffer(self,value):
        self.chargedReserveBuffer = value

    def getChargedReserveBuffer(self):
        return self.chargedReserveBuffer

    def setOpenWindowState(self,state):
        self.openWindowState = state
    
    def hasOpenWindow(self):
        return self.openWindowState > 0

    def hasLongOpenWindow(self):
        return self.openWindowState > 1

    def setInfo(self,value):
        self.info = value

    def getInfo(self):
        return self.info

    def setForcedInfo(self,value):
        self.forcedInfo = value

    def getForcedInfo(self):
        return self.forcedInfo

    def setDebugInfo(self,value):
        self.debugInfo = value

    def getDebugInfo(self):
        return self.debugInfo

class HouseHeatingState():
    def __init__(self):
        self.heatingStates = {}
        
    def setHeatingState(self,roomName,state):
        self.heatingStates[roomName]=state

    def getHeatingState(self,roomName):
        return self.heatingStates[roomName]
    
    def setHeatingRequested(self,value):
        self.heatingRequested=value

    def isHeatingRequested(self):
        return self.heatingRequested
