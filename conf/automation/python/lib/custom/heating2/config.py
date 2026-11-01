from custom.heating.house import ThermalStorageType, ThermalBridgeType, Wall, Door, Window, Room

# uValue => https://www.ubakus.de/u-wert-rechner/?
# uOffset => Wärmebrückenzuschlag

_ground_floor_tiles       = ThermalStorageType( uValue=0.317, uOffset=0.05, uValueInner=3.064, uValueOuter=0.323, capacityInKiloJoulePerSquareMeter=182.0)
_ground_floor_parquet     = ThermalStorageType( uValue=0.310, uOffset=0.05, uValueInner=2.529, uValueOuter=0.323, capacityInKiloJoulePerSquareMeter=168.0)

_ground_ceiling           = ThermalStorageType( uValue=0.610, uOffset=0   , capacityInKiloJoulePerSquareMeter=308.0 )

_outer_36_wall            = ThermalStorageType( uValue=0.233, uOffset=0.05, capacityInKiloJoulePerSquareMeter=83.0 )
_outer_24_wall            = ThermalStorageType( uValue=0.345, uOffset=0.05, capacityInKiloJoulePerSquareMeter=59.0 )

_inner_garage_wall        = ThermalStorageType( uValue=0.230, uOffset=0   , capacityInKiloJoulePerSquareMeter=77.0 )
_inner_11_wall            = ThermalStorageType( uValue=0.864, uOffset=0   , capacityInKiloJoulePerSquareMeter=43.0 )
_inner_17_wall            = ThermalStorageType( uValue=0.558, uOffset=0   , capacityInKiloJoulePerSquareMeter=57.0 )

_first_floor              = ThermalStorageType( uValue=0.610, uOffset=0   , capacityInKiloJoulePerSquareMeter=136.0 )
_first_ceiling            = ThermalStorageType( uValue=0.186, uOffset=0.05, capacityInKiloJoulePerSquareMeter=9.30 )
_first_sloping_ceiling    = ThermalStorageType( uValue=0.186, uOffset=0.05, capacityInKiloJoulePerSquareMeter=9.30 )

_attic_floor              = ThermalStorageType( uValue=0.186, uOffset=0   , capacityInKiloJoulePerSquareMeter=1.7 )

_main_door                = ThermalBridgeType( uValue=1.400, uOffset=0.08 )
_utilityroom_garage_door  = ThermalBridgeType( uValue=1.700, uOffset=0.08 )
_outer_window             = ThermalBridgeType( uValue=0.970, uOffset=0.05 )

#_outer_shutter            = ThermalBridgeType( uValue=0.34 , uOffset=0.05 )

_first_sloping_window     = ThermalBridgeType( uValue=1.400, uOffset=0.1 )

# https://de.wikipedia.org/wiki/W%C3%A4rmedurchgangskoeffizient
_garage_window            = ThermalBridgeType( uValue=2.0  , uOffset=0.1 )
_garage_door              = ThermalBridgeType( uValue=3.49 , uOffset=0.1 )

_first_floor_height = 2.57
_second_floor_height = 2.45
_attic_floor_height = 2.10

BuildingConfig = [
    Room(
        name='lGF_Garage',
        ventilation=False,
        volume=54.0702 * _attic_floor_height / 2.0,
        walls=[
            Wall(direction='floor', area=27.456025, type=_attic_floor),
            Wall(direction='ceiling', area=27.456025, type=_first_sloping_ceiling),
            Wall(direction='west', area=5.319, type=_outer_24_wall),
            Wall(direction='north', area=4.18, type=_inner_garage_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=3.509, type=_inner_garage_wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.5, type=_inner_garage_wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.85, type=_inner_garage_wall,bound="lGF_Guesttoilet"),
            Wall(direction='east', area=5.21, type=_outer_24_wall),
            Wall(direction='south', area=17.039, type=_outer_24_wall)
        ],
        transitions=[
            Window(direction='west', area=0.6, type=_garage_window),
            Door(direction='west', area=1.880625, type=_garage_door),
            Door(direction='east', area=1.880625, type=_garage_door)
        ]
    ),
    Room(
        name='lGF_Guesttoilet',
        ventilation=True,
        additionalRadiator=True,
        heatingVolume=45.0, # these and all following volume flow rates are based on calculations of the hydraulic balancing calculation.
        volume=4.92445 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=6.29125, type=_ground_floor_tiles),
            Wall(direction='ceiling', area=6.29125, type=_ground_ceiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner_11_wall, bound="lGF_Utilityroom"),
            Wall(direction='north', area=3.4949, type=_inner_17_wall, bound="lGF_Corridor"),
            Wall(direction='east', area=9.14345, type=_outer_36_wall),
            Wall(direction='south', area=5.0225, type=_inner_garage_wall, bound="lGF_Garage")
        ],
        transitions=[
            Window(direction='east', area=1.045, type=_outer_window, contactItem='pGF_Guesttoilet_Openingcontact_Window_State', shutterItem='pGF_Guesttoilet_Shutter_Control', shutterArea=0.1292)
        ]
    ),
    Room(
        name='lGF_Utilityroom',
        ventilation=True,
        # TODO check
        #heatingVolume=27.04,
        volume=7.816325 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=8.9875, type=_ground_floor_tiles),
            Wall(direction='ceiling', area=8.9875, type=_ground_ceiling, bound="lFF_Bathroom"),
            Wall(direction='west', area=10.31765, type=_inner_11_wall, bound="lGF_Boxroom"),
            Wall(direction='north', area=5.39615, type=_inner_17_wall, bound="lGF_Corridor"),
            Wall(direction='east', area=10.31765, type=_inner_11_wall, bound="lGF_Guesttoilet"),
            Wall(direction='south', area=5.294375, type=_inner_garage_wall, bound="lGF_Garage")
        ],
        transitions=[
            Door(direction='south', area=1.880625, type=_utilityroom_garage_door, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Boxroom',
        ventilation=True,
        volume=4.72615 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=5.734025, type=_ground_floor_tiles),
            Wall(direction='ceiling', area=5.734025, type=_ground_ceiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='west', area=8.5388, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='north', area=4.57765, type=_inner_17_wall, bound="lGF_Livingroom"),
            Wall(direction='east', area=10.31765, type=_inner_11_wall, bound="lGF_Utilityroom"),
            Wall(direction='south', area=4.57765, type=_inner_garage_wall, bound="lGF_Garage")
        ]
    ),
    Room(
        name='lGF_Livingroom',
        ventilation=True,
        heatingVolume=108.0 + 108.0 + 60.0,
        volume=37.9957 * _first_floor_height + 10.7406 * _first_floor_height,
        walls=[
            # Kitchen
            Wall(direction='floor', area=12.999225, type=_ground_floor_parquet),
            Wall(direction='ceiling', area=12.999225, type=_ground_ceiling, bound="lFF_Bedroom"), # Dressingroom
            Wall(direction='east', area=8.789925, type=_inner_17_wall, bound="lGF_Boxroom"),
            Wall(direction='south', area=4.6781, type=_inner_garage_wall, bound="lGF_Garage"),
            Wall(direction='south', area=5.453, type=_outer_36_wall),
            Wall(direction='west', area=8.069575, type=_outer_36_wall),
            #Wall(direction='north', area=4.57765, type=_inner_17_wall),

            # Livingroom
            Wall(direction='floor', area=42.4732875, type=_ground_floor_parquet),
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
        ventilation=True,
        heatingVolume=90.0,
        volume=11.53445 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=13.5891, type=_ground_floor_parquet),
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
        ventilation=False,
        heatingVolume=54.0,
        volume=11.3076 * _first_floor_height,
        walls=[
            Wall(direction='floor', area=12.9843, type=_ground_floor_tiles),
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
        ventilation=False,
        heatingVolume=42.0,
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
        ventilation=True,
        heatingVolume=45.0,
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
        ventilation=True,
        heatingVolume=45.0,
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
        ventilation=True,
        heatingVolume=42.0 + 42.0,
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
        ]
    ),
    Room(
        name='lFF_Bathroom',
        ventilation=True,
        additionalRadiator=True,
        heatingVolume=42.0,
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
        ventilation=True,
        volume=54.0702 * _attic_floor_height / 2.0,
        walls=[
            # To simplify things: calculate it only for the bedroom, rather than individually for each of the rooms below it. The 'area' value corresponds to the combined floor area of ​​all the rooms underneath.
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
