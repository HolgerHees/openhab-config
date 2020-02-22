# -*- coding: utf-8 -*-

class State(object):
    def setBufferCapacity(self,value):
        self.bufferCapacity = value

    def getBufferCapacity(self):
        return self.bufferCapacity

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

    def setPassiveSaldo(self,value):
        self.saldo = value

    def getPassiveSaldo(self):
        return self.saldo
      
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
    def setName(self,name):
        self.name = name

    def getName(self):
        return self.name

    def setOpenWindowCount(self,count):
        self.openWindowCount = count

    def getOpenWindowCount(self):
        return self.openWindowCount

    def setActive(self,active):
        self.active = active

    def getActive(self):
        return self.active

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

    def setSunDebugInfo(self,value):
        self.sunDebugInfo = value
        
    def getSunDebugInfo(self):
        return self.sunDebugInfo

    def setReferenceTemperature(self,value):
        self.referenceTemperature = value

    def getReferenceTemperature(self):
        return self.referenceTemperature

class HouseHeatingState():
    def setHeatingStates(self,values):
        self.heatingStates = values
        
    def getHeatingStates(self):
        return self.heatingStates

    def getHeatingState(self,roomName):
        return self.heatingStates[roomName]
    
    def setHeatingState(self,roomName,state):
        self.heatingStates[roomName]=state

class RoomHeatingState():
    def __init__(self):
        self.lazyReduction = 0
        self.heatingDemandEnergy = 0
        self.heatingDemandTime = 0
        self.chargedBuffer = 0

    def setLazyReduction(self,value):
        self.lazyReduction = value

    def getLazyReduction(self):
        return self.lazyReduction

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

    def setChargedBuffer(self,value):
        self.chargedBuffer = value

    def getChargedBuffer(self):
        return self.chargedBuffer

    def setHeatingBuffer(self,value):
        self.heatingBuffer = value

    def getHeatingBuffer(self):
        return self.heatingBuffer

    def setInfo(self,value):
        self.info = value

    def getInfo(self):
        return self.info
