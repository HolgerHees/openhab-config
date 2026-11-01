class ThermalBridgeType():
    def __init__(self, uValue, uOffset):
        self.uValue = uValue
        self.uOffset = uOffset
        
    def getUValue(self):
        return self.uValue
        
    def getUOffset(self):
        return self.uOffset

class ThermalStorageType(ThermalBridgeType):
    def __init__(self, uValue, uOffset, capacityInKiloJoulePerSquareMeter, uValueInner=None, uValueOuter=None):
        super().__init__(uValue, uOffset)
        self.uValueInner = uValueInner
        self.uValueOuter = uValueOuter
        self.capacityInKiloJoulePerSquareMeter = capacityInKiloJoulePerSquareMeter
       
    def getUValueInner(self):
        return self.uValueInner

    def getUValueOuter(self):
        return self.uValueOuter

class Wall():
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

    def getCapacityInWattHours(self):
        return (self.type.capacityInKiloJoulePerSquareMeter / 3.6) * self.area

    def isWindow(self):
        return False

class Door(Wall):
    def __init__(self, direction, area, type, bound= None, contactItem=None):
        super(Door,self).__init__(direction, area, type, bound)
        self.contactItem = contactItem
        
    def getContactItem(self):
        return self.contactItem

class Window(Door):
    def __init__(self, direction, area, type, bound= None, contactItem=None, shutterItem=None, shutterArea=None, radiationArea=None, sunProtectionItem=None):
        super().__init__(direction, area, type, bound, contactItem)
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

    def isWindow(self):
        return True

class Room():
    def __init__(self, name, ventilation=False, additionalRadiator=False, heatingVolume=None, volume=None, walls=[], transitions=[]):
        self.name = name
        self.ventilation = ventilation
        self.additionalRadiator = additionalRadiator
        self.heatingVolume = heatingVolume
        self.volume = volume
        self.walls = walls
        self.transitions = transitions
  
    def getName(self):
        return self.name

    def hasVentilation(self):
        return self.ventilation

    def hasAdditionalRadiator(self):
        return self.additionalRadiator

    def getHeatingVolume(self):
        return self.heatingVolume

    def getVolume(self):
        return self.volume

    def getWalls(self):
        return self.walls

    def getTransitions(self):
        return self.transitions
