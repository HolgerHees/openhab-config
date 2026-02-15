from openhab import rule, Registry, logger
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, ItemCommandTrigger
from openhab.actions import Transformation

from shared.toolbox import ToolboxHelper

from custom.heating.heating import Heating
from custom.heating.house import ThermalStorageType, ThermalBridgeType, Wall, Door, Window, Room
from custom.suncalculation import SunRadiation
from custom.sunprotection import SunProtectionHelper
from custom.weather import WeatherHelper

from datetime import datetime, timedelta

import scope


#postUpdate("pGF_Utilityroom_Heating_Demand",scope.OFF)
#postUpdate("pGF_Guesttoilet_Heating_Demand",scope.OFF)
#postUpdate("pGF_Livingroom_Heating_Demand",scope.OFF)
#postUpdate("pGF_Workroom_Heating_Demand",scope.OFF)
#postUpdate("pGF_Corridor_Heating_Demand",scope.OFF)
#postUpdate("pFF_Corridor_Heating_Demand",scope.OFF)
#postUpdate("pFF_Fitnessroom_Heating_Demand",scope.OFF)
#postUpdate("pFF_Makeuproom_Heating_Demand",scope.OFF)
#postUpdate("pFF_Bedroom_Heating_Demand",scope.OFF)
#postUpdate("pFF_Bathroom_Heating_Demand",scope.OFF)

Heating.forecast_cloud_cover_item_name = "pOutdoor_WeatherService_Cloud_Cover"
Heating.forecast_temperature_item_name = "pOutdoor_WeatherService_Temperature"

Heating.current_temperature_garden_item_name = WeatherHelper.getTemperatureItemName()

Heating.ventilation_filter_runtime_item_name = "pGF_Utilityroom_Ventilation_Filter_Runtime"

Heating.ventilation_level_item_name = "pGF_Utilityroom_Ventilation_Outgoing"
Heating.ventilation_outgoing_temperature_item_name = "pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"
Heating.ventilation_incomming_temperature_item_name = "pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"

Heating.heatingPower = "pGF_Utilityroom_Heating_Power"
Heating.heating_circuit_pump_speed_item_name = "pGF_Utilityroom_Heating_Circuit_Pump_Speed"
Heating.heating_temperature_pipe_out_item_name = "pGF_Utilityroom_Heating_Temperature_Pipe_Out"
Heating.heating_temperature_pipe_in_item_name = "pGF_Utilityroom_Heating_Temperature_Pipe_In"

Heating.heating_mode_item_name = "pOther_Manual_State_Heating"
Heating.holiday_status_item_name = "pOther_Manual_State_Holiday"
Heating.precence_status_item_name = "pOther_Presence_State"

Heating.forced_states_item_name = "pGF_Utilityroom_Heating_Force_States"

_ground_floor = ThermalStorageType( capacity=164.0, uValue=0.320, uOffset=0.08, factor=0.60 )
_ground_ceiling = ThermalStorageType( capacity=308.0, uValue=0.610, uOffset=0.1, factor=1.0 )

_outer_36_wall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0 )
_outer_22_wall = ThermalStorageType( capacity=53.0, uValue=0.348, uOffset=0.08, factor=1.0 )
_garage_wall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0 )

_inner_11_wall = ThermalStorageType( capacity=87.0 / 2.0, uValue=0.883, uOffset=0, factor=1.0 )
_inner_17_wall = ThermalStorageType( capacity=111.0 / 2.0, uValue=0.565, uOffset=0, factor=1.0 )

_main_door = ThermalBridgeType( uValue=1.400, uOffset=0.08, factor=1.0 )
_utilityroom_garage_door = ThermalBridgeType( uValue=1.700, uOffset=0.08, factor=1.0 )
_outer_window = ThermalBridgeType( uValue=0.970, uOffset=0.08, factor=1.0 )

_outer_shutter = ThermalBridgeType( uValue=0.34, uOffset=0.08, factor=1.0 )

_first_floor = ThermalStorageType( capacity=136.0, uValue=0.610, uOffset=0.1, factor=1.0 )
_first_ceiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0 )
_first_sloping_ceiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0 )
_first_sloping_window = ThermalBridgeType( uValue=1.400, uOffset=0.1, factor=1.0 )

_attic_floor = ThermalStorageType( capacity=1.7, uValue=0.186, uOffset=0, factor=1.0 )

# https://de.wikipedia.org/wiki/W%C3%A4rmedurchgangskoeffizient
_garage_window = ThermalBridgeType( uValue=2.0, uOffset=0.1, factor=1.0 )
_garage_door = ThermalBridgeType( uValue=3.49, uOffset=0.1, factor=1.0 )

_first_floor_height = 2.57
_second_floor_height = 2.45
_attic_floor_height = 2.10

rooms = [
    Room(
        name='lGF_Garage',
        volume=54.0702 * _attic_floor_height / 2.0,
        walls=[
            Wall(direction='floor', area=27.456025, type=_attic_floor),
            Wall(direction='ceiling', area=27.456025, type=_first_sloping_ceiling),
            Wall(direction='west', area=5.319, type=_outer_22_wall),
            Wall(direction='north', area=4.18, type=_outer_36_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=3.509, type=_outer_36_wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.5, type=_outer_36_wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.85, type=_outer_36_wall,bound="lGF_Guesttoilet"),
            Wall(direction='east', area=5.21, type=_outer_22_wall),
            Wall(direction='south', area=17.039, type=_outer_22_wall)
        ],
        transitions=[
            Window(direction='west', area=0.6, type=_garage_window),
            Door(direction='west', area=1.880625, type=_garage_door),
            Door(direction='east', area=1.880625, type=_garage_door)
        ]
    ),
    Room(
        name='lGF_Guesttoilet',
        additionalRadiator=True,
        heatingVolume=29.63,
        volume=4.92445 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=6.29125, type=_ground_floor),
            Wall(direction='ceiling', area=6.29125, type=_ground_ceiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner_11_wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.4949, type=_inner_17_wall, bound="lGF_Corridor"),
            Wall(direction='east', area=9.14345, type=_outer_36_wall),
            Wall(direction='south', area=5.0225, type=_garage_wall, bound="lGF_Garage")
        ],
        transitions=[
            Window(direction='east', area=1.045, type=_outer_window, contactItem='pGF_Guesttoilet_Openingcontact_Window_State', shutterItem='pGF_Guesttoilet_Shutter_Control', shutterArea=0.1292)
        ]
    ),
    Room(
        name='lGF_Utilityroom',
        # TODO check
        #heatingVolume=27.04,
        volume=7.816325 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=8.9875, type=_ground_floor),
            Wall(direction='ceiling', area=8.9875, type=_ground_ceiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner_11_wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.39615, type=_inner_17_wall, bound="lGF_Corridor"),
            Wall(direction='east', area=10.31765, type=_inner_11_wall, bound="lGF_Guesttoilet"),
            Wall(direction='south', area=5.294375, type=_garage_wall, bound="lGF_Garage")
        ],
        transitions=[
            Door(direction='south', area=1.880625, type=_utilityroom_garage_door, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Boxroom',
        volume=4.72615 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=5.734025, type=_ground_floor),
            Wall(direction='ceiling', area=5.734025, type=_ground_ceiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='west', area=8.5388, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=4.57765, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='east', area=10.31765, type=_inner_11_wall, bound="lGF_Utilityroom"),
            Wall(direction='south', area=4.57765, type=_garage_wall, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Livingroom',
        heatingVolume=84.20 + 84.20 + 49.90,
        volume=37.9957 * _first_floor_height + 10.7406 * _first_floor_height,
        walls=[
            # Kitchen
            Wall(direction='floor', area=12.999225, type=_ground_floor),
            Wall(direction='ceiling', area=12.999225, type=_ground_ceiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='east', area=8.789925, type=_inner_17_wall, bound="lGF_Boxroom"),
            Wall(direction='south', area=4.6781, type=_garage_wall, bound="lGF_Garage"),
            Wall(direction='south', area=5.453, type=_outer_36_wall),
            Wall(direction='west', area=8.069575, type=_outer_36_wall),
            #Wall(direction='north', area=4.57765, type=_inner_17_wall),

            # Livingroom
            Wall(direction='floor', area=42.4732875, type=_ground_floor),
            Wall(direction='ceiling', area=16.3125, type=_ground_ceiling, bound="lFF_Bedroom"),
            Wall(direction='ceiling', area=17.07625, type=_ground_ceiling, bound="lFF_Makeuproom"),
            Wall(direction='ceiling', area=9.0845375, type=_ground_ceiling, bound="lFF_Corridor"),
            Wall(direction='south', area=3.393775, type=_outer_36_wall),
            Wall(direction='west', area=9.292675, type=_outer_36_wall),
            Wall(direction='north', area=18.92765, type=_outer_36_wall),
            Wall(direction='east', area=7.34725, type=_inner_17_wall, bound="lGF_Corridor"),
            Wall(direction='east', area=10.339175, type=_inner_17_wall, bound="lGF_Workroom"),
            Wall(direction='south', area=6.177675, type=_inner_17_wall, bound="lGF_Boxroom")
        ],
        transitions=[
            Window(direction='west', area=2.2, type=_outer_window, contactItem='pGF_Kitchen_Openingcontact_Window_State', shutterItem='pGF_Kitchen_Shutter_Control', shutterArea=0.2992, radiationArea=0.645*1.01*2.0, sunProtectionItem="pOther_Automatic_State_Sunprotection_Livingroom"),
            Window(direction='west', area=5.8232, type=_outer_window, contactItem='pGF_Livingroom_Openingcontact_Window_Terrace_State', shutterItem='pGF_Livingroom_Shutter_Terrace_Control', shutterArea=0.4267, radiationArea=0.625*2.13*3.0),
            Window(direction='west', area=4.0832, type=_outer_window, contactItem='pGF_Livingroom_Openingcontact_Window_Couch_State', shutterItem='pGF_Livingroom_Shutter_Couch_Control', shutterArea=0.2992, radiationArea=0.625*2.13*2.0)
        ]
    ),
    Room(
        name='lGF_Workroom',
        heatingVolume=60.19,
        volume=11.53445 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=13.5891, type=_ground_floor),
            Wall(direction='ceiling', area=13.5891, type=_ground_ceiling, bound="lFF_Fitnessroom"),
            Wall(direction='west', area=10.31765, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=10.8486, type=_outer_36_wall),
            Wall(direction='east', area=7.9847, type=_outer_36_wall),
            Wall(direction='south', area=9.06975, type=_inner_17_wall, bound="lGF_Corridor")
        ],
        transitions=[
            Window(direction='east', area=2.07625, type=_outer_window, contactItem='pGF_Workroom_Openingcontact_Window_State', shutterItem='pGF_Workroom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lGF_Corridor',
        heatingVolume=40.93,
        volume=11.3076 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=12.9843, type=_ground_floor),
            Wall(direction='ceiling', area=2.0524125, type=_ground_ceiling, bound="lFF_Corridor"),
            Wall(direction='west', area=7.0746, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=9.06975, type=_inner_17_wall, bound="lGF_Workroom"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer_36_wall),
            Wall(direction='south', area=3.4949, type=_inner_17_wall, bound="lGF_Guesttoilet"),
            Wall(direction='south', area=4.04725, type=_inner_17_wall, bound="lGF_Utilityroom")
        ],
        transitions=[
            # count the main door only 50%, because other 50% is counted on upper floor
            Door(direction='east', area=4.6632/2.0, type=_main_door, contactItem='pGF_Corridor_Openingcontact_Door_State'),
            # count 50% of the sloping window from upper floor
            Window(direction='east', area=0.7676/2.0, type=_first_sloping_window)
        ]
    ),
    Room(
        name='lFF_Corridor',
        heatingVolume=38.45,
        volume=18.1926 * _second_floor_height - 4.3968,
        walls=[
            Wall(direction='floor', area=4.61578125, type=_first_floor, bound="lGF_Livingroom"),
            Wall(direction='floor', area=4.61578125, type=_first_floor, bound="lGF_Corridor"),
            Wall(direction='ceiling', area=14.1436125, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=7.77045, type=_inner_11_wall, bound="lFF_Bedroom"),
            Wall(direction='north', area=8.51865, type=_inner_17_wall, bound="lFF_Fitnessroom"),
            Wall(direction='north', area=1.69615, type=_inner_17_wall, bound="lFF_Makeuproom"),
            # east wall is shared between lower and upper floor
            Wall(direction='east', area=(5.19525+3.435)/2.0, type=_outer_36_wall),
            Wall(direction='east', area=8.026, type=_first_sloping_ceiling),
            Wall(direction='south', area=8.51865, type=_inner_17_wall, bound="lFF_Bathroom"),
            Wall(direction='south', area=1.69615, type=_inner_17_wall, bound="lFF_Bedroom"), # Dressingroom
        ],
        transitions=[
            # count 50% of the main door from lower floor
            Door(direction='east', area=4.6632/2.0, type=_main_door, contactItem='pGF_Corridor_Openingcontact_Door_State'),
            # count the sloping window only 50%, because other 50% is counted on lower floor
            Window(direction='east', area=0.7676/2.0, type=_first_sloping_window)
        ]
    ),
    Room(
        name='lFF_Fitnessroom',
        heatingVolume=39.61,
        volume=13.036325 * _second_floor_height - 4.6016,
        walls=[
            Wall(direction='floor', area=4.0, type=_first_floor, bound="lGF_Livingroom"),
            Wall(direction='floor', area=12.626875, type=_first_floor, bound="lGF_Workroom"),
            Wall(direction='ceiling', area=10.3266375, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner_11_wall, bound="lFF_Makeuproom"),
            Wall(direction='north', area=8.1533, type=_outer_36_wall),
            Wall(direction='east', area=3.595, type=_outer_36_wall),
            Wall(direction='east', area=9.2032, type=_first_sloping_ceiling),
            Wall(direction='south', area=8.51865, type=_inner_17_wall, bound="lFF_Corridor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outer_window, contactItem='pFF_Fitnessroom_Openingcontact_Window_State', shutterItem='pFF_Fitnessroom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lFF_Makeuproom',
        heatingVolume=41.32,
        volume=14.99575 * _second_floor_height - 4.6016,
        walls=[
            Wall(direction='floor', area=17.07625, type=_first_floor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=10.7760125, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=3.595, type=_outer_36_wall),
            Wall(direction='west', area=9.2032, type=_first_sloping_ceiling),
            Wall(direction='north', area=8.5008, type=_outer_36_wall),
            Wall(direction='east', area=9.9941, type=_inner_11_wall, bound="lFF_Fitnessroom"),
            Wall(direction='south', area=7.17, type=_inner_17_wall, bound="lFF_Bedroom"),
            Wall(direction='south', area=1.69615, type=_inner_17_wall, bound="lFF_Corridor")
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outer_window, contactItem='pFF_Makeuproom_Openingcontact_Window_State', shutterItem='pFF_Makeuproom_Shutter_Control', shutterArea=0.2567)
        ]
    ),
    Room(
        name='lFF_Bedroom',
        heatingVolume=35.87 + 39.33,
        volume=(14.3929 * _second_floor_height) + (14.88435 * _second_floor_height - 4.6016),
        walls=[
            # Bedroom
            Wall(direction='floor', area=16.3125, type=_first_floor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=16.3125, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=5.9851, type=_outer_36_wall),
            Wall(direction='north', area=12.51, type=_inner_17_wall, bound="lFF_Makeuproom"),
            Wall(direction='east', area=8.03455, type=_inner_11_wall, bound="lFF_Corridor"),
            Wall(direction='south', area=3.28735, type=_outer_36_wall),
            Wall(direction='south', area=0.5, type=_first_sloping_ceiling),

            # Dressingroom
            Wall(direction='floor', area=16.660625, type=_first_floor, bound="lGF_Livingroom"),
            Wall(direction='ceiling', area=10.40850625, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=3.5075, type=_outer_36_wall),
            Wall(direction='west', area=8.9792, type=_first_sloping_ceiling),
            Wall(direction='north', area=3.63485, type=_inner_17_wall, bound="lFF_Corridor"),
            Wall(direction='east', area=9.9941, type=_inner_11_wall, bound="lFF_Bathroom"),
            Wall(direction='south', area=9.0333, type=_outer_36_wall)
        ],
        transitions=[
            Window(direction='west', area=3.1375, type=_outer_window, contactItem='pFF_Bedroom_Openingcontact_Window_State', shutterItem='pFF_Bedroom_Shutter_Control', shutterArea=0.4267, radiationArea=0.615*1.00*3.0, sunProtectionItem="pOther_Automatic_State_Sunprotection_Bedroom"),
            Window(direction='south', area=1.41875, type=_outer_window, contactItem='pFF_Dressingroom_Openingcontact_Window_State', shutterItem='pFF_Dressingroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Dressingroom")
#        ]
        ]
    ),
#    Room(
#        name='lFF_Dressingroom',
#        heatingVolume=57.58,
#        volume=14.88435 * _second_floor_height - 4.6016,
#        walls=[
#            Wall(direction='floor', area=16.660625, type=_first_floor, bound="lGF_Livingroom"),
#            Wall(direction='ceiling', area=10.40850625, type=_first_ceiling, bound="lFF_Attic"),
#            Wall(direction='west', area=3.5075, type=_outer_36_wall),
#            Wall(direction='west', area=8.9792, type=_first_sloping_ceiling),
#            Wall(direction='north', area=3.63485, type=_inner_17_wall, bound="lFF_Corridor"),
#            Wall(direction='east', area=9.9941, type=_inner_11_wall, bound="lFF_Bathroom"),
#            Wall(direction='south', area=9.0333, type=_outer_36_wall)
#        ],
#        transitions=[
#            Window(direction='south', area=1.41875, type=_outer_window, contactItem='pFF_Dressingroom_Openingcontact_Window_State', shutterItem='pFF_Dressingroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Dressingroom")
#        ]
#    ),
    Room(
        name='lFF_Bathroom',
        additionalRadiator=True,
        heatingVolume=35.31,
        volume=12.51273 * _second_floor_height - 2.5884,
        walls=[
            Wall(direction='floor', area=5.482375, type=_first_floor, bound="lGF_Guesttoilet"),
            Wall(direction='floor', area=8.9875, type=_first_floor, bound="lGF_Utilityroom"),
            Wall(direction='ceiling', area=10.3266375, type=_first_ceiling, bound="lFF_Attic"),
            Wall(direction='west', area=9.9941, type=_inner_11_wall, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='north', area=7.4633, type=_inner_17_wall, bound="lFF_Corridor"),
            Wall(direction='east', area=5.033, type=_outer_36_wall),
            Wall(direction='east', area=5.1768, type=_first_sloping_ceiling),
            Wall(direction='south', area=7.63045, type=_outer_36_wall)
        ],
        transitions=[
            Window(direction='south', area=1.41875, type=_outer_window, contactItem='pFF_Bathroom_Openingcontact_Window_State', shutterItem='pFF_Bathroom_Shutter_Control', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Bathroom")
        ]
    ),
    Room(
        name='lFF_Attic',
        volume=54.0702 * _attic_floor_height / 2.0,
        walls=[
            Wall(direction='floor', area=59.871875, type=_attic_floor, bound="lFF_Bedroom" ),
            Wall(direction='west', area=9.9941, type=_outer_36_wall),
            Wall(direction='west', area=49.9872093014803, type=_first_sloping_ceiling),
            Wall(direction='north', area=5.91675, type=_outer_36_wall),
            Wall(direction='east', area=49.9872093014803, type=_first_sloping_ceiling),
            Wall(direction='south', area=5.01995, type=_outer_36_wall)
        ],
        transitions=[
            Window(direction='east', area=0.7676, type=_first_sloping_window),
            Window(direction='south', area=0.7676, type=_outer_window, contactItem='pFF_Attic_Openingcontact_Window_State', shutterItem='pFF_Attic_Shutter_Control', shutterArea=0.19295, radiationArea=0.72*1.00, sunProtectionItem="pOther_Automatic_State_Sunprotection_Attic")
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

@rule(
    triggers = [
        GenericCronTrigger("0 */5 * * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Common_Fault")
    ]
)
class ErrorMessage:
    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent":
            if Registry.getItem("pGF_Utilityroom_Heating_Common_Fault").getLastStateUpdate() < datetime.now().astimezone() - timedelta(minutes=10):
                Registry.getItem("eOther_Error_Heating_Message").postUpdateIfDifferent("Keine Updates mehr seit mehr als 10 Minuten")
                return
        elif Registry.getItemState("pGF_Utilityroom_Heating_Common_Fault").intValue() > 0:
            Registry.getItem("eOther_Error_Heating_Message").postUpdateIfDifferent(Transformation.transform("MAP", "heating_state_de.map", Registry.getItemState("pGF_Utilityroom_Heating_Common_Fault").toString() ))
            return

        Registry.getItem("eOther_Error_Heating_Message").postUpdateIfDifferent("")

@rule(
    triggers = [
        #GenericCronTrigger("*/15 * * * * ?"),
        GenericCronTrigger("0 */10 1 ? * MON,FRI"),
        GenericCronTrigger("0 0 2 ? * MON,FRI")
    ]
)
class Ventile:
    maintenanceMode = {}

    # refresh heating ventile twice per week
    def execute(self, module, input):
        # **** DEBUG ****
        #for room in filter( lambda room: room.getHeatingVolume() != None and room.getName() in controllableRooms,Heating.getRooms()):
        #    circuiteItem = Heating.getHeatingCircuitItemName(room)
        #    self.logger.info(circuiteItem + " " + str(Registry.getItem(circuiteItem).getLastStateChange()))
        # **** DEBUG ****

        now = datetime.now().astimezone()
        for room in filter( lambda room: room.getHeatingVolume() != None and room.getName() in controllableRooms,Heating.getRooms()):
            circuiteItemName = Heating.getHeatingCircuitItemName(room)
            circuiteItem = Registry.getItem(circuiteItemName)
            if now.hour == 2:
                if room not in Ventile.maintenanceMode:
                    continue
                #self.logger.info("STOP " + room.getName() + " " + str(scope.ON if circuiteItem.getState() == scope.OFF else scope.OFF))
                circuiteItem.sendCommand(scope.ON if circuiteItem.getState() == scope.OFF else scope.OFF)
                del Ventile.maintenanceMode[room]
            elif circuiteItem.getLastStateChange() is None or circuiteItem.getLastStateChange() < now - timedelta(hours=24):
                #self.logger.info("START " + room.getName() + " " + str(scope.ON if circuiteItem.getState() == scope.OFF else scope.OFF))
                circuiteItem.sendCommand(scope.ON if circuiteItem.getState() == scope.OFF else scope.OFF)
                Ventile.maintenanceMode[room] = True

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Auto_Mode"),
        GenericCronTrigger("15 * * * * ?")
    ]
)
class Main:
    def __init__(self):
        self.active_heating_operating_mode = -1
        self.active_reduced_time_in_minutes = -1

        #self.test()

    def execute(self, module, input):
        self.logger.info(u"--------: >>>" )

        if input['event'].getType() != "TimerEvent" and input['event'].getItemName() == 'pGF_Utilityroom_Heating_Auto_Mode':
            self.active_heating_operating_mode = -1
            self.active_reduced_time_in_minutes = -1

        now = datetime.now().astimezone()
        auto_mode_enabled = Registry.getItemState("pGF_Utilityroom_Heating_Auto_Mode").intValue() == 1

        current_operating_mode_change = Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange()
        current_operating_mode = Registry.getItemState("pGF_Utilityroom_Heating_Operating_Mode").intValue()

        current_heating_demand = Registry.getItemState("pGF_Utilityroom_Heating_Demand")

        heating = Heating(self.logger)

        messured_radiation_short_term = WeatherHelper.getSolarPowerStableItemState(10).doubleValue()
        messured_radiation_long_term = WeatherHelper.getSolarPowerStableItemState(30).doubleValue()
        messured_light_level_short_term = WeatherHelper.getLightLevelStableItemState(30).doubleValue()
        messured_light_level_long_term = WeatherHelper.getLightLevelStableItemState(60).doubleValue()

        cr, cr4, cr8, hhs = heating.calculate(current_heating_demand == scope.ON, messured_radiation_short_term)

        # **** DEBUG ****
        heating.logCoolingAndRadiations("FC8     ", cr8)
        heating.logCoolingAndRadiations("FC4     ", cr4)
        heating.logCoolingAndRadiations("Current ", cr, messured_radiation_long_term, messured_light_level_long_term)

        heating.logHeatingStates(cr, hhs )
        # ***************

        if auto_mode_enabled:
            heating_requested = hhs.isHeatingRequested()

            # *** CHECK OPEN WINDOWS AND MIN HEATING VOLUME ***
            disabled_heating_demand_count = 0
            requested_possible_heating_volume = 0.0
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):

                rs = cr.getRoomState(room.getName())
                rhs = hhs.getHeatingState(room.getName())

                # *** CHECKED HEATING DEMAND ***
                if rhs.hasLongOpenWindow():
                    disabled_heating_demand_count = disabled_heating_demand_count + 1

                if rhs.getHeatingDemandTime() != None and rhs.getHeatingDemandTime() > 0.0:
                    requested_possible_heating_volume = requested_possible_heating_volume + rs.getPossibleHeatingVolume()

            if heating_requested:
                # *** FORCED HEATING OFF ***
                if disabled_heating_demand_count >= 3:
                    heating_requested = False
                    self.logger.info(u"        : ---")
                    self.logger.info(u"        : Heating OFF • too many open windows")

                # *** FORCED HEATING OFF IF ONLY 20%***
                if requested_possible_heating_volume < Heating.total_heating_volume * 0.2:
                    heating_requested = False
                    activeHeatingVolume = round(requested_possible_heating_volume / 1000.0,3)
                    possibleHeatingVolume = round(Heating.total_heating_volume / 1000.0,3)
                    self.logger.info(u"        : ---")
                    self.logger.info(u"        : Heating OFF • only {}m² of {}m² active".format(activeHeatingVolume,possibleHeatingVolume))
                # *************************************************


            # *** PERSIST AND CIRCUITS ************************
            # forced open circuits are needed during burner startup phase to avoid burner start/stops
            forced_open_circuit_on_start = ( # nur WW or Reduziert
                                         # Forced circuits should stay open when burner is inactive
                                         current_operating_mode != 2
                                         or
                                         # Heizen mit WW
                                         # Forced circuits should stay open until burner is active for 5 min.
                                         (current_operating_mode == 2 and now - timedelta(minutes=5) < current_operating_mode_change)
                                       )
            longest_runetime = 0
            last_circuit_opened_at = None
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.getRooms()):

                rs = cr.getRoomState(room.getName())
                rhs = hhs.getHeatingState(room.getName())

                # *** PERSIST HEATING CHARGE LEVEL ***
                total_charge_level = rs.getChargedBuffer()
                Registry.getItem(Heating.getHeatingBufferItemName(room)).postUpdateIfDifferent(total_charge_level)

                # *** PERSIST HEATING TARGET TEMPERATURE ***
                Registry.getItem(Heating.getHeatingTargetTemperatureItemName(room)).postUpdateIfDifferent(rhs.getHeatingTargetTemperature() )

                if heating_requested and rhs.getHeatingDemandTime() > longest_runetime:
                    longest_runetime = rhs.getHeatingDemandTime()

                # *** PERSIST HEATING DEMAND ***
                if heating_requested and (rhs.getHeatingDemandTime() > 0 or room.getName() not in controllableRooms):
                    Registry.getItem(Heating.getHeatingDemandItemName(room)).postUpdateIfDifferent(scope.ON)
                else:
                    Registry.getItem(Heating.getHeatingDemandItemName(room)).postUpdateIfDifferent(scope.OFF)

                # *** CONTROL CIRCUITS AND HK ***
                if room.getName() in controllableRooms and room not in Ventile.maintenanceMode:
                    circuit_item = Heating.getHeatingCircuitItemName(room)
                    if heating_requested and ( rhs.getHeatingDemandTime() > 0 or forced_open_circuit_on_start ):
                        #self.logger.info("ON")
                        if Registry.getItem(circuit_item).sendCommandIfDifferent(scope.ON):
                            circuit_last_change = now
                        else:
                            circuit_last_change = Registry.getItem(circuit_item).getLastStateChange()

                        if last_circuit_opened_at == None or last_circuit_opened_at < circuit_last_change:
                            last_circuit_opened_at = circuit_last_change
                    else:
                        #self.logger.info("OFF")
                        Registry.getItem(circuit_item).sendCommandIfDifferent(scope.OFF)

                    # wall radiator
                    if room.hasAdditionalRadiator():
                        # additional radiator should only be enabled in case of CF heating
                        if heating_requested and ( rhs.getForcedInfo() == 'CF' or forced_open_circuit_on_start ):
                            Registry.getItem(Heating.getHeatingHKItemName(room)).sendCommandIfDifferent(scope.ON)
                        else:
                            Registry.getItem(Heating.getHeatingHKItemName(room)).sendCommandIfDifferent(scope.OFF)
            # *************************************************

            self.logger.info(u"        : ---" )

            # a heating ciruit was opened less then 5 minutes ago.
            # delay heating request to give circuit some time to open
            if current_heating_demand == scope.OFF and last_circuit_opened_at != None and now - timedelta(minutes=5) < last_circuit_opened_at:
                #self.logger.info(u"{}".format(last_circuit_opened_at))
                opened_before_in_minutes = int((now - last_circuit_opened_at).total_seconds() / 60)
                self.logger.info(u"Demand  : DELAYED • circuit was opened {} min. ago".format(opened_before_in_minutes))
            else:
                heating_demand = scope.ON if heating_requested else scope.OFF
                Registry.getItem("pGF_Utilityroom_Heating_Demand").postUpdateIfDifferent(heating_demand)

                endMsg = u" • {} min. to go".format(Heating.visualizeHeatingDemandTime(longest_runetime)) if longest_runetime > 0 else u""
                last_heating_demand_change = Registry.getItem("pGF_Utilityroom_Heating_Demand").getLastStateUpdate() # can be "getLastStateUpdate" datetime, because it is changed only from heating rule
                last_change_before_in_minutes = int((now - last_heating_demand_change).total_seconds() / 60)
                last_heating_change_formatted = last_heating_demand_change.strftime("%H:%M")
                last_change_before_formatted = last_change_before_in_minutes if last_change_before_in_minutes < 60 else '{:02d}:{:02d}'.format(*divmod(last_change_before_in_minutes, 60));
                self.logger.info(u"Demand  : {} since {} • {} min. ago{}".format(heating_demand, last_heating_change_formatted, last_change_before_formatted,endMsg) )

                self.controlHeating(now,current_operating_mode,current_operating_mode_change,heating_requested)
        else:
            self.logger.info(u"Demand  : SKIPPED • MANUAL MODE ACTIVE")

        self.setSunStates(now, cr, cr4, cr8, hhs, messured_radiation_long_term, messured_light_level_short_term, messured_light_level_long_term)

        self.logger.info(u"--------: <<<" )

    def setSunStates(self, now, cr, cr4, cr8, hhs, messured_radiation_long_term, messured_light_level_short_term, messured_light_level_long_term):
        cloud_cover = cr.getCloudCover()

        messured_radiation_short_term = cr.getSunRadiation()

        if messured_radiation_long_term is None:
            messured_radiation_long_term = messured_radiation_short_term

        _sun_south_radiation, _sun_west_radiation, _sun_radiation, _sun_debug_info = SunRadiation.getSunPowerPerHour(now, cloud_cover, messured_radiation_short_term)
        effective_south_radiation_short_term = _sun_south_radiation / 60.0
        effective_west_radiation_short_term = _sun_west_radiation / 60.0
        #self.logger.info(u"Gemessen Avg 10 min until {}: {} {}".format(offset,effective_south_radiation_short_term, effective_west_radiation_short_term))

        _sun_south_radiation, _sun_west_radiation, _sun_radiation, _sun_debug_info = SunRadiation.getSunPowerPerHour(now, cloud_cover, messured_radiation_long_term)
        effective_south_radiation_long_term = _sun_south_radiation / 60.0
        effective_west_radiation_long_term = _sun_west_radiation / 60.0
        #self.logger.info(u"Gemessen Avg 30 min until {}: {} {}".format(offset,effective_south_radiation_long_term, effective_west_radiation_long_term))

        effective_south_radiation_max = cr.getSunSouthRadiationMax() / 60.0
        effective_west_radiation_max = cr.getSunWestRadiationMax() / 60.0
        #self.logger.info(u"Max: {} {}".format(effective_south_radiation_max, effective_west_radiation_max))

        current_outdoor_temperature = cr.getReferenceTemperature()
        current_outdoor_temperature4 = cr4.getReferenceTemperature()
        current_outdoor_temperature8 = cr8.getReferenceTemperature()

        fallback_target_temperature = hhs.getHeatingState("lGF_Livingroom").getHeatingTargetTemperature()

        #self.logger.info(u"{} {}".format(messured_radiation_short_term,messured_radiation_long_term))

        # terrace radiation
        effective_radiation_short_term = messured_radiation_short_term / 60.0
        effective_radiation_long_term = messured_radiation_long_term / 60.0

        # use same azimut and elevation as heating calculation
        azimut, elevation, min_elevation, _ = SunRadiation.getSunData( now )
        if elevation >= min_elevation:
            if azimut >= 120:
                #self.logger.info(u"Sun     : {:.1f} W/min ({:.1f} W/min)".format(effective_radiation_short_term,effective_radiation_long_term))
                # glare protection during sandra's workdays
                needed_sunprotection = azimut >= 180 \
                    and messured_light_level_short_term > 15000 and messured_light_level_long_term > 15000 \
                    and now.weekday() <= 4 and Registry.getItemState("pOther_Presence_Sandra_State") == scope.ON
                if not needed_sunprotection:
                    # hot stone protection
                    needed_sunprotection = effective_radiation_long_term > 8.0 and (current_outdoor_temperature > 26 or current_outdoor_temperature4 > 26)
                    if not needed_sunprotection:
                        # hot room protection (only above 18°C)
                        target_room_temperature = hhs.getHeatingState("lGF_Livingroom").getHeatingTargetTemperature()
                        current_room_temperature = cr.getRoomState("lGF_Livingroom").getCurrentTemperature()
                        needed_sunprotection = self.isTooWarm(effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature )

                if needed_sunprotection:
                    if Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdateIfDifferent(SunProtectionHelper.STATE_TERRACE_CLOSED):
                        self.logger.info(u"DEBUG: SP switching 2 • {} • {} ({}) W/m² • {} ({}) lux".format("Terrace",round(effective_radiation_short_term,1),round(effective_radiation_long_term,1),int(messured_light_level_short_term), int(messured_light_level_long_term)))
                elif Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_OPEN:
                    Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdate(SunProtectionHelper.STATE_TERRACE_MAYBE_CLOSED)
                    self.logger.info(u"DEBUG: SP switching 1 • {} • {} ({}) W/m² • {} ({}) lux".format("Terrace",round(effective_radiation_short_term,1),round(effective_radiation_long_term,1),int(messured_light_level_short_term), int(messured_light_level_long_term)))
        elif azimut > 260.00:
            #if Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_OPEN:
            if Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdateIfDifferent(SunProtectionHelper.STATE_TERRACE_OPEN):
                self.logger.info(u"DEBUG: SP switching 0 • {}".format("Terrace"))

        for room in Heating.getRooms():
            rs = cr.getRoomState(room.getName())

            target_room_temperature = fallback_target_temperature if room.getHeatingVolume() == None else hhs.getHeatingState(room.getName()).getHeatingTargetTemperature()

            for transition in room.transitions:
                if not isinstance(transition,Window) or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
                    continue

                #if current_outdoor_temperature < target_room_temperature and current_outdoor_temperature4 < target_room_temperature and current_outdoor_temperature8 < target_room_temperature:
                #    Registry.getItem(transition.getSunProtectionItem()).postUpdateIfDifferent(scope.OFF )
                #    continue

                current_room_temperature = rs.getCurrentTemperature()

                effective_radiation_short_term = effective_south_radiation_short_term if transition.getDirection() == 'south' else effective_west_radiation_short_term
                effective_radiation_long_term = effective_south_radiation_long_term if transition.getDirection() == 'south' else effective_west_radiation_long_term
                effective_radiation_max = effective_south_radiation_max if transition.getDirection() == 'south' else effective_west_radiation_max

                if Registry.getItemState(transition.getSunProtectionItem()) == scope.ON:
                    radiationTooLow = (effective_radiation_short_term < 2.0 and ( effective_radiation_max < 2.0 or effective_radiation_long_term < 2.0 ))

                    roomTemperatureTooCold = current_room_temperature < target_room_temperature - 0.7

                    radiationNotWayTooHigh = (effective_radiation_short_term < 12.0 and ( effective_radiation_max < 12.0 or effective_radiation_long_term < 12.0 ))
                    itsGettingColderAndRoomIsNotWarmEnoughForIt = ( \
                        current_outdoor_temperature < target_room_temperature - 0.2 \
                        and \
                        current_outdoor_temperature4 < target_room_temperature - 0.2 \
                        and \
                        current_room_temperature < target_room_temperature + ( 1.8 if radiationNotWayTooHigh else 0.8 ) \
                    )

                    if radiationTooLow or roomTemperatureTooCold or itsGettingColderAndRoomIsNotWarmEnoughForIt:
                        if Registry.getItem(transition.getSunProtectionItem()).getLastStateUpdate() < now - timedelta(minutes=60):
                            Registry.getItem(transition.getSunProtectionItem()).postUpdate(scope.OFF)
                            self.logger.info(u"DEBUG: SP switching OFF • {} {} {} {}".format(room.getName(),effective_radiation_short_term,effective_radiation_long_term,effective_radiation_max))
                        else:
                            self.logger.info(u"DEBUG: SP skipped OFF • {} {} {} {}".format(room.getName(),effective_radiation_short_term,effective_radiation_long_term,effective_radiation_max))
                else:
                    #self.logger.info(u"{} {}".format(room.getName(),effective_radiation_short_term))
                    #self.logger.info(u"{} {}".format(radiation_too_high,room_temperature_too_warm))
                    #self.logger.info(u"{} {}".format(current_room_temperature,target_room_temperature))
                    #self.logger.info(u"{} {}".format(current_outdoor_temperature,current_outdoor_temperature4))

                    tooWarm = self.isTooWarm(effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature )
                    if tooWarm:
                        if Registry.getItem(transition.getSunProtectionItem()).getLastStateUpdate() < now - timedelta(minutes=30):
                            Registry.getItem(transition.getSunProtectionItem()).postUpdate(scope.ON)
                            self.logger.info(u"DEBUG: SP switching ON • {} {} {} {}".format(room.getName(),effective_radiation_short_term,effective_radiation_long_term,effective_radiation_max))
                        else:
                            self.logger.info(u"DEBUG: SP skipped ON • {} {} {} {}".format(room.getName(),effective_radiation_short_term,effective_radiation_long_term,effective_radiation_max))

    def isTooWarm( self, effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature ):
        if current_outdoor_temperature <= 18 and current_outdoor_temperature4 <= 18:
            return False

        radiation_too_high = effective_radiation_short_term > 5.0

        room_temperature_too_warm = current_room_temperature > target_room_temperature - 0.5

        radiation_way_too_high = effective_radiation_short_term > 15.0
        its_getting_warmer_or_room_is_way_too_warm = ( \
            current_outdoor_temperature > target_room_temperature \
            or \
            current_outdoor_temperature4 > target_room_temperature \
            or \
            current_room_temperature > target_room_temperature + ( 2.0 if not radiation_way_too_high else 1.0 ) \
        )
        return radiation_too_high and room_temperature_too_warm and its_getting_warmer_or_room_is_way_too_warm

    def controlHeating( self, now, current_operating_mode, current_operating_mode_change, is_heating_requested ):

        # 0 - Abschalten
        # 1 - Nur WW
        # 2 - Heizen mit WW
        # 3 - Reduziert
        # 4 - Normal

        if self.active_heating_operating_mode == -1:
            self.active_heating_operating_mode = current_operating_mode

        force_retry = self.active_heating_operating_mode != current_operating_mode
        force_retry_msg = u" • RETRY {} {}".format(self.active_heating_operating_mode,current_operating_mode) if force_retry else u""
        delayed_msg = u""

        last_change_before_in_minutes = int((now - current_operating_mode_change).total_seconds() / 60)
        last_heating_change_formatted = current_operating_mode_change.strftime("%H:%M")
        last_change_before_formatted = last_change_before_in_minutes if last_change_before_in_minutes < 60 else '{:02d}:{:02d}'.format(*divmod(last_change_before_in_minutes, 60));

        self.logger.info(u"Active  : {} since {} • {} min. ago".format(Transformation.transform("MAP", "heating_de.map", str(current_operating_mode) ),last_heating_change_formatted,last_change_before_formatted) )

        # Nur WW
        if current_operating_mode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if is_heating_requested:
                is_running_long_enough = Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange() < now - timedelta(minutes=Heating.MIN_ONLY_WW_TIME)

                if force_retry or is_running_long_enough:
                    self.active_heating_operating_mode = 2
                    Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").sendCommand(self.active_heating_operating_mode)
                else:
                    runtime_to_go = Heating.MIN_ONLY_WW_TIME - last_change_before_in_minutes
                    delayed_msg = u" in {} min.".format(runtime_to_go)

                self.logger.info(u"Switch  : Heizen mit WW{}{}".format(delayed_msg,force_retry_msg))
            self.active_reduced_time_in_minutes = -1

        # Heizen mit WW
        elif current_operating_mode == 2:
            current_power_state = Registry.getItemState("pGF_Utilityroom_Heating_Power").intValue()

            if current_power_state == 0 and last_change_before_in_minutes < 1:
                self.logger.info(u"Delayed : Give the heating system more time to react")
                return

            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not is_heating_requested:
                is_running_long_enough = Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange() < now - timedelta(minutes=Heating.MIN_HEATING_TIME)

                if current_power_state == 0 or force_retry or is_running_long_enough:
                    self.active_heating_operating_mode = 1
                    Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").sendCommand(self.active_heating_operating_mode)
                else:
                    runtime_to_go = Heating.MIN_HEATING_TIME - last_change_before_in_minutes
                    delayed_msg = u" in {} min.".format(runtime_to_go)

                self.logger.info(u"Switch  : Nur WW{}{}".format(delayed_msg,force_retry_msg))
                self.active_reduced_time_in_minutes = -1

            # Brenner läuft nicht
            elif current_power_state == 0:
                force_reduced_msg = None

                # No burner starts since 10 minutes
                waiting_time = now - timedelta(minutes=10)
                if Registry.getItem("pGF_Utilityroom_Heating_Power").getLastStateChange() < waiting_time and Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange() < waiting_time:
                    force_reduced_msg = u" • No burner starts"
                else:
                    burner_starts = self.getBurnerStarts(now, 5)
                    is_water_heating = self.is_water_heating(now, 5)
                    # if burnder starts during last 5 minutes > 1 and no water heating (diff < 1°)
                    if burner_starts > 1 and not is_water_heating:
                        force_reduced_msg = u" • Too many burner starts • Heating system tried to start {} times".format(burner_starts)

                if force_reduced_msg != None:
                    self.active_reduced_time_in_minutes = Heating.MIN_REDUCED_TIME if self.active_reduced_time_in_minutes == -1 else min( self.active_reduced_time_in_minutes * 2, Heating.MAX_REDUCED_TIME )
                    self.active_heating_operating_mode = 3

                    Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").sendCommand(self.active_heating_operating_mode)
                    self.logger.info(u"Switch  : Reduziert{}{}".format(force_reduced_msg,force_retry_msg))
                elif is_water_heating:
                    self.logger.info(u"Delayed : Heating system heats water")
                else:
                    self.logger.info(u"Delayed : Heating system tried to start {} times".format(burner_starts))

            else:
                if Registry.getItemState("pGF_Utilityroom_Heating_Circuit_Pump_Speed").intValue() == 0:
                    if self.is_water_heating(now, 5):
                        self.logger.info(u"Paused  : Heating system heats water")
                    else:
                        if Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Boiler_Target").doubleValue() >= 55:
                            self.logger.info(u"Paused  : Heating system heats boiler")
                        else:
                            self.logger.info(u"Paused  : For unkown reason")
                # reset reduced counter after 5 minutes of heating
                elif self.active_reduced_time_in_minutes != -1 and Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange() < now - timedelta(minutes=5):
                    self.active_reduced_time_in_minutes = -1

        # Reduziert
        elif current_operating_mode == 3:
            # Wenn Temperatur seit XX min OK ist und der brenner sowieso aus ist kann gleich in 'Nur WW' gewechselt werden
            if not is_heating_requested:
                self.active_heating_operating_mode = 1
                Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").sendCommand(self.active_heating_operating_mode)
                self.logger.info(u"Switch  : Nur WW because heating is not needed anymore{}".format(force_retry_msg))
            else:
                # Dauernd reduziert läuft seit mindestens XX Minuten
                target_reduced_time_in_minutes = self.active_reduced_time_in_minutes if self.active_reduced_time_in_minutes != -1 else Heating.MIN_REDUCED_TIME
                #self.logger.info("{}".format(self.active_reduced_time_in_minutes))
                #self.logger.info("{}".format(target_reduced_time_in_minutes))
                if force_retry or Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").getLastStateChange() < now - timedelta(minutes=target_reduced_time_in_minutes):
                    self.active_heating_operating_mode = 2
                    Registry.getItem("pGF_Utilityroom_Heating_Operating_Mode").sendCommand(self.active_heating_operating_mode)
                elif not force_retry:
                    runtime_to_go = target_reduced_time_in_minutes - last_change_before_in_minutes
                    delayed_msg = u" in {} min.".format(runtime_to_go)

                self.logger.info(u"Switch  : Heizen mit WW{}{}".format(delayed_msg,force_retry_msg))

    def is_water_heating(self, now, limit_minutes):
        return ( Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Water_Storage").doubleValue() - ToolboxHelper.getMinimumSince("pGF_Utilityroom_Heating_Temperature_Water_Storage", now - timedelta(minutes=limit_minutes)).doubleValue() ) >= 1

    def getBurnerStarts( self, now, limit_minutes ):
        min_time = ToolboxHelper.getPersistedEntry("pGF_Utilityroom_Heating_Operating_Mode", now).getTimestamp()
        _min_time = now - timedelta(minutes=limit_minutes)
        if min_time < _min_time:
            min_time = _min_time

        current_time = now
        last_is_heating = False

        # check for new burner starts during this time periode
        # "pGF_Utilityroom_Heating_Burner_Starts" is not useable because of wather heating
        burner_starts = 0
        while current_time > min_time:
            current_item_entry = ToolboxHelper.getPersistedEntry("pGF_Utilityroom_Heating_Power", current_time)
            current_is_heating = ( current_item_entry.getState().doubleValue() != 0.0 )

            # count only heating events
            if current_is_heating != last_is_heating and current_is_heating:
                burner_starts = burner_starts + 1

            current_time = current_item_entry.getTimestamp() - timedelta(microseconds=1)
            last_is_heating = current_is_heating

        return burner_starts

    #def test(self):
    #    formatter  = DateTimeFormatter.ISO_OFFSET_DATE_TIME
    #    zdtWithZoneOffset = ZonedDateTime.parse("2024-02-13T07:58:15+01:00", formatter)
    #    zdtInLocalTimeline = zdtWithZoneOffset.withZoneSameInstant(ZoneId.systemDefault())

    #    ref = ZonedDateTime.now()
    #    self.logger.info("{} {}".format(ref, zdtInLocalTimeline))
    #    count = self.getBurnerStarts(zdtInLocalTimeline, 5)
    #    self.logger.info(str(count))

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Utilityroom_Heating_Operating_Mode")
    ]
)
class CommandHandler():
    # refresh heating ventile twice per week
    def execute(self, module, input):
        command = input["event"].getItemCommand()
        Registry.getItem("pGF_Utilityroom_Heating_Command").sendCommand("write;0x2323;1;{}".format(command))
        #self.logger.info("write;0x2323;1;{}".format(command))
