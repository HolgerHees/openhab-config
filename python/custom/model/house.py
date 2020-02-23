# -*- coding: utf-8 -*-

class ThermalBridgeType(object):
    def __init__(self, uValue=None, uOffset=None, factor=None, referenceTemperatureItem=None):
        self.uValue = uValue
        self.uOffset = uOffset
        self.factor = factor
        self.referenceTemperatureItem = referenceTemperatureItem
        
    def getUValue(self):
        return self.uValue
        
    def getUOffset(self):
        return self.uOffset

    def getFactor(self):
        return self.factor

    def getReferenceTemperatureItem(self):
        return self.referenceTemperatureItem

class ThermalStorageType(ThermalBridgeType):
    def __init__(self, capacity, uValue=None, uOffset=None, factor=None, referenceTemperatureItem=None):
        super(ThermalStorageType,self).__init__(uValue, uOffset, factor, referenceTemperatureItem)
        self.capacity = capacity
        
    def getCapacity(self):
        return self.capacity
       
class Wall(object):
    def __init__(self, direction, area, type, bound= None):
        self.direction = direction
        self.area = area
        self.type = type
        self.bound = bound
    
    def getDirection(self):
        return self.direction

    def getArea(self):
        return self.area

    def getType(self):
        return self.type

    def getBound(self):
        return self.bound

class Door(Wall):
    def __init__(self, direction, area, type, contactItem=None):
        super(Door,self).__init__(direction, area, type)
        self.contactItem = contactItem
        
    def getContactItem(self):
        return self.contactItem

class Window(Door):
    def __init__(self, direction, area, type, contactItem=None, shutterItem=None, shutterArea=None, radiationArea=None, sunProtectionItem=None):
        super(Window,self).__init__(direction, area, type, contactItem)
        self.shutterItem = shutterItem
        self.shutterArea = shutterArea
        self.radiationArea = radiationArea
        self.sunProtectionItem = sunProtectionItem
        
    def getShutterItem(self):
        return self.shutterItem
      
    def getShutterArea(self):
        return self.shutterArea

    def getRadiationArea(self):
        return self.radiationArea

    def getSunProtectionItem(self):
        return self.sunProtectionItem

class Room(object):
    def __init__(self, name, temperatureSensorItem, temperatureTargetItem=None, heatingBufferItem=None, heatingCircuitItem=None, heatingArea=None, volume=None, walls=None, transitions=[]):
        self.name = name
        self.temperatureSensorItem = temperatureSensorItem
        self.temperatureTargetItem = temperatureTargetItem
        self.heatingBufferItem = heatingBufferItem
        self.heatingCircuitItem = heatingCircuitItem
        self.heatingArea = heatingArea
        self.volume = volume
        self.walls = walls
        self.transitions = transitions
  
    def getName(self):
        return self.name

    def getTemperatureSensorItem(self):
        return self.temperatureSensorItem

    def getTemperatureTargetItem(self):
        return self.temperatureTargetItem

    def getHeatingBufferItem(self):
        return self.heatingBufferItem

    def getHeatingCircuitItem(self):
        return self.heatingCircuitItem

    def getHeatingArea(self):
        return self.heatingArea

    def getVolume(self):
        return self.volume

    def getWalls(self):
        return self.walls

    def getTransitions(self):
        return self.transitions
