from core.triggers import CronTrigger, ItemStateChangeTrigger
from custom.helper import rule, getNow, getHistoricItemEntry, getItemState, getItemLastChange, getItemLastUpdate, sendCommand, sendCommandIfChanged, postUpdate, postUpdateIfChanged, itemLastChangeOlderThen, itemLastUpdateOlderThen, getStableItemState
from custom.model.heating import Heating
from custom.model.house import ThermalStorageType, ThermalBridgeType, Wall, Door, Window, Room
from custom.model.sun import SunRadiation

from org.joda.time import DateTime
from org.joda.time.format import DateTimeFormat
from core.actions import Transformation
import math

OFFSET_FORMATTER = DateTimeFormat.forPattern("HH:mm")

Heating.cloudCoverFC8Item = "Cloud_Cover_Forecast8"
Heating.cloudCoverFC4Item = "Cloud_Cover_Forecast4"
Heating.cloudCoverItem = "Cloud_Cover_Current"

Heating.temperatureGardenFC8Item = "Temperature_Garden_Forecast8"
Heating.temperatureGardenFC4Item = "Temperature_Garden_Forecast4"

Heating.ventilationFilterRuntimeItem = "Ventilation_Filter_Runtime"

Heating.ventilationLevelItem = "Ventilation_Outgoing"
Heating.ventilationOutgoingTemperatureItem = "Ventilation_Outdoor_Outgoing_Temperature"
Heating.ventilationIncommingTemperatureItem = "Ventilation_Outdoor_Incoming_Temperature"

Heating.heatingPower = "Heating_Power"
Heating.heatingCircuitPumpSpeedItem = "Heating_Circuit_Pump_Speed"
Heating.heatingTemperaturePipeOutItem = "Heating_Temperature_Pipe_Out"
Heating.heatingTemperaturePipeInItem = "Heating_Temperature_Pipe_In"

Heating.holidayStatusItem = "State_Holidays_Active"

_groundFloor = ThermalStorageType( capacity=164.0, uValue=0.320, uOffset=0.08, factor=0.60 )
_groundCeiling = ThermalStorageType( capacity=308.0, uValue=0.610, uOffset=0.1, factor=1.0 )

_outer36Wall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0 )
_outer22Wall = ThermalStorageType( capacity=53.0, uValue=0.348, uOffset=0.08, factor=1.0 )
_garageWall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0 )

_inner11Wall = ThermalStorageType( capacity=87.0 / 2.0, uValue=0.883, uOffset=0, factor=1.0 )
_inner17Wall = ThermalStorageType( capacity=111.0 / 2.0, uValue=0.565, uOffset=0, factor=1.0 )

_mainDoor = ThermalBridgeType( uValue=1.400, uOffset=0.08, factor=1.0 )
_utilityroomGarageDoor = ThermalBridgeType( uValue=1.700, uOffset=0.08, factor=1.0 )
_outerWindow = ThermalBridgeType( uValue=0.970, uOffset=0.08, factor=1.0 )

_outerShutter = ThermalBridgeType( uValue=0.34, uOffset=0.08, factor=1.0 )

_firstFloor = ThermalStorageType( capacity=136.0, uValue=0.610, uOffset=0.1, factor=1.0 )
_firstCeiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0 )
_firstSlopingCeiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0 )
_firstSlopingWindow = ThermalBridgeType( uValue=1.400, uOffset=0.1, factor=1.0 )

_atticFloor = ThermalStorageType( capacity=1.7, uValue=0.186, uOffset=0, factor=1.0 )

# https://de.wikipedia.org/wiki/W%C3%A4rmedurchgangskoeffizient
_garageWindow = ThermalBridgeType( uValue=2.0, uOffset=0.1, factor=1.0 )
_garageDoor = ThermalBridgeType( uValue=3.49, uOffset=0.1, factor=1.0 )

_firstFloorHeight = 2.57
_secondFloorHeight = 2.45
_atticFloorHeight = 2.10

Heating.temperatureSensorItemPlaceholder = u"Temperature_{}"
Heating.temperatureTargetItemPlaceholder = u"Temperature_{}_Target"
Heating.heatingBufferItemPlaceholder = u"Heating_{}_Charged"
Heating.heatingCircuitItemPlaceholder = u"Heating_{}_Circuit"
Heating.heatingTargetTemperatureItemPlaceholder = u"Heating_{}_Target_Temperature"
Heating.heatingDemandItemPlaceholder = u"Heating_{}_Demand"

rooms = [
    Room(
        name='FF_Garage',
        volume=54.0702 * _atticFloorHeight / 2.0,
        walls=[
            Wall(direction='floor', area=27.456025, type=_atticFloor),
            Wall(direction='ceiling', area=27.456025, type=_firstSlopingCeiling),
            Wall(direction='west', area=5.319, type=_outer22Wall),
            Wall(direction='north', area=4.18, type=_outer36Wall, bound="FF_Livingroom"),
            Wall(direction='north', area=3.509, type=_outer36Wall, bound="FF_Boxroom"),
            Wall(direction='north', area=5.5, type=_outer36Wall, bound="FF_Utilityroom"),
            Wall(direction='north', area=3.85, type=_outer36Wall,bound="FF_GuestWC"),
            Wall(direction='east', area=5.21, type=_outer22Wall),
            Wall(direction='south', area=17.039, type=_outer22Wall)
        ],
        transitions=[
            Window(direction='west', area=0.6, type=_garageWindow),
            Door(direction='west', area=1.880625, type=_garageDoor),
            Door(direction='east', area=1.880625, type=_garageDoor) 
        ]
    ),
    Room(
        name='FF_GuestWC',
        additionalRadiator=True,
        heatingVolume=29.63,
        volume=4.92445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=6.29125, type=_groundFloor),
            Wall(direction='ceiling', area=6.29125, type=_groundCeiling, bound="SF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="FF_Utilityroom"),
            Wall(direction='north', area=3.4949, type=_inner17Wall, bound="FF_Floor"),
            Wall(direction='east', area=9.14345, type=_outer36Wall),
            Wall(direction='south', area=5.0225, type=_garageWall, bound="FF_Garage")
        ],
        transitions=[
            Window(direction='east', area=1.045, type=_outerWindow, contactItem='Window_FF_GuestWC', shutterItem='Shutters_FF_GuestWC', shutterArea=0.1292)
        ]
    ),
    Room(
        name='FF_Utilityroom',
        # TODO check
        #heatingVolume=27.04,
        volume=7.816325 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=8.9875, type=_groundFloor),
            Wall(direction='ceiling', area=8.9875, type=_groundCeiling, bound="SF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="FF_Boxroom"),
            Wall(direction='north', area=5.39615, type=_inner17Wall, bound="FF_Floor"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="FF_GuestWC"),
            Wall(direction='south', area=5.294375, type=_garageWall, bound="FF_Garage")
        ],
        transitions=[
            Door(direction='south', area=1.880625, type=_utilityroomGarageDoor, bound="FF_Garage")
        ]
    ),
    Room(
        name='FF_Boxroom',
        volume=4.72615 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=5.734025, type=_groundFloor),
            Wall(direction='ceiling', area=5.734025, type=_groundCeiling, bound="SF_Bedroom"), # Dressingroom
            Wall(direction='west', area=8.5388, type=_inner17Wall, bound="FF_Livingroom"),
            Wall(direction='north', area=4.57765, type=_inner17Wall, bound="FF_Livingroom"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="FF_Utilityroom"),
            Wall(direction='south', area=4.57765, type=_garageWall, bound="FF_Garage")
        ]
    ),
    Room(
        name='FF_Livingroom',
        heatingVolume=84.20 + 84.20 + 49.90,
        volume=37.9957 * _firstFloorHeight + 10.7406 * _firstFloorHeight,
        walls=[
            # Kitchen
            Wall(direction='floor', area=12.999225, type=_groundFloor),
            Wall(direction='ceiling', area=12.999225, type=_groundCeiling, bound="SF_Bedroom"), # Dressingroom
            Wall(direction='east', area=8.789925, type=_inner17Wall, bound="FF_Boxroom"),
            Wall(direction='south', area=4.6781, type=_garageWall, bound="FF_Garage"),
            Wall(direction='south', area=5.453, type=_outer36Wall),
            Wall(direction='west', area=8.069575, type=_outer36Wall),
            #Wall(direction='north', area=4.57765, type=_inner17Wall),

            # Livingroom
            Wall(direction='floor', area=42.4732875, type=_groundFloor),
            Wall(direction='ceiling', area=16.3125, type=_groundCeiling, bound="SF_Bedroom"),
            Wall(direction='ceiling', area=17.07625, type=_groundCeiling, bound="SF_Child2"),
            Wall(direction='ceiling', area=9.0845375, type=_groundCeiling, bound="SF_Floor"),
            Wall(direction='south', area=3.393775, type=_outer36Wall),
            Wall(direction='west', area=9.292675, type=_outer36Wall),
            Wall(direction='north', area=18.92765, type=_outer36Wall),
            Wall(direction='east', area=7.34725, type=_inner17Wall, bound="FF_Floor"),
            Wall(direction='east', area=10.339175, type=_inner17Wall, bound="FF_Guestroom"),
            Wall(direction='south', area=6.177675, type=_inner17Wall, bound="FF_Boxroom")
        ],
        transitions=[
            Window(direction='west', area=2.2, type=_outerWindow, contactItem='Window_FF_Kitchen', shutterItem='Shutters_FF_Kitchen', shutterArea=0.2992, radiationArea=0.645*1.01*2.0, sunProtectionItem="State_Sunprotection_Livingroom"),
            Window(direction='west', area=5.8232, type=_outerWindow, contactItem='Window_FF_Livingroom_Terrace', shutterItem='Shutters_FF_Livingroom_Terrace', shutterArea=0.4267, radiationArea=0.625*2.13*3.0),
            Window(direction='west', area=4.0832, type=_outerWindow, contactItem='Window_FF_Livingroom_Couch', shutterItem='Shutters_FF_Livingroom_Couch', shutterArea=0.2992, radiationArea=0.625*2.13*2.0)
        ]
    ),
    Room(
        name='FF_Guestroom',
        heatingVolume=60.19,
        volume=11.53445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=13.5891, type=_groundFloor),
            Wall(direction='ceiling', area=13.5891, type=_groundCeiling, bound="SF_Child1"),
            Wall(direction='west', area=10.31765, type=_inner17Wall, bound="FF_Livingroom"),
            Wall(direction='north', area=10.8486, type=_outer36Wall),
            Wall(direction='east', area=7.9847, type=_outer36Wall),
            Wall(direction='south', area=9.06975, type=_inner17Wall, bound="FF_Floor")
        ],
        transitions=[
            Window(direction='east', area=2.07625, type=_outerWindow, contactItem='Window_FF_Guestroom', shutterItem='Shutters_FF_Guestroom', shutterArea=0.2567)
        ]
    ),
    Room(
        name='FF_Floor',
        heatingVolume=40.93,
        volume=11.3076 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=12.9843, type=_groundFloor),
            Wall(direction='ceiling', area=2.0524125, type=_groundCeiling, bound="SF_Floor"),
            Wall(direction='west', area=7.0746, type=_inner17Wall, bound="FF_Livingroom"),
            Wall(direction='north', area=9.06975, type=_inner17Wall, bound="FF_Guestroom"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer36Wall),
            Wall(direction='south', area=3.4949, type=_inner17Wall, bound="FF_GuestWC"),
            Wall(direction='south', area=4.04725, type=_inner17Wall, bound="FF_Utilityroom")
        ],
        transitions=[
            # count the main door only 50%, because other 50% is counted on upper floor
            Door(direction='east', area=4.6632/2.0, type=_mainDoor, contactItem='Door_FF_Floor'),
            # count 50% of the sloping window from upper floor
            Window(direction='east', area=0.7676/2.0, type=_firstSlopingWindow)
        ]
    ),
    Room(
        name='SF_Floor',
        heatingVolume=38.45,
        volume=18.1926 * _secondFloorHeight - 4.3968,
        walls=[
            Wall(direction='floor', area=4.61578125, type=_firstFloor, bound="FF_Livingroom"),
            Wall(direction='floor', area=4.61578125, type=_firstFloor, bound="FF_Floor"),
            Wall(direction='ceiling', area=14.1436125, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=7.77045, type=_inner11Wall, bound="SF_Bedroom"),
            Wall(direction='north', area=8.51865, type=_inner17Wall, bound="SF_Child1"),
            Wall(direction='north', area=1.69615, type=_inner17Wall, bound="SF_Child2"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer36Wall),
            Wall(direction='east', area=8.026, type=_firstSlopingCeiling),
            Wall(direction='south', area=8.51865, type=_inner17Wall, bound="SF_Bathroom"),
            Wall(direction='south', area=1.69615, type=_inner17Wall, bound="SF_Bedroom"), # Dressingroom
        ],
        transitions=[
            # count 50% of the main door from lower floor
            Door(direction='east', area=4.6632/2.0, type=_mainDoor, contactItem='Door_FF_Floor'),
            # count the sloping window only 50%, because other 50% is counted on lower floor
            Window(direction='east', area=0.7676/2.0, type=_firstSlopingWindow)
        ]
    ),
    Room(
        name='SF_Child1',
        heatingVolume=39.61,
        volume=13.036325 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=4.0, type=_firstFloor, bound="FF_Livingroom"),
            Wall(direction='floor', area=12.626875, type=_firstFloor, bound="FF_Guestroom"),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner11Wall, bound="SF_Child2"),
            Wall(direction='north', area=8.1533, type=_outer36Wall),
            Wall(direction='east', area=3.595, type=_outer36Wall),
            Wall(direction='east', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='south', area=8.51865, type=_inner17Wall, bound="SF_Floor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='Window_SF_Child1', shutterItem='Shutters_SF_Child1', shutterArea=0.2567)
        ]
    ),
    Room(
        name='SF_Child2',
        heatingVolume=41.32,
        volume=14.99575 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=17.07625, type=_firstFloor, bound="FF_Livingroom"),
            Wall(direction='ceiling', area=10.7760125, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=3.595, type=_outer36Wall),
            Wall(direction='west', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='north', area=8.5008, type=_outer36Wall),
            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="SF_Child1"),
            Wall(direction='south', area=7.17, type=_inner17Wall, bound="SF_Bedroom"),
            Wall(direction='south', area=1.69615, type=_inner17Wall, bound="SF_Floor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='Window_SF_Child2', shutterItem='Shutters_SF_Child2', shutterArea=0.2567)
        ]
    ),
    Room(
        name='SF_Bedroom',
        heatingVolume=35.87 + 39.33,
        volume=(14.3929 * _secondFloorHeight) + (14.88435 * _secondFloorHeight - 4.6016),
        walls=[
            # Bedroom
            Wall(direction='floor', area=16.3125, type=_firstFloor, bound="FF_Livingroom"),
            Wall(direction='ceiling', area=16.3125, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=5.9851, type=_outer36Wall),
            Wall(direction='north', area=12.51, type=_inner17Wall, bound="SF_Child2"),
            Wall(direction='east', area=8.03455, type=_inner11Wall, bound="SF_Floor"),
            Wall(direction='south', area=3.28735, type=_outer36Wall),
            Wall(direction='south', area=0.5, type=_firstSlopingCeiling),

            # Dressingroom
            Wall(direction='floor', area=16.660625, type=_firstFloor, bound="FF_Livingroom"),
            Wall(direction='ceiling', area=10.40850625, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=3.5075, type=_outer36Wall),
            Wall(direction='west', area=8.9792, type=_firstSlopingCeiling),
            Wall(direction='north', area=3.63485, type=_inner17Wall, bound="SF_Floor"),
            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="SF_Bathroom"),
            Wall(direction='south', area=9.0333, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='west', area=3.1375, type=_outerWindow, contactItem='Window_SF_Bedroom', shutterItem='Shutters_SF_Bedroom', shutterArea=0.4267, radiationArea=0.615*1.00*3.0, sunProtectionItem="State_Sunprotection_Bedroom"),
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='Window_SF_Dressingroom', shutterItem='Shutters_SF_Dressingroom', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="State_Sunprotection_Dressingroom")
#        ]
        ]
    ),
#    Room(
#        name='SF_Dressingroom',
#        heatingVolume=57.58,
#        volume=14.88435 * _secondFloorHeight - 4.6016,
#        walls=[
#            Wall(direction='floor', area=16.660625, type=_firstFloor, bound="FF_Livingroom"),
#            Wall(direction='ceiling', area=10.40850625, type=_firstCeiling, bound="SF_Attic"),
#            Wall(direction='west', area=3.5075, type=_outer36Wall),
#            Wall(direction='west', area=8.9792, type=_firstSlopingCeiling),
#            Wall(direction='north', area=3.63485, type=_inner17Wall, bound="SF_Floor"),
#            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="SF_Bathroom"),
#            Wall(direction='south', area=9.0333, type=_outer36Wall)
#        ],
#        transitions=[
#            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='Window_SF_Dressingroom', shutterItem='Shutters_SF_Dressingroom', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="State_Sunprotection_Dressingroom")
#        ]
#    ),
    Room(
        name='SF_Bathroom',
        additionalRadiator=True,
        heatingVolume=35.31,
        volume=12.51273 * _secondFloorHeight - 2.5884,
        walls=[
            Wall(direction='floor', area=5.482375, type=_firstFloor, bound="FF_GuestWC"),
            Wall(direction='floor', area=8.9875, type=_firstFloor, bound="FF_Utilityroom"),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling, bound="SF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner11Wall, bound="SF_Bedroom"), # Dressingroom
            Wall(direction='north', area=7.4633, type=_inner17Wall, bound="SF_Floor"),
            Wall(direction='east', area=5.033, type=_outer36Wall),
            Wall(direction='east', area=5.1768, type=_firstSlopingCeiling),
            Wall(direction='south', area=7.63045, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='Window_SF_Bathroom', shutterItem='Shutters_SF_Bathroom', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="State_Sunprotection_Bathroom")
        ]
    ),
    Room(
        name='SF_Attic',
        volume=54.0702 * _atticFloorHeight / 2.0,
        walls=[
            Wall(direction='floor', area=59.871875, type=_atticFloor, bound="SF_Bedroom" ),
            Wall(direction='west', area=9.9941, type=_outer36Wall),
            Wall(direction='west', area=49.9872093014803, type=_firstSlopingCeiling),
            Wall(direction='north', area=5.91675, type=_outer36Wall),
            Wall(direction='east', area=49.9872093014803, type=_firstSlopingCeiling),
            Wall(direction='south', area=5.01995, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='east', area=0.7676, type=_firstSlopingWindow),
            Window(direction='south', area=0.7676, type=_outerWindow, contactItem='Window_SF_Attic', shutterItem='Shutters_SF_Attic', shutterArea=0.19295, radiationArea=0.72*1.00, sunProtectionItem="State_Sunprotection_Attic")
        ]
    )
]

Heating.init(rooms)

controllableRooms = {
  'FF_Livingroom': True,
  'FF_Floor': True,
  'FF_Guestroom': True,
  'FF_GuestWC': True,
  'FF_GuestWCHK': True,
  'SF_Floor': True,
  'SF_Child1': True,
  'SF_Child2': True,
  'SF_Bedroom': True,
  'SF_Bathroom': True,
  'SF_BathroomHK': True
}
maintenanceMode = {}

#@rule("heating_control.py")
#class TestRule():
#    def __init__(self):
#        totalVolume=0
#        for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):
#            #roomCapacity = 0
#            #for wall in room.getWalls():
#            #    capacity = ( wall.getArea() * wall.getType().getCapacity() ) / 3.6 # converting kj into watt
#            #    roomCapacity = roomCapacity + capacity
#            #self.log.info("{} {}".format(room.getName(),roomCapacity)) 
#            self.log.info("{} {}".format(room.getName(),room.getHeatingVolume())) 
#            totalVolume = totalVolume + room.getHeatingVolume()
#        self.log.info("{}".format(totalVolume))
#              
#    def execute(self, module, input):
#        pass

#@rule("heating_control.py")
#class TestRule():
#    def __init__(self):
#        heating = Heating(self.log)

#        currentTotalVentilationEnergy = heating.getVentilationEnergy(1.0) / 3.6

#        for room in Heating.getRooms():
#        #for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):
#            energyLost = ventilationLost = leakLost = roomCapacity = 0
#            for transition in filter( lambda transition: transition.getBound() == None, room.getTransitions() ):
#                type = transition.getType()
#                coolingPerKelvin = ( type.getUValue() + type.getUOffset() ) * transition.getArea() * type.getFactor()
#                energyLost = energyLost + coolingPerKelvin

#            ventilationLost = ventilationLost + room.getVolume() * currentTotalVentilationEnergy / Heating.totalVolume

#            leakLost = leakLost + heating.getLeakingEnergy(room.getVolume(),20.0,19.0) / 3.6

#            for wall in room.getWalls():
#                if wall.getBound() == None:
#                    type = wall.getType()
#                    coolingPerKelvin = ( type.getUValue() + type.getUOffset() ) * wall.getArea() * type.getFactor()
#                    energyLost = energyLost + coolingPerKelvin

#                capacity = ( wall.getArea() * wall.getType().getCapacity() ) / 3.6 # converting kj into watt
#                roomCapacity = roomCapacity + capacity

#            self.log.info(u"{} wall: {} ventilation: {} leak: {} capacity: {}".format(room.getName(),energyLost,ventilationLost,leakLost,roomCapacity))

#    def execute(self, module, input):
#        pass

@rule("heating_control.py")
class HeatingVentileRule():
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */10 1 ? * MON,FRI"),
            CronTrigger("0 0 2 ? * MON,FRI")
        ]

    # refresh heating ventile twice per week
    def execute(self, module, input):
        now = getNow()
        for room in filter( lambda room: room.getHeatingVolume() != None and room.getName() in controllableRooms,Heating.getRooms()):
            circuiteItem = Heating.getHeatingCircuitItem(room)
            maintainanceModeActive = room in maintenanceMode

            if maintainanceModeActive or itemLastChangeOlderThen(circuiteItem,now.minusHours(24)):
                hour = now.getHourOfDay()
                if hour == 2 or getItemState(circuiteItem) == OFF:
                    postUpdateIfChanged(circuiteItem,ON)
                else:
                    postUpdateIfChanged(circuiteItem,OFF)
                    
                if room.hasAdditionalRadiator():
                    hkItem = Heating.getHeatingHKItem(room)
                    if hour == 2 or getItemState(hkItem) == OFF:
                        sendCommandIfChanged(hkItem,ON)
                    else:
                        sendCommandIfChanged(hkItem,OFF)
                
                if hour == 2:
                    del maintenanceMode[room]
                elif not maintainanceModeActive:
                    maintenanceMode[room] = True
                
@rule("heating_control.py")
class HeatingControlRule():
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Operating_Mode")
        ]

    def execute(self, module, input):
        mqttActions = actions.get("mqtt","mqtt:broker:mosquitto")
        mqttActions.publishMQTT("/vcontrol/setBetriebsartTo",u"{}".format(getItemState("Heating_Operating_Mode").intValue()))
            
@rule("heating_control.py")
class HeatingControlRule():
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Auto_Mode"),
            CronTrigger("15 * * * * ?")
#            CronTrigger("*/15 * * * * ?")
        ]
        self.activeHeatingOperatingMode = -1

    def execute(self, module, input):
        self.log.info(u"--------: >>>" )

        now = getNow()
        autoModeEnabled = getItemState("Heating_Auto_Mode").intValue() == 1
        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        currentHeatingDemand = getItemState("Heating_Demand")

        outdoorTemperatureItemName = getItemState("Outdoor_Temperature_Item_Name").toString()
        heating = Heating(self.log,outdoorTemperatureItemName)

        cr, cr4, cr8, hhs = heating.calculate(currentHeatingDemand == ON)    
        
        if autoModeEnabled:
            heatingRequested = hhs.isHeatingRequested()
            
            # *** CHECK OPEN WINDOWS AND MIN HEATING VOLUME ***
            disabledHeatingDemandCount = 0
            requestedPossibleHeatingVolume = 0.0
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):
            
                rs = cr.getRoomState(room.getName())
                rhs = hhs.getHeatingState(room.getName())

                # *** CHECKED HEATING DEMAND ***
                if rhs.hasLongOpenWindow():
                    disabledHeatingDemandCount = disabledHeatingDemandCount + 1
            
                if rhs.getHeatingDemandTime() != None and rhs.getHeatingDemandTime() > 0.0:
                    requestedPossibleHeatingVolume = requestedPossibleHeatingVolume + rs.getPossibleHeatingVolume()
                
            if heatingRequested:
                # *** FORCED HEATING OFF ***
                if disabledHeatingDemandCount >= 3:
                    heatingRequested = False
                    self.log.info(u"        : ---")
                    self.log.info(u"        : Heating OFF • too many open windows")
                    
                # *** FORCED HEATING OFF IF ONLY 20%***
                if requestedPossibleHeatingVolume < Heating.totalHeatingVolume * 0.2:
                    heatingRequested = False
                    activeHeatingVolume = round(requestedPossibleHeatingVolume / 1000.0,3)
                    possibleHeatingVolume = round(Heating.totalHeatingVolume / 1000.0,3)
                    self.log.info(u"        : ---")
                    self.log.info(u"        : Heating OFF • only {}m² of {}m² active".format(activeHeatingVolume,possibleHeatingVolume))
                # *************************************************


            # *** PERSIST AND CIRCUITS ************************
            longestRuntime = 0
            lastCircuitOpenedAt = None
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):
                
                rs = cr.getRoomState(room.getName())
                rhs = hhs.getHeatingState(room.getName())
                
                # *** PERSIST HEATING CHARGE LEVEL ***
                totalChargeLevel = rs.getChargedBuffer()
                postUpdateIfChanged( Heating.getHeatingBufferItem(room), totalChargeLevel )
                
                # *** PERSIST HEATING TARGET TEMPERATURE ***
                postUpdateIfChanged(Heating.getHeatingTargetTemperatureItem(room), rhs.getHeatingTargetTemperature() )
                
                if heatingRequested and rhs.getHeatingDemandTime() > longestRuntime:
                    longestRuntime = rhs.getHeatingDemandTime()

                # *** PERSIST HEATING DEMAND ***
                if heatingRequested and (rhs.getHeatingDemandTime() > 0 or room.getName() not in controllableRooms):
                    postUpdateIfChanged(Heating.getHeatingDemandItem(room),ON)
                else:
                    postUpdateIfChanged(Heating.getHeatingDemandItem(room),OFF)
                    
                # *** CONTROL CIRCUITS AND HK ***
                if room.getName() in controllableRooms and room not in maintenanceMode:
                    circuitItem = Heating.getHeatingCircuitItem(room)
                    if heatingRequested and rhs.getHeatingDemandTime() > 0:
                        #self.log.info("ON")
                        if sendCommandIfChanged(circuitItem,ON):
                            circuitLastChange = now
                        else:
                            circuitLastChange = getItemLastChange(circuitItem)
                            
                        if lastCircuitOpenedAt == None or lastCircuitOpenedAt.getMillis() < circuitLastChange.getMillis():
                            lastCircuitOpenedAt = circuitLastChange                            
                    else:
                        #self.log.info("OFF")
                        sendCommandIfChanged(circuitItem,OFF)
                        
                    # wall radiator
                    if room.hasAdditionalRadiator():
                        # additional radiator should only be enabled in case of CF heating
                        if heatingRequested and rhs.getForcedInfo() == 'CF':
                            sendCommandIfChanged(Heating.getHeatingHKItem(room),ON)
                        else:
                            sendCommandIfChanged(Heating.getHeatingHKItem(room),OFF)
            # *************************************************
            
            
            self.log.info(u"        : ---" )
            
            # a heating ciruit was opened less then 5 minutes ago.
            # delay heating request to give circuit some time to open
            if currentHeatingDemand == OFF and lastCircuitOpenedAt != None and now.getMillis() - lastCircuitOpenedAt.getMillis() < 5 * 60 * 1000:
                #self.log.info(u"{}".format(lastCircuitOpenedAt))
                openedBeforeInMinutes = int( round( ( now.getMillis() - lastCircuitOpenedAt.getMillis() ) / 1000.0 / 60.0 ) )
                self.log.info(u"Demand  : DELAYED • circuit was opened {} min. ago".format(openedBeforeInMinutes))
            else:
                heatingDemand = ON if heatingRequested else OFF
                postUpdateIfChanged("Heating_Demand", heatingDemand )
            
                endMsg = u" • {} min. to go".format(Heating.visualizeHeatingDemandTime(longestRuntime)) if longestRuntime > 0 else u""
                lastHeatingDemandChange = getItemLastUpdate("Heating_Demand") # can be "getItemLastUpdate" datetime, because it is changed only from heating rule
                lastChangeBeforeInMinutes = int( round( ( now.getMillis() - lastHeatingDemandChange.getMillis() ) / 1000.0 / 60.0 ) )
                lastHeatingChangeFormatted = OFFSET_FORMATTER.print(lastHeatingDemandChange)
                lastChangeBeforeFormatted = lastChangeBeforeInMinutes if lastChangeBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastChangeBeforeInMinutes, 60));
                self.log.info(u"Demand  : {} since {} • {} min. ago{}".format(heatingDemand, lastHeatingChangeFormatted, lastChangeBeforeFormatted,endMsg) )
                
                self.controlHeating(now,currentOperatingMode,heatingRequested)  
        else:
            self.log.info(u"Demand  : SKIPPED • MANUAL MODE ACTIVE")

        self.setSunStates(now,cr,cr4,hhs)
        
        self.log.info(u"--------: <<<" )

    def setSunStates(self, now, cr, cr4, hhs ):
        cloudCover = cr.getCloudCover()

        azimut = getItemState("Sun_Azimuth").doubleValue()

        # 225 => 15:32:30.781
        # 245 => 16:57:30.784
        # 80 min diff. ( ( ( 24h * 60min ) / 360° ) * 20° )
        # => ignore radiation in this timewindow because of a tree which is hiding the sun
        if azimut > 225 and azimut < 245:
            offset = ( azimut - 225 ) * 80 / 20
            #self.log.info(u"{}".format(offset))
            offset = DateTime(int(now.getMillis()-offset*60*1000))
            #self.log.info(u"{}".format(offset))
        else:
            offset = now
            
        _messuredRadiation = getStableItemState(offset,"WeatherStation_Solar_Power",10)
        _sunSouthRadiation, _sunWestRadiation, _sunDebugInfo = SunRadiation.getSunPowerPerHour(offset,cloudCover,_messuredRadiation)
        effectiveSouthRadiationShortTerm = _sunSouthRadiation / 60.0
        effectiveWestRadiationShortTerm = _sunWestRadiation / 60.0
        self.log.info(u"Gemessen Avg 10 min until {}: {} {}".format(offset,effectiveSouthRadiationShortTerm, effectiveWestRadiationShortTerm))

        #azimut = getItemState("Sun_Azimuth").doubleValue()
        #longTermTimeWindow = 120 if azimut > 225 and azimut < 245 else 30 # in this direction a tree is hiding the sun
        #longTermTimeWindow = 120 if azimut > 228 and azimut < 242 else 30 # in this direction a tree is hiding the sun
        _messuredRadiation = getStableItemState(offset,"WeatherStation_Solar_Power",30)
        _sunSouthRadiation, _sunWestRadiation, _sunDebugInfo = SunRadiation.getSunPowerPerHour(offset,cloudCover,_messuredRadiation)
        effectiveSouthRadiationLongTerm = _sunSouthRadiation / 60.0
        effectiveWestRadiationLongTerm = _sunWestRadiation / 60.0
        self.log.info(u"Gemessen Avg 30 min until {}: {} {}".format(offset,effectiveSouthRadiationLongTerm, effectiveWestRadiationLongTerm))
      
        effectiveSouthRadiationMax = cr.getSunSouthRadiationMax() / 60.0
        effectiveWestRadiationMax = cr.getSunWestRadiationMax() / 60.0
        self.log.info(u"Max: {} {}".format(effectiveSouthRadiationMax, effectiveWestRadiationMax))
      
        currentOutdoorTemperature = cr.getReferenceTemperature()
        currentOutdoorTemperature4 = cr4.getReferenceTemperature()

        fallbackTargetTemperature = hhs.getHeatingState("FF_Livingroom").getHeatingTargetTemperature()
      
        for room in Heating.getRooms():
            rs = cr.getRoomState(room.getName())
            
            targetRoomTemperature = fallbackTargetTemperature if room.getHeatingVolume() == None else hhs.getHeatingState(room.getName()).getHeatingTargetTemperature()
            
            for transition in room.transitions:
                if not isinstance(transition,Window) or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
                    continue
                  
                currentRoomTemperature = rs.getCurrentTemperature()

                effectiveRadiationShortTerm = effectiveSouthRadiationShortTerm if transition.getDirection() == 'south' else effectiveWestRadiationShortTerm
                effectiveRadiationLongTerm = effectiveSouthRadiationLongTerm if transition.getDirection() == 'south' else effectiveWestRadiationLongTerm
                effectiveRadiationMax = effectiveSouthRadiationMax if transition.getDirection() == 'south' else effectiveWestRadiationMax

                if getItemState(transition.getSunProtectionItem()) == ON:
                    radiationTooLow = (effectiveRadiationShortTerm < 2.0 and ( effectiveRadiationMax < 2.0 or effectiveRadiationLongTerm < 2.0 ))
                    
                    roomTemperatureTooCold = currentRoomTemperature < targetRoomTemperature - 0.7
                    
                    radiationNotWayTooHigh = (effectiveRadiationShortTerm < 12.0 and ( effectiveRadiationMax < 12.0 or effectiveRadiationLongTerm < 12.0 ))
                    itsGettingColderAndRoomIsNotWarmEnoughForIt = ( \
                        currentOutdoorTemperature < targetRoomTemperature - 0.2 \
                        and \
                        currentOutdoorTemperature4 < targetRoomTemperature - 0.2 \
                        and \
                        currentRoomTemperature < targetRoomTemperature + ( 1.8 if radiationNotWayTooHigh else 0.8 ) \
                    )
                  
                    if radiationTooLow or roomTemperatureTooCold or itsGettingColderAndRoomIsNotWarmEnoughForIt:
                        if itemLastUpdateOlderThen(transition.getSunProtectionItem(), getNow().minusMinutes(60)):
                            postUpdate(transition.getSunProtectionItem(), OFF )
                            self.log.info(u"DEBUG: SP switching off {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                        else:
                            self.log.warn(u"DEBUG: SP skipped off {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                else:
                    radiationTooHigh = effectiveRadiationShortTerm > 5.0
                    
                    roomTemperatureTooWarm = currentRoomTemperature > targetRoomTemperature - 0.5
                    
                    radiationWayTooHigh = effectiveRadiationShortTerm > 15.0
                    itsGettingWarmerOrRoomIsWayTooWarm = ( \
                        currentOutdoorTemperature > targetRoomTemperature \
                        or \
                        currentOutdoorTemperature4 > targetRoomTemperature \
                        or \
                        currentRoomTemperature > targetRoomTemperature + ( 2.0 if not radiationWayTooHigh else 1.0 ) \
                    )
                    
                    #self.log.info(u"{} {}".format(room.getName(),effectiveRadiationShortTerm))
                    #self.log.info(u"{} {}".format(radiationTooHigh,roomTemperatureTooWarm))
                    #self.log.info(u"{} {}".format(currentRoomTemperature,targetRoomTemperature))
                    #self.log.info(u"{} {}".format(currentOutdoorTemperature,currentOutdoorTemperature4))
                    
                    if radiationTooHigh and roomTemperatureTooWarm and itsGettingWarmerOrRoomIsWayTooWarm:
                        if itemLastUpdateOlderThen(transition.getSunProtectionItem(), getNow().minusMinutes(30)):
                            postUpdate(transition.getSunProtectionItem(), ON )
                            self.log.info(u"DEBUG: SP switching on {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                        else:
                            self.log.warn(u"DEBUG: SP skipped on {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))

        #effectiveSouthRadiation = cr.getSunSouthRadiation() / 60.0
        #effectiveWestRadiation = cr.getSunWestRadiation() / 60.0

        #currentOutdoorTemperature = cr.getReferenceTemperature()

        #fallbackTargetTemperature = hhs.getHeatingState("FF_Livingroom").getHeatingTargetTemperature()
      
        #for room in Heating.getRooms():
        #    rs = cr.getRoomState(room.getName())
            
        #    targetRoomTemperature = fallbackTargetTemperature if room.getHeatingVolume() == None else hhs.getHeatingState(room.getName()).getHeatingTargetTemperature()
            
        #    for transition in room.transitions:
        #        if not isinstance(transition,Window) or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
        #            continue
                  
        #        currentRoomTemperature = rs.getCurrentTemperature()

        #        effectiveRadiation = effectiveSouthRadiation if transition.getDirection() == 'south' else effectiveWestRadiation

        #        if getItemState(transition.getSunProtectionItem()) == ON:
        #            targetRoomTemperature = targetRoomTemperature - 0.6
                   
        #            if effectiveRadiation < 3.7 or currentRoomTemperature < targetRoomTemperature or currentOutdoorTemperature < targetRoomTemperature:
        #                #postUpdate(transition.getSunProtectionItem(), OFF )
        #                self.log.info(u"DEBUG: SP switching off {} {} {} {} {}".format(room.getName(),effectiveRadiation,currentRoomTemperature,currentOutdoorTemperature,targetRoomTemperature))
        #            #else: 
        #            #    self.log.info(u"SP still needed")
        #        else:
        #            targetRoomTemperature = targetRoomTemperature - 0.5

        #            if effectiveRadiation > 3.8 and currentRoomTemperature > targetRoomTemperature and currentOutdoorTemperature > targetRoomTemperature:
        #                #postUpdate(transition.getSunProtectionItem(), ON )
        #                self.log.info(u"DEBUG: SP switching on {} {} {} {} {}".format(room.getName(),effectiveRadiation,currentRoomTemperature,currentOutdoorTemperature,targetRoomTemperature))
        #        #else:
        #        #   self.log.info(u"SP not needed")

    def controlHeating( self, now, currentOperatingMode, isHeatingRequested ):

        # 0 - Abschalten
        # 1 - Nur WW
        # 2 - Heizen mit WW
        # 3 - Reduziert
        # 4 - Normal
        
        if self.activeHeatingOperatingMode == -1:
            self.activeHeatingOperatingMode = currentOperatingMode
        
        forceRetry = self.activeHeatingOperatingMode != currentOperatingMode
        forceRetryMsg = u" • RETRY {} {}".format(self.activeHeatingOperatingMode,currentOperatingMode) if forceRetry else u""
        delayedMsg = u""
        
        currentOperatingModeChange = getItemLastChange("Heating_Operating_Mode")
        lastChangeBeforeInMinutes = int( math.floor( ( now.getMillis() - currentOperatingModeChange.getMillis() ) / 1000.0 / 60.0 ) )
        lastHeatingChangeFormatted = OFFSET_FORMATTER.print(currentOperatingModeChange)
        lastChangeBeforeFormatted = lastChangeBeforeInMinutes if lastChangeBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastChangeBeforeInMinutes, 60));
        
        self.log.info(u"Active  : {} since {} • {} min. ago".format(Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) ),lastHeatingChangeFormatted,lastChangeBeforeFormatted) )
        
        # Nur WW
        if currentOperatingMode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if isHeatingRequested:
                isRunningLongEnough = itemLastChangeOlderThen("Heating_Operating_Mode", now.minusMinutes(Heating.MIN_ONLY_WW_TIME))
                
                if forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode", self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.MIN_ONLY_WW_TIME - int( round( ( now.getMillis() - currentOperatingModeChange.getMillis() ) / 1000.0 / 60.0 ) )
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Heizen mit WW{}{}".format(delayedMsg,forceRetryMsg))

        # Heizen mit WW
        elif currentOperatingMode == 2:
            currentPowerState = getItemState("Heating_Power").intValue()
            
            if currentPowerState == 0 and lastChangeBeforeInMinutes < 1:
                self.log.info(u"Delayed : Give the heating system more time to react")
                return
        
            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not isHeatingRequested:
                isRunningLongEnough = itemLastChangeOlderThen("Heating_Operating_Mode",now.minusMinutes(Heating.MIN_HEATING_TIME))
                
                if currentPowerState == 0 or forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 1
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.MIN_HEATING_TIME - int( round( ( now.getMillis() - currentOperatingModeChange.getMillis() ) / 1000.0 / 60.0 ) )
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Nur WW{}{}".format(delayedMsg,forceRetryMsg))
                  
            # Brenner läuft nicht
            elif currentPowerState == 0:
                forceReducedMsg = None
                
                # TODO maybe check Heating_Temperature_Wather_Storage if the temerature is increasing => hint that water heating is active
                # TODO also if Heating_Power is going from 0 to 65 and one minute later from 65 to 0 is a hint for a unsuccessful start
                
                # No burner starts since a while
                if itemLastChangeOlderThen("Heating_Power",now.minusMinutes(5)) and itemLastChangeOlderThen("Heating_Operating_Mode",now.minusMinutes(5)):
                    forceReducedMsg = u" • No burner starts"
                else:
                    burnerStarts = self.getBurnerStarts(now)
                
                    if burnerStarts > 1:
                        forceReducedMsg = u" • Too many burner starts"
                        
                if forceReducedMsg != None:
                    self.activeHeatingOperatingMode = 3
                   
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"Switch  : Reduziert{}{}".format(forceReducedMsg,forceRetryMsg))
        
        # Reduziert
        elif currentOperatingMode == 3:
            # Wenn Temperatur seit XX min OK ist und der brenner sowieso aus ist kann gleich in 'Nur WW' gewechselt werden
            if not isHeatingRequested:
                self.activeHeatingOperatingMode = 1
                sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                self.log.info(u"Switch  : Nur WW because heating is not needed anymore{}".format(forceRetryMsg))
            else:
                lastReducedRuntime = self.getLastReductionTime( currentOperatingModeChange )
                if lastReducedRuntime > 0:
                    targetReducedTime = int( round(lastReducedRuntime * 2.0 / 1000.0 / 60.0, 0) )
                    if targetReducedTime > Heating.MAX_REDUCTION_TIME:
                        targetReducedTime = Heating.MAX_REDUCTION_TIME
                    elif targetReducedTime < Heating.MIN_REDUCED_TIME:
                        # SHOULD NEVER HAPPEN !!!
                        self.log.error(u"MIN_REDUCED_TIME less then allowed. Was {}".format(targetReducedTime))
                        targetReducedTime = Heating.MIN_REDUCED_TIME
                else:
                    targetReducedTime = Heating.MIN_REDUCED_TIME
                                
                #self.log.info(u"E {}".format(targetReducedTime))
                    
                # Dauernd reduziert läuft seit mindestens XX Minuten
                if forceRetry or itemLastChangeOlderThen("Heating_Operating_Mode",now.minusMinutes(targetReducedTime) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                elif not forceRetry:
                    runtimeToGo = targetReducedTime - int( round( ( now.getMillis() - currentOperatingModeChange.getMillis() ) / 1000.0 / 60.0 ) )
                    delayedMsg = u" in {} min.".format(runtimeToGo)
                    
                self.log.info(u"Switch  : Heizen mit WW{}{}".format(delayedMsg,forceRetryMsg))
                
    def getBurnerStarts( self, now ):
        # max 5 min.
        minTimestamp = getHistoricItemEntry("Heating_Operating_Mode",now).getTimestamp().getTime()
        _minTimestamp = now.minusMinutes(5).getMillis()
        if minTimestamp < _minTimestamp:
            minTimestamp = _minTimestamp

        currentTime = now
        lastItemEntry = None
        burnerStarts = 0
        
        # check for new burner starts during this time periode
        # "Heating_Burner_Starts" is not useable because of wather heating
        while currentTime.getMillis() > minTimestamp:
            currentItemEntry = getHistoricItemEntry("Heating_Power", currentTime)
            if lastItemEntry is not None:
                currentHeating = ( currentItemEntry.getState().doubleValue() != 0.0 )
                lastHeating = ( lastItemEntry.getState().doubleValue() != 0.0 )
                
                if currentHeating != lastHeating:
                    burnerStarts = burnerStarts + 1
            
            currentTime = DateTime( currentItemEntry.getTimestamp().getTime() - 1 )
            lastItemEntry = currentItemEntry
            
        return burnerStarts
    
    def getLastReductionTime( self, currentOperatingModeUpdate ):
        lastOperatingMode = getHistoricItemEntry("Heating_Operating_Mode",currentOperatingModeUpdate.minusSeconds(1))
        #self.log.info(u"A {}".format(lastOperatingMode.getState().intValue()))
        
        # last mode was "Heizen mit WW"
        if lastOperatingMode.getState().intValue() == 2:
            lastOperatingModeUpdate = DateTime( lastOperatingMode.getTimestamp().getTime() )
            lastHeatingTime = currentOperatingModeUpdate.getMillis() - lastOperatingModeUpdate.getMillis()
            #self.log.info(u"B {}".format(lastHeatingTime))

            # last mode was running less then MIN_HEATING_TIME
            if lastHeatingTime < Heating.MIN_HEATING_TIME * 60 * 1000:
                # mode before was "Reduziert"
                previousOperatingMode = getHistoricItemEntry("Heating_Operating_Mode",lastOperatingModeUpdate.minusSeconds(1))
                #self.log.info(u"C {}".format(previousOperatingMode.getState().intValue()))

                if previousOperatingMode.getState().intValue() == 3:
                    # letzt calculate last "reduziert" runtime and increase it by 2
                    previousOperatingModeUpdate = DateTime( previousOperatingMode.getTimestamp().getTime() ) 
                    lastReducedRuntime = lastOperatingModeUpdate.getMillis() - previousOperatingModeUpdate.getMillis()
                    
                    return lastReducedRuntime
        return 0  
                                                
             
