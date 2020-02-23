# -*- coding: utf-8 -*-

class State(object):
    def setBufferCapacity(self,value):
        self.bufferCapacity = value

    def getBufferCapacity(self):
        return self.bufferCapacity

    def getBufferSlotCapacity(self):
        return self.bufferCapacity * 0.1

    def setWallCooling(self,value):
        self.wallCooling = value
        
    def getWallCooling(self):
        return self.wallCooling
        
    def setWallRadiation(self,value):
        self.wallRadiation = value
        
    def getWallRadiation(self):
        return self.wallRadiation

    def setVentilationCooling(self,value):
        self.ventilationCooling = value
        
    def getVentilationCooling(self):
        return self.ventilationCooling

    def setLeakCooling(self,value):
        self.leakCooling = value
        
    def getLeakCooling(self):
        return self.leakCooling

    def setWindowCooling(self,value):
        self.windowCooling = value
        
    def getWindowCooling(self):
        return self.windowCooling

    def setWindowRadiation(self,value):
        self.windowRadiation = value

    def getWindowRadiation(self):
        return self.windowRadiation

    def getPassiveSaldo(self):
        return self.wallCooling+self.wallRadiation+self.ventilationCooling+self.leakCooling+self.windowCooling+self.windowRadiation
      
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

    def setOpenWindowCount(self,count):
        self.openWindowCount = count

    def getOpenWindowCount(self):
        return self.openWindowCount

    def setCurrentTemperature(self,value):
        self.temperature = value

    def getCurrentTemperature(self):
        return self.temperature

    def setTargetTemperature(self,value):
        self.targetTemperature = value

    def getTargetTemperature(self):
        return self.targetTemperature

    def setHeatingBuffer(self,value):
        self.heatingBuffer = value

    def getHeatingBuffer(self):
        return self.heatingBuffer
      
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

    def setHeatingDebugInfo(self,value):
        self.heatingDebugInfo = value
        
    def getHeatingDebugInfo(self):
        return self.heatingDebugInfo

    def setReferenceTemperature(self,value):
        self.referenceTemperature = value

    def getReferenceTemperature(self):
        return self.referenceTemperature
      
    def setSunSouthRadiation(self,value):
        self.sunSouthRadiation = value
        
    def getSunSouthRadiation(self):
        return self.sunSouthRadiation

    def setSunWestRadiation(self,value):
        self.sunWestRadiation = value

    def getSunWestRadiation(self):
        return self.sunWestRadiation

    def setSunDebugInfo(self,value):
        self.sunDebugInfo = value
        
    def getSunDebugInfo(self):
        return self.sunDebugInfo

class HouseHeatingState():
    def __init__(self):
        self.heatingStates = {}
        
    def setHeatingState(self,roomName,state):
        self.heatingStates[roomName]=state

    def getHeatingState(self,roomName):
        return self.heatingStates[roomName]
    
    def setHeatingNeeded(self,value):
        self.heatingNeeded=value

    def isHeatingNeeded(self):
        return self.heatingNeeded

class RoomHeatingState():
    def __init__(self):
        self.lazyReduction = 0
        self.outdoorReduction = 0
        self.nightReduction = 0
        self.heatingDemandEnergy = 0
        self.heatingDemandTime = 0
        self.chargedBuffer = 0
        self.originalChargedBuffer = 0
        self.forcedInfo = None

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

    def setHeatingDemandEnergy(self,value):
        self.heatingDemandEnergy = value

    def getHeatingDemandEnergy(self):
        return self.heatingDemandEnergy

    def setHeatingDemandTime(self,value):
        self.heatingDemandTime = value

    def getHeatingDemandTime(self):
        return self.heatingDemandTime

    def setOriginalChargedBuffer(self,value):
        self.originalChargedBuffer = value

    def getOriginalChargedBuffer(self):
        return self.originalChargedBuffer

    def setChargedBuffer(self,value):
        self.chargedBuffer = value

    def getChargedBuffer(self):
        return self.chargedBuffer

    def setInfo(self,value):
        self.info = value

    def getInfo(self):
        return self.info

    def setForcedInfo(self,value):
        self.forcedInfo = value

    def getForcedInfo(self):
        return self.forcedInfo
