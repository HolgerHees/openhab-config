import math 
from java.time import ZonedDateTime  
from java.time.format import DateTimeFormatter
from java.time.temporal import ChronoUnit

from shared.triggers import CronTrigger, ItemStateChangeTrigger
from shared.helper import rule, getHistoricItemEntry, getItemState, getItemLastChange, getItemLastUpdate, sendCommand, sendCommandIfChanged, postUpdate, postUpdateIfChanged, itemLastUpdateOlderThen, itemLastChangeOlderThen, getStableItemState, getMinItemState, startTimer
from shared.actions import Transformation
from custom.heating.heating import Heating
from custom.heating.house import ThermalStorageType, ThermalBridgeType, Wall, Door, Window, Room
from custom.suncalculation import SunRadiation
from custom.sunprotection import SunProtectionHelper
from custom.weather import WeatherHelper


OFFSET_FORMATTER = DateTimeFormatter.ofPattern("HH:mm")

#postUpdate("pGF_Utilityroom_Heating_Demand",OFF)
#postUpdate("pGF_Guesttoilet_Heating_Demand",OFF)
#postUpdate("pGF_Livingroom_Heating_Demand",OFF)
#postUpdate("pGF_Workroom_Heating_Demand",OFF)
#postUpdate("pGF_Corridor_Heating_Demand",OFF)
#postUpdate("pFF_Corridor_Heating_Demand",OFF)
#postUpdate("pFF_Fitnessroom_Heating_Demand",OFF)
#postUpdate("pFF_Makeuproom_Heating_Demand",OFF)
#postUpdate("pFF_Bedroom_Heating_Demand",OFF)
#postUpdate("pFF_Bathroom_Heating_Demand",OFF)

Heating.cloudCoverFC8Item = "pOutdoor_Weather_Forecast_Cloud_Cover_8h"
Heating.cloudCoverFC4Item = "pOutdoor_Weather_Forecast_Cloud_Cover_4h"
Heating.cloudCoverItem = "pOutdoor_Weather_Current_Cloud_Cover"

Heating.temperatureGardenFC8Item = "pOutdoor_Weather_Forecast_Temperature_8h"
Heating.temperatureGardenFC4Item = "pOutdoor_Weather_Forecast_Temperature_4h"

Heating.ventilationFilterRuntimeItem = "pGF_Utilityroom_Ventilation_Filter_Runtime"

Heating.ventilationLevelItem = "pGF_Utilityroom_Ventilation_Outgoing"
Heating.ventilationOutgoingTemperatureItem = "pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"
Heating.ventilationIncommingTemperatureItem = "pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"

Heating.heatingPower = "pGF_Utilityroom_Heating_Power"
Heating.heatingCircuitPumpSpeedItem = "pGF_Utilityroom_Heating_Circuit_Pump_Speed"
Heating.heatingTemperaturePipeOutItem = "pGF_Utilityroom_Heating_Temperature_Pipe_Out"
Heating.heatingTemperaturePipeInItem = "pGF_Utilityroom_Heating_Temperature_Pipe_In"

Heating.heatingModeItem = "pOther_Manual_State_Heating"
Heating.holidayStatusItem = "pOther_Manual_State_Holiday"
Heating.precenceStatusItem = "pOther_Presence_State"

Heating.forcedStatesItem = "pGF_Utilityroom_Heating_Force_States"
 
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

rooms = [
    Room(
        name='lGF_Garage',
        volume=54.0702 * _atticFloorHeight / 2.0,
        walls=[
            Wall(direction='floor', area=27.456025, type=_atticFloor),
            Wall(direction='ceiling', area=27.456025, type=_firstSlopingCeiling),
            Wall(direction='west', area=5.319, type=_outer22Wall),
            Wall(direction='north', area=4.18, type=_outer36Wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=3.509, type=_outer36Wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.5, type=_outer36Wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.85, type=_outer36Wall,bound="lGF_Guesttoilet"),
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
        name='lGF_Guesttoilet',
        additionalRadiator=True,
        heatingVolume=29.63,
        volume=4.92445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=6.29125, type=_groundFloor),
            Wall(direction='ceiling', area=6.29125, type=_groundCeiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.4949, type=_inner17Wall, bound="lGF_Corridor"),
            Wall(direction='east', area=9.14345, type=_outer36Wall),
            Wall(direction='south', area=5.0225, type=_garageWall, bound="lGF_Garage")
        ],
        transitions=[
            Window(direction='east', area=1.045, type=_outerWindow, contactItem='pGF_Guesttoilet_Openingcontact_Window_State', shutterItem='pGF_Guesttoilet_Shutter_Control', shutterArea=0.1292)
        ]
    ),
    Room(
        name='lGF_Utilityroom',
        # TODO check
        #heatingVolume=27.04,
        volume=7.816325 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=8.9875, type=_groundFloor),
            Wall(direction='ceiling', area=8.9875, type=_groundCeiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.39615, type=_inner17Wall, bound="lGF_Corridor"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="lGF_Guesttoilet"),
            Wall(direction='south', area=5.294375, type=_garageWall, bound="lGF_Garage")
        ],
        transitions=[
            Door(direction='south', area=1.880625, type=_utilityroomGarageDoor, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Boxroom',
        volume=4.72615 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=5.734025, type=_groundFloor),
            Wall(direction='ceiling', area=5.734025, type=_groundCeiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='west', area=8.5388, type=_inner17Wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=4.57765, type=_inner17Wall, bound="lGF_Livingroom"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="lGF_Utilityroom"),
            Wall(direction='south', area=4.57765, type=_garageWall, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Livingroom',
        heatingVolume=84.20 + 84.20 + 49.90,
        volume=37.9957 * _firstFloorHeight + 10.7406 * _firstFloorHeight,
        walls=[
            # Kitchen
            Wall(direction='floor', area=12.999225, type=_groundFloor),
            Wall(direction='ceiling', area=12.999225, type=_groundCeiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='east', area=8.789925, type=_inner17Wall, bound="lGF_Boxroom"),
            Wall(direction='south', area=4.6781, type=_garageWall, bound="lGF_Garage"),
            Wall(direction='south', area=5.453, type=_outer36Wall),
            Wall(direction='west', area=8.069575, type=_outer36Wall),
            #Wall(direction='north', area=4.57765, type=_inner17Wall),

            # Livingroom
            Wall(direction='floor', area=42.4732875, type=_groundFloor),
            Wall(direction='ceiling', area=16.3125, type=_groundCeiling, bound="lFF_Bedroom"),
            Wall(direction='ceiling', area=17.07625, type=_groundCeiling, bound="lFF_Makeuproom"),
            Wall(direction='ceiling', area=9.0845375, type=_groundCeiling, bound="lFF_Corridor"),
            Wall(direction='south', area=3.393775, type=_outer36Wall),
            Wall(direction='west', area=9.292675, type=_outer36Wall),
            Wall(direction='north', area=18.92765, type=_outer36Wall),
            Wall(direction='east', area=7.34725, type=_inner17Wall, bound="lGF_Corridor"),
            Wall(direction='east', area=10.339175, type=_inner17Wall, bound="lGF_Workroom"),
            Wall(direction='south', area=6.177675, type=_inner17Wall, bound="lGF_Boxroom")
        ],
        transitions=[
            Window(direction='west', area=2.2, type=_outerWindow, contactItem='pGF_Kitchen_Openingcontact_Window_State', shutterItem='pGF_Kitchen_Shutter_Control', shutterArea=0.2992, radiationArea=0.645*1.01*2.0, sunProtectionItem="pOther_Automatic_State_Sunprotection_Livingroom"),
            Window(direction='west', area=5.8232, type=_outerWindow, contactItem='pGF_Livingroom_Openingcontact_Window_Terrace_State', shutterItem='pGF_Livingroom_Shutter_Terrace_Control', shutterArea=0.4267, radiationArea=0.625*2.13*3.0),
            Window(direction='west', area=4.0832, type=_outerWindow, contactItem='pGF_Livingroom_Openingcontact_Window_Couch_State', shutterItem='pGF_Livingroom_Shutter_Couch_Control', shutterArea=0.2992, radiationArea=0.625*2.13*2.0)
        ]
    ),
    Room(
        name='lGF_Workroom',
        heatingVolume=60.19,
        volume=11.53445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=13.5891, type=_groundFloor),
            Wall(direction='ceiling', area=13.5891, type=_groundCeiling, bound="lFF_Fitnessroom"),
            Wall(direction='west', area=10.31765, type=_inner17Wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=10.8486, type=_outer36Wall),
            Wall(direction='east', area=7.9847, type=_outer36Wall),
            Wall(direction='south', area=9.06975, type=_inner17Wall, bound="lGF_Corridor")
        ],
        transitions=[
            Window(direction='east', area=2.07625, type=_outerWindow, contactItem='pGF_Workroom_Openingcontact_Window_State', shutterItem='pGF_Workroom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lGF_Corridor',
        heatingVolume=40.93,
        volume=11.3076 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=12.9843, type=_groundFloor),
            Wall(direction='ceiling', area=2.0524125, type=_groundCeiling, bound="lFF_Corridor"),
            Wall(direction='west', area=7.0746, type=_inner17Wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=9.06975, type=_inner17Wall, bound="lGF_Workroom"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer36Wall),
            Wall(direction='south', area=3.4949, type=_inner17Wall, bound="lGF_Guesttoilet"),
            Wall(direction='south', area=4.04725, type=_inner17Wall, bound="lGF_Utilityroom")
        ],
        transitions=[
            # count the main door only 50%, because other 50% is counted on upper floor
            Door(direction='east', area=4.6632/2.0, type=_mainDoor, contactItem='pGF_Corridor_Openingcontact_Door_State'),
            # count 50% of the sloping window from upper floor
            Window(direction='east', area=0.7676/2.0, type=_firstSlopingWindow)
        ]
    ),
    Room(
        name='lFF_Corridor',
        heatingVolume=38.45,
        volume=18.1926 * _secondFloorHeight - 4.3968,
        walls=[
            Wall(direction='floor', area=4.61578125, type=_firstFloor, bound="lGF_Livingroom"),
            Wall(direction='floor', area=4.61578125, type=_firstFloor, bound="lGF_Corridor"),
            Wall(direction='ceiling', area=14.1436125, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=7.77045, type=_inner11Wall, bound="lFF_Bedroom"),
            Wall(direction='north', area=8.51865, type=_inner17Wall, bound="lFF_Fitnessroom"),
            Wall(direction='north', area=1.69615, type=_inner17Wall, bound="lFF_Makeuproom"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer36Wall),
            Wall(direction='east', area=8.026, type=_firstSlopingCeiling),
            Wall(direction='south', area=8.51865, type=_inner17Wall, bound="lFF_Bathroom"),
            Wall(direction='south', area=1.69615, type=_inner17Wall, bound="lFF_Bedroom"), # Dressingroom
        ],
        transitions=[
            # count 50% of the main door from lower floor
            Door(direction='east', area=4.6632/2.0, type=_mainDoor, contactItem='pGF_Corridor_Openingcontact_Door_State'),
            # count the sloping window only 50%, because other 50% is counted on lower floor
            Window(direction='east', area=0.7676/2.0, type=_firstSlopingWindow)
        ]
    ),
    Room(
        name='lFF_Fitnessroom',
        heatingVolume=39.61,
        volume=13.036325 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=4.0, type=_firstFloor, bound="lGF_Livingroom"),
            Wall(direction='floor', area=12.626875, type=_firstFloor, bound="lGF_Workroom"),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner11Wall, bound="lFF_Makeuproom"),
            Wall(direction='north', area=8.1533, type=_outer36Wall),
            Wall(direction='east', area=3.595, type=_outer36Wall),
            Wall(direction='east', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='south', area=8.51865, type=_inner17Wall, bound="lFF_Corridor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='pFF_Fitnessroom_Openingcontact_Window_State', shutterItem='pFF_Fitnessroom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lFF_Makeuproom',
        heatingVolume=41.32,
        volume=14.99575 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=17.07625, type=_firstFloor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=10.7760125, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=3.595, type=_outer36Wall),
            Wall(direction='west', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='north', area=8.5008, type=_outer36Wall),
            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="lFF_Fitnessroom"),
            Wall(direction='south', area=7.17, type=_inner17Wall, bound="lFF_Bedroom"),
            Wall(direction='south', area=1.69615, type=_inner17Wall, bound="lFF_Corridor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='pFF_Makeuproom_Openingcontact_Window_State', shutterItem='pFF_Makeuproom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lFF_Bedroom',
        heatingVolume=35.87 + 39.33,
        volume=(14.3929 * _secondFloorHeight) + (14.88435 * _secondFloorHeight - 4.6016),
        walls=[
            # Bedroom
            Wall(direction='floor', area=16.3125, type=_firstFloor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=16.3125, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=5.9851, type=_outer36Wall),
            Wall(direction='north', area=12.51, type=_inner17Wall, bound="lFF_Makeuproom"),
            Wall(direction='east', area=8.03455, type=_inner11Wall, bound="lFF_Corridor"),
            Wall(direction='south', area=3.28735, type=_outer36Wall),
            Wall(direction='south', area=0.5, type=_firstSlopingCeiling),

            # Dressingroom
            Wall(direction='floor', area=16.660625, type=_firstFloor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=10.40850625, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=3.5075, type=_outer36Wall),
            Wall(direction='west', area=8.9792, type=_firstSlopingCeiling),
            Wall(direction='north', area=3.63485, type=_inner17Wall, bound="lFF_Corridor"),
            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="lFF_Bathroom"),
            Wall(direction='south', area=9.0333, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='west', area=3.1375, type=_outerWindow, contactItem='pFF_Bedroom_Openingcontact_Window_State', shutterItem='pFF_Bedroom_Shutter_Control', shutterArea=0.4267, radiationArea=0.615*1.00*3.0, sunProtectionItem="pOther_Automatic_State_Sunprotection_Bedroom"),
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='pFF_Dressingroom_Openingcontact_Window_State', shutterItem='pFF_Dressingroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Dressingroom")
#        ]
        ]
    ),
#    Room(
#        name='lFF_Dressingroom',
#        heatingVolume=57.58,
#        volume=14.88435 * _secondFloorHeight - 4.6016,
#        walls=[
#            Wall(direction='floor', area=16.660625, type=_firstFloor, bound="lGF_Livingroom"),
#            Wall(direction='ceiling', area=10.40850625, type=_firstCeiling, bound="lFF_Attic"),
#            Wall(direction='west', area=3.5075, type=_outer36Wall),
#            Wall(direction='west', area=8.9792, type=_firstSlopingCeiling),
#            Wall(direction='north', area=3.63485, type=_inner17Wall, bound="lFF_Corridor"),
#            Wall(direction='east', area=9.9941, type=_inner11Wall, bound="lFF_Bathroom"),
#            Wall(direction='south', area=9.0333, type=_outer36Wall)
#        ],
#        transitions=[
#            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='pFF_Dressingroom_Openingcontact_Window_State', shutterItem='pFF_Dressingroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Dressingroom")
#        ]
#    ),
    Room(
        name='lFF_Bathroom',
        additionalRadiator=True,
        heatingVolume=35.31,
        volume=12.51273 * _secondFloorHeight - 2.5884,
        walls=[
            Wall(direction='floor', area=5.482375, type=_firstFloor, bound="lGF_Guesttoilet"),
            Wall(direction='floor', area=8.9875, type=_firstFloor, bound="lGF_Utilityroom"),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling, bound="lFF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner11Wall, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='north', area=7.4633, type=_inner17Wall, bound="lFF_Corridor"),
            Wall(direction='east', area=5.033, type=_outer36Wall),
            Wall(direction='east', area=5.1768, type=_firstSlopingCeiling),
            Wall(direction='south', area=7.63045, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='pFF_Bathroom_Openingcontact_Window_State', shutterItem='pFF_Bathroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Bathroom")
        ]
    ),
    Room(
        name='lFF_Attic',
        volume=54.0702 * _atticFloorHeight / 2.0,
        walls=[
            Wall(direction='floor', area=59.871875, type=_atticFloor, bound="lFF_Bedroom" ),
            Wall(direction='west', area=9.9941, type=_outer36Wall),
            Wall(direction='west', area=49.9872093014803, type=_firstSlopingCeiling),
            Wall(direction='north', area=5.91675, type=_outer36Wall),
            Wall(direction='east', area=49.9872093014803, type=_firstSlopingCeiling),
            Wall(direction='south', area=5.01995, type=_outer36Wall)
        ],
        transitions=[
            Window(direction='east', area=0.7676, type=_firstSlopingWindow),
            Window(direction='south', area=0.7676, type=_outerWindow, contactItem='pFF_Attic_Openingcontact_Window_State', shutterItem='pFF_Attic_Shutter_Control', shutterArea=0.19295, radiationArea=0.72*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Attic")
        ]
    )
]

Heating.init(rooms)

controllableRooms = {
  'lGF_Livingroom': True,
  'lGF_Corridor': True,
  'lGF_Workroom': True,
  'lGF_Guesttoilet': True,
  'lFF_Corridor': True,
  'lFF_Fitnessroom': True,
  'lFF_Makeuproom': True,
  'lFF_Bedroom': True,
  'lFF_Bathroom': True
}
maintenanceMode = {}

#@rule()
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

#@rule()
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

@rule()
class HeatingControlErrorMessage:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */5 * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Common_Fault")
        ]

    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent":
            if itemLastUpdateOlderThen("pGF_Utilityroom_Heating_Common_Fault", ZonedDateTime.now().minusMinutes(10)):
                postUpdateIfChanged("eOther_Error_Heating_Message", u"Keine Updates mehr seit mehr als 10 Minuten")
                return
        elif getItemState("pGF_Utilityroom_Heating_Common_Fault").intValue() > 0:
            postUpdateIfChanged("eOther_Error_Heating_Message", Transformation.transform("MAP", "heating_state_de.map", getItemState("pGF_Utilityroom_Heating_Common_Fault").toString() ))
            return

        postUpdateIfChanged("eOther_Error_Heating_Message", "")

@rule()
class HeatingControlVentile:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */10 1 ? * MON,FRI"),
            CronTrigger("0 0 2 ? * MON,FRI")
        ]

    # refresh heating ventile twice per week
    def execute(self, module, input):
        now = ZonedDateTime.now()
        for room in filter( lambda room: room.getHeatingVolume() != None and room.getName() in controllableRooms,Heating.getRooms()):
            circuiteItem = Heating.getHeatingCircuitItem(room)
            maintainanceModeActive = room in maintenanceMode

            if maintainanceModeActive or itemLastChangeOlderThen(circuiteItem,now.minusHours(24)):
                hour = now.getHour()
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

@rule()
class HeatingControlMain:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Auto_Mode"),
            CronTrigger("15 * * * * ?")
        ]
        self.activeHeatingOperatingMode = -1
        self.activeReducedTimeInMinutes = -1

        #self.test()

    def execute(self, module, input):
        self.log.info(u"--------: >>>" )

        if input['event'].getType() != "TimerEvent" and input['event'].getItemName() == 'pGF_Utilityroom_Heating_Auto_Mode':
            self.activeHeatingOperatingMode = -1
            self.activeReducedTimeInMinutes = -1

        now = ZonedDateTime.now()
        autoModeEnabled = getItemState("pGF_Utilityroom_Heating_Auto_Mode").intValue() == 1

        currentOperatingModeChange = getItemLastChange("pGF_Utilityroom_Heating_Operating_Mode")
        currentOperatingMode = getItemState("pGF_Utilityroom_Heating_Operating_Mode").intValue()

        currentHeatingDemand = getItemState("pGF_Utilityroom_Heating_Demand")

        heating = Heating(self.log, WeatherHelper.getTemperatureItemName())

        messuredRadiationShortTerm = WeatherHelper.getSolarPowerStableItemState(now, 10)
        messuredRadiationLongTerm = WeatherHelper.getSolarPowerStableItemState(now, 30)
        messuredLightLevelShortTerm = WeatherHelper.getLightLevelStableItemState(now, 30)
        messuredLightLevelLongTerm = WeatherHelper.getLightLevelStableItemState(now, 60)

        cr, cr4, cr8, hhs = heating.calculate(currentHeatingDemand == ON, messuredRadiationShortTerm)    

        # **** DEBUG ****
        heating.logCoolingAndRadiations("FC8     ",cr8)
        heating.logCoolingAndRadiations("FC4     ",cr4)
        heating.logCoolingAndRadiations("Current ",cr, messuredRadiationLongTerm, messuredLightLevelLongTerm)
        
        heating.logHeatingStates(cr, hhs )
        # ***************

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
            # forced open circuits are needed during burner startup phase to avoid burner start/stops
            forcedOpenCircuitOnStart = ( # nur WW or Reduziert
                                         # Forced circuits should stay open when burner is inactive
                                         currentOperatingMode != 2
                                         or 
                                         # Heizen mit WW
                                         # Forced circuits should stay open until burner is active for 5 min.
                                         (currentOperatingMode == 2 and now.minusMinutes(5).isBefore(currentOperatingModeChange))
                                       )
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
                    if heatingRequested and ( rhs.getHeatingDemandTime() > 0 or forcedOpenCircuitOnStart ):
                        #self.log.info("ON")
                        if sendCommandIfChanged(circuitItem,ON):
                            circuitLastChange = now
                        else:
                            circuitLastChange = getItemLastChange(circuitItem)
                            
                        if lastCircuitOpenedAt == None or lastCircuitOpenedAt.isBefore(circuitLastChange):
                            lastCircuitOpenedAt = circuitLastChange                            
                    else:
                        #self.log.info("OFF")
                        sendCommandIfChanged(circuitItem,OFF)
                        
                    # wall radiator
                    if room.hasAdditionalRadiator():
                        # additional radiator should only be enabled in case of CF heating
                        if heatingRequested and ( rhs.getForcedInfo() == 'CF' or forcedOpenCircuitOnStart ):
                            sendCommandIfChanged(Heating.getHeatingHKItem(room),ON)
                        else:
                            sendCommandIfChanged(Heating.getHeatingHKItem(room),OFF)
            # *************************************************
            
            self.log.info(u"        : ---" )
            
            # a heating ciruit was opened less then 5 minutes ago.
            # delay heating request to give circuit some time to open
            if currentHeatingDemand == OFF and lastCircuitOpenedAt != None and now.minusMinutes(5).isBefore(lastCircuitOpenedAt):
                #self.log.info(u"{}".format(lastCircuitOpenedAt))
                openedBeforeInMinutes = ChronoUnit.MINUTES.between(lastCircuitOpenedAt,now)
                self.log.info(u"Demand  : DELAYED • circuit was opened {} min. ago".format(openedBeforeInMinutes))
            else:
                heatingDemand = ON if heatingRequested else OFF
                postUpdateIfChanged("pGF_Utilityroom_Heating_Demand", heatingDemand )
            
                endMsg = u" • {} min. to go".format(Heating.visualizeHeatingDemandTime(longestRuntime)) if longestRuntime > 0 else u""
                lastHeatingDemandChange = getItemLastUpdate("pGF_Utilityroom_Heating_Demand") # can be "getItemLastUpdate" datetime, because it is changed only from heating rule
                lastChangeBeforeInMinutes = ChronoUnit.MINUTES.between(lastHeatingDemandChange,now)
                lastHeatingChangeFormatted = OFFSET_FORMATTER.format(lastHeatingDemandChange)
                lastChangeBeforeFormatted = lastChangeBeforeInMinutes if lastChangeBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastChangeBeforeInMinutes, 60));
                self.log.info(u"Demand  : {} since {} • {} min. ago{}".format(heatingDemand, lastHeatingChangeFormatted, lastChangeBeforeFormatted,endMsg) )
                
                self.controlHeating(now,currentOperatingMode,currentOperatingModeChange,heatingRequested)  
        else:
            self.log.info(u"Demand  : SKIPPED • MANUAL MODE ACTIVE")

        self.setSunStates(now,cr,cr4,cr8,hhs, messuredRadiationLongTerm, messuredLightLevelShortTerm, messuredLightLevelLongTerm)
        
        self.log.info(u"--------: <<<" )
   
    def setSunStates(self, now, cr, cr4, cr8, hhs, messuredRadiationLongTerm, messuredLightLevelShortTerm, messuredLightLevelLongTerm):
        cloudCover = cr.getCloudCover()
        
        messuredRadiationShortTerm = cr.getSunRadiation()

        if messuredRadiationLongTerm is None:
            messuredRadiationLongTerm = messuredRadiationShortTerm

        _sunSouthRadiation, _sunWestRadiation, _sunRadiation, _sunDebugInfo = SunRadiation.getSunPowerPerHour(now,cloudCover,messuredRadiationShortTerm)
        effectiveSouthRadiationShortTerm = _sunSouthRadiation / 60.0
        effectiveWestRadiationShortTerm = _sunWestRadiation / 60.0
        #self.log.info(u"Gemessen Avg 10 min until {}: {} {}".format(offset,effectiveSouthRadiationShortTerm, effectiveWestRadiationShortTerm))

        _sunSouthRadiation, _sunWestRadiation, _sunRadiation, _sunDebugInfo = SunRadiation.getSunPowerPerHour(now,cloudCover,messuredRadiationLongTerm)
        effectiveSouthRadiationLongTerm = _sunSouthRadiation / 60.0
        effectiveWestRadiationLongTerm = _sunWestRadiation / 60.0
        #self.log.info(u"Gemessen Avg 30 min until {}: {} {}".format(offset,effectiveSouthRadiationLongTerm, effectiveWestRadiationLongTerm))
      
        effectiveSouthRadiationMax = cr.getSunSouthRadiationMax() / 60.0
        effectiveWestRadiationMax = cr.getSunWestRadiationMax() / 60.0
        #self.log.info(u"Max: {} {}".format(effectiveSouthRadiationMax, effectiveWestRadiationMax))
      
        currentOutdoorTemperature = cr.getReferenceTemperature()
        currentOutdoorTemperature4 = cr4.getReferenceTemperature()
        currentOutdoorTemperature8 = cr8.getReferenceTemperature()

        fallbackTargetTemperature = hhs.getHeatingState("lGF_Livingroom").getHeatingTargetTemperature()
        
        #self.log.info(u"{} {}".format(messuredRadiationShortTerm,messuredRadiationLongTerm))
        
        # terrace radiation
        effectiveRadiationShortTerm = messuredRadiationShortTerm / 60.0
        effectiveRadiationLongTerm = messuredRadiationLongTerm / 60.0
        
        # use same azimut and elevation as heating calculation
        elevation, azimut = SunRadiation._getSunData( now )
        #azimut = getItemState("pOutdoor_Astro_Sun_Azimuth").doubleValue()
        #elevation = getItemState("pOutdoor_Astro_Sun_Elevation").doubleValue()

        #self.log.info(u"{} {} {}".format(azimut,elevation,SunRadiation.getMinElevation(azimut)))
        
        if azimut >= 120 and azimut <= SunRadiation.AZIMUT_NW_LIMIT and elevation >= SunRadiation.getMinElevation(azimut):
            #self.log.info(u"Sun     : {:.1f} W/min ({:.1f} W/min)".format(effectiveRadiationShortTerm,effectiveRadiationLongTerm))
            
            # glare protection during sandra's workdays
            needsSunprotection = azimut >= 180 \
                and messuredLightLevelShortTerm > 15000 and messuredLightLevelLongTerm > 15000 \
                and now.getDayOfWeek().getValue() <= 5 and getItemState("pOther_Presence_Sandra_State") == ON
            if not needsSunprotection:
                # hot stone protection
                needsSunprotection = effectiveRadiationLongTerm > 8.0 and (currentOutdoorTemperature > 26 or currentOutdoorTemperature4 > 26)
                if not needsSunprotection:
                    # hot room protection (only above 18°C)
                    targetRoomTemperature = hhs.getHeatingState("lGF_Livingroom").getHeatingTargetTemperature()
                    currentRoomTemperature = cr.getRoomState("lGF_Livingroom").getCurrentTemperature()
                    needsSunprotection = self.isTooWarm(effectiveRadiationShortTerm, currentOutdoorTemperature, currentOutdoorTemperature4, currentRoomTemperature, targetRoomTemperature )
                        
            if needsSunprotection:
                if postUpdateIfChanged("pOther_Automatic_State_Sunprotection_Terrace", SunProtectionHelper.STATE_TERRACE_CLOSED ):
                    self.log.info(u"DEBUG: SP switching 2 • {} • {} ({}) W/m² • {} ({}) lux".format("Terrace",round(effectiveRadiationShortTerm,1),round(effectiveRadiationLongTerm,1),int(messuredLightLevelShortTerm), int(messuredLightLevelLongTerm)))
            elif getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == 0:
                postUpdate("pOther_Automatic_State_Sunprotection_Terrace", SunProtectionHelper.STATE_TERRACE_MAYBE_CLOSED )
                self.log.info(u"DEBUG: SP switching 1 • {} • {} ({}) W/m² • {} ({}) lux".format("Terrace",round(effectiveRadiationShortTerm,1),round(effectiveRadiationLongTerm,1),int(messuredLightLevelShortTerm), int(messuredLightLevelLongTerm)))
        else:
            #if getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == 2:
            if postUpdateIfChanged("pOther_Automatic_State_Sunprotection_Terrace", SunProtectionHelper.STATE_TERRACE_OPEN ):
                self.log.info(u"DEBUG: SP switching 0 • {}".format("Terrace"))
       
        for room in Heating.getRooms():
            rs = cr.getRoomState(room.getName())
            
            targetRoomTemperature = fallbackTargetTemperature if room.getHeatingVolume() == None else hhs.getHeatingState(room.getName()).getHeatingTargetTemperature()
            
            #weatherAvgTemperature = getItemState("pOutdoor_Weather_Current_Temperature_Avg").floatValue()
            
            for transition in room.transitions:
                if not isinstance(transition,Window) or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
                    continue
                  
                #if currentOutdoorTemperature < targetRoomTemperature and currentOutdoorTemperature4 < targetRoomTemperature and currentOutdoorTemperature8 < targetRoomTemperature:
                #    postUpdateIfChanged(transition.getSunProtectionItem(), OFF )
                #    continue

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
                        if itemLastUpdateOlderThen(transition.getSunProtectionItem(), ZonedDateTime.now().minusMinutes(60)):
                            postUpdate(transition.getSunProtectionItem(), OFF )
                            self.log.info(u"DEBUG: SP switching OFF • {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                        else:
                            self.log.warn(u"DEBUG: SP skipped OFF • {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                else:
                    #self.log.info(u"{} {}".format(room.getName(),effectiveRadiationShortTerm))
                    #self.log.info(u"{} {}".format(radiationTooHigh,roomTemperatureTooWarm))
                    #self.log.info(u"{} {}".format(currentRoomTemperature,targetRoomTemperature))
                    #self.log.info(u"{} {}".format(currentOutdoorTemperature,currentOutdoorTemperature4))

                    tooWarm = self.isTooWarm(effectiveRadiationShortTerm, currentOutdoorTemperature, currentOutdoorTemperature4, currentRoomTemperature, targetRoomTemperature )
                    if tooWarm:
                        if itemLastUpdateOlderThen(transition.getSunProtectionItem(), ZonedDateTime.now().minusMinutes(30)):
                            postUpdate(transition.getSunProtectionItem(), ON )
                            self.log.info(u"DEBUG: SP switching ON • {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))
                        else:
                            self.log.warn(u"DEBUG: SP skipped ON • {} {} {} {}".format(room.getName(),effectiveRadiationShortTerm,effectiveRadiationLongTerm,effectiveRadiationMax))

    def isTooWarm( self, effectiveRadiationShortTerm, currentOutdoorTemperature, currentOutdoorTemperature4, currentRoomTemperature, targetRoomTemperature ):
        if currentOutdoorTemperature <= 18 and currentOutdoorTemperature4 <= 18:
            return False
        
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
        return radiationTooHigh and roomTemperatureTooWarm and itsGettingWarmerOrRoomIsWayTooWarm
                    
    def controlHeating( self, now, currentOperatingMode, currentOperatingModeChange, isHeatingRequested ):

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
        
        lastChangeBeforeInMinutes = ChronoUnit.MINUTES.between(currentOperatingModeChange,now)
        lastHeatingChangeFormatted = OFFSET_FORMATTER.format(currentOperatingModeChange)
        lastChangeBeforeFormatted = lastChangeBeforeInMinutes if lastChangeBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastChangeBeforeInMinutes, 60));
        
        self.log.info(u"Active  : {} since {} • {} min. ago".format(Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) ),lastHeatingChangeFormatted,lastChangeBeforeFormatted) )
        
        # Nur WW
        if currentOperatingMode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if isHeatingRequested:
                isRunningLongEnough = itemLastChangeOlderThen("pGF_Utilityroom_Heating_Operating_Mode", now.minusMinutes(Heating.MIN_ONLY_WW_TIME))
                
                if forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 2
                    sendCommand("pGF_Utilityroom_Heating_Operating_Mode", self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.MIN_ONLY_WW_TIME - lastChangeBeforeInMinutes
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Heizen mit WW{}{}".format(delayedMsg,forceRetryMsg))
            self.activeReducedTimeInMinutes = -1

        # Heizen mit WW
        elif currentOperatingMode == 2:
            currentPowerState = getItemState("pGF_Utilityroom_Heating_Power").intValue()
            
            if currentPowerState == 0 and lastChangeBeforeInMinutes < 1:
                self.log.info(u"Delayed : Give the heating system more time to react")
                return
        
            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not isHeatingRequested:
                isRunningLongEnough = itemLastChangeOlderThen("pGF_Utilityroom_Heating_Operating_Mode",now.minusMinutes(Heating.MIN_HEATING_TIME))
                
                if currentPowerState == 0 or forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 1
                    sendCommand("pGF_Utilityroom_Heating_Operating_Mode",self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.MIN_HEATING_TIME - lastChangeBeforeInMinutes
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Nur WW{}{}".format(delayedMsg,forceRetryMsg))
                self.activeReducedTimeInMinutes = -1
                  
            # Brenner läuft nicht
            elif currentPowerState == 0:
                forceReducedMsg = None

                # No burner starts since 10 minutes
                waiting_time = now.minusMinutes(10)
                if itemLastChangeOlderThen("pGF_Utilityroom_Heating_Power",waiting_time) and itemLastChangeOlderThen("pGF_Utilityroom_Heating_Operating_Mode",waiting_time):
                    forceReducedMsg = u" • No burner starts"
                else:
                    burnderStarts = self.getBurnerStarts(now, 5)
                    isWaterHeating = self.isWaterHeating(now, 5)
                    # if burnder starts during last 5 minutes > 1 and no water heating (diff < 1°)
                    if burnderStarts > 1 and not isWaterHeating:
                        forceReducedMsg = u" • Too many burner starts • Heating system tried to start {} times".format(burnderStarts)
                        
                if forceReducedMsg != None:
                    self.activeReducedTimeInMinutes = Heating.MIN_REDUCED_TIME if self.activeReducedTimeInMinutes == -1 else min( self.activeReducedTimeInMinutes * 2, Heating.MAX_REDUCED_TIME )
                    self.activeHeatingOperatingMode = 3
                   
                    sendCommand("pGF_Utilityroom_Heating_Operating_Mode",self.activeHeatingOperatingMode)
                    self.log.info(u"Switch  : Reduziert{}{}".format(forceReducedMsg,forceRetryMsg))
                elif isWaterHeating:
                    self.log.info(u"Delayed : Heating system heats water")
                else:
                    self.log.info(u"Delayed : Heating system tried to start {} times".format(burnderStarts))

            else:
                if getItemState("pGF_Utilityroom_Heating_Circuit_Pump_Speed").intValue() == 0:
                    if self.isWaterHeating(now, 5):
                        self.log.info(u"Paused  : Heating system heats water")
                    else:
                        if getItemState("pGF_Utilityroom_Heating_Temperature_Boiler_Target").doubleValue() >= 55:
                            self.log.info(u"Paused  : Heating system heats boiler")
                        else:
                            self.log.info(u"Paused  : For unkown reason")
                # reset reduced counter after 5 minutes of heating
                elif self.activeReducedTimeInMinutes != -1 and itemLastChangeOlderThen("pGF_Utilityroom_Heating_Operating_Mode",now.minusMinutes(5)):
                    self.activeReducedTimeInMinutes = -1
         
        # Reduziert
        elif currentOperatingMode == 3:
            # Wenn Temperatur seit XX min OK ist und der brenner sowieso aus ist kann gleich in 'Nur WW' gewechselt werden
            if not isHeatingRequested:
                self.activeHeatingOperatingMode = 1
                sendCommand("pGF_Utilityroom_Heating_Operating_Mode",self.activeHeatingOperatingMode)
                self.log.info(u"Switch  : Nur WW because heating is not needed anymore{}".format(forceRetryMsg))
            else:
                # Dauernd reduziert läuft seit mindestens XX Minuten
                targetReducedTimeInMinutes = self.activeReducedTimeInMinutes if self.activeReducedTimeInMinutes != -1 else Heating.MIN_REDUCED_TIME
                #self.log.info("{}".format(self.activeReducedTimeInMinutes))
                #self.log.info("{}".format(targetReducedTimeInMinutes))
                if forceRetry or itemLastChangeOlderThen("pGF_Utilityroom_Heating_Operating_Mode",now.minusMinutes(targetReducedTimeInMinutes) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("pGF_Utilityroom_Heating_Operating_Mode",self.activeHeatingOperatingMode)
                elif not forceRetry:
                    runtimeToGo = targetReducedTimeInMinutes - lastChangeBeforeInMinutes
                    delayedMsg = u" in {} min.".format(runtimeToGo)
                    
                self.log.info(u"Switch  : Heizen mit WW{}{}".format(delayedMsg,forceRetryMsg))

    def isWaterHeating(self, now, limit_minutes):
        return ( getItemState("pGF_Utilityroom_Heating_Temperature_Water_Storage").doubleValue() - getMinItemState("pGF_Utilityroom_Heating_Temperature_Water_Storage", now.minusMinutes(limit_minutes)).doubleValue() ) >= 1

    def getBurnerStarts( self, now, limit_minutes ):
        minTime = getHistoricItemEntry("pGF_Utilityroom_Heating_Operating_Mode",now).getTimestamp()
        _minTime = now.minusMinutes(limit_minutes)
        if minTime.isBefore(_minTime):
            minTime = _minTime

        currentTime = now
        lastIsHeating = False

        # check for new burner starts during this time periode
        # "pGF_Utilityroom_Heating_Burner_Starts" is not useable because of wather heating
        burnerStarts = 0
        while currentTime.isAfter(minTime):
            currentItemEntry = getHistoricItemEntry("pGF_Utilityroom_Heating_Power", currentTime)
            currentIsHeating = ( currentItemEntry.getState().doubleValue() != 0.0 )

            # count only heating events
            if currentIsHeating != lastIsHeating and currentIsHeating:
                burnerStarts = burnerStarts + 1
            
            currentTime = currentItemEntry.getTimestamp().minusNanos(1)
            lastIsHeating = currentIsHeating
            
        return burnerStarts

    #def test(self):
    #    formatter  = DateTimeFormatter.ISO_OFFSET_DATE_TIME
    #    zdtWithZoneOffset = ZonedDateTime.parse("2024-02-13T07:58:15+01:00", formatter)
    #    zdtInLocalTimeline = zdtWithZoneOffset.withZoneSameInstant(ZoneId.systemDefault())

    #    ref = ZonedDateTime.now()
    #    self.log.info("{} {}".format(ref, zdtInLocalTimeline))
    #    count = self.getBurnerStarts(zdtInLocalTimeline, 5)
    #    self.log.info(str(count))
