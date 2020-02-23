from core.triggers import CronTrigger
from custom.helper import rule, getNow, getItemState, getItemLastUpdate, postUpdateIfChanged, itemLastUpdateOlderThen
from custom.model.heating import Heating
from custom.model.house import ThermalStorageType, ThermalBridgeType, Wall, Door, Window, Room

from org.joda.time.format import DateTimeFormat
from core.actions import Transformation

OFFSET_FORMATTER = DateTimeFormat.forPattern("HH:mm")

Heating.cloudCoverFC8Item = "Cloud_Cover_Forecast8"
Heating.cloudCoverFC4Item = "Cloud_Cover_Forecast4"
Heating.cloudCoverItem = "Cloud_Cover_Current"

Heating.temperatureGardenFC8Item = "Temperature_Garden_Forecast8"
Heating.temperatureGardenFC4Item = "Temperature_Garden_Forecast4"
Heating.temperatureGardenItem = "Heating_Temperature_Outdoor" # Temperature_Garden
Heating.temperatureGarageItem = "Temperature_FF_Garage"
Heating.temperatureAtticItem = "Heating_Temperature_Outdoor"

Heating.ventilationFilterRuntimeItem = "Ventilation_Filter_Runtime"

Heating.ventilationLevelItem = "Ventilation_Outgoing"
Heating.ventilationOutgoingTemperatureItem = "Ventilation_Outdoor_Outgoing_Temperature"
Heating.ventilationIncommingTemperatureItem = "Ventilation_Outdoor_Incoming_Temperature"

Heating.heatingCircuitPumpSpeedItem = "Heating_Circuit_Pump_Speed"
Heating.heatingTemperaturePipeOutItem = "Heating_Temperature_Pipe_Out"
Heating.heatingTemperaturePipeInItem = "Heating_Temperature_Pipe_In"

Heating.holidayStatusItem = "State_Holidays_Active"
 
_groundFloor = ThermalStorageType( capacity=164.0, uValue=0.320, uOffset=0.08, factor=0.60, referenceTemperatureItem=Heating.temperatureGardenItem )
_groundCeiling = ThermalStorageType( capacity=308.0 )

_outerWall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )
_garageWall = ThermalStorageType( capacity=77.0, uValue=0.234, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGarageItem )

_inner11Wall = ThermalStorageType( capacity=87.0 / 2.0 )
_inner17Wall = ThermalStorageType( capacity=111.0 / 2.0 )

_mainDoor = ThermalBridgeType( uValue=1.400, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )
_garageDoor = ThermalBridgeType( uValue=1.700, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGarageItem )
_outerWindow = ThermalBridgeType( uValue=0.970, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )

_outerShutter = ThermalBridgeType( uValue=0.34, uOffset=0.08, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )

_firstFloor = ThermalStorageType( capacity=136.0 )
_firstCeiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0, referenceTemperatureItem=Heating.temperatureAtticItem )
_firstSlopingCeiling = ThermalStorageType( capacity=9.30, uValue=0.186, uOffset=0.1, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )
_firstSlopingWindow = ThermalBridgeType( uValue=1.400, uOffset=0.1, factor=1.0, referenceTemperatureItem=Heating.temperatureGardenItem )

_atticFloor = ThermalStorageType( capacity=1.7 )

_firstFloorHeight = 2.57
_secondFloorHeight = 2.45
_atticFloorHeight = 2.10

#_maxVolume = 1.2 # 1200l max Volumenstrom of a Vitodens 200-W Typ B2HA with 13kW
Heating.maxHeatingVolume = 0.584 # 584l Nenn-Umlaufwassermenge of a Vitodens 200-W Typ B2HA with 13kW

Heating.radiatedThermalStorageType = _outerWall

Heating.rooms = [
    Room(
        name='FF Guest WC',
        temperatureSensorItem='Temperature_FF_GuestWC',
        temperatureTargetItem='Temperature_FF_GuestWC_Target',
        heatingBufferItem='Heating_FF_GuestWC_Charged',
        heatingCircuitItem='Heating_FF_GuestWC_Circuit',
        heatingArea=4.92445,
        volume=4.92445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=6.29125, type=_groundFloor),
            Wall(direction='ceiling', area=6.29125, type=_groundCeiling),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="FF Utilityroom"),
            Wall(direction='north', area=3.4949, type=_inner17Wall, bound="FF Floor"),
            Wall(direction='east', area=9.14345, type=_outerWall),
            Wall(direction='south', area=5.0225, type=_garageWall)
        ],
        transitions=[
            Window(direction='east', area=1.045, type=_outerWindow, contactItem='Window_FF_GuestWC', shutterItem='Shutters_FF_GuestWC', shutterArea=0.1292)
        ]
    ),
    Room(
        name='FF Utilityroom',
        temperatureSensorItem='Temperature_FF_Utilityroom',
        #heatingArea=3.0,
        volume=7.816325 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=8.9875, type=_groundFloor),
            Wall(direction='ceiling', area=8.9875, type=_groundCeiling),
            Wall(direction='west', area=10.31765, type=_inner11Wall, bound="FF Boxroom"),
            Wall(direction='north', area=5.39615, type=_inner17Wall, bound="FF Floor"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="FF Guest WC"),
            Wall(direction='south', area=5.294375, type=_garageWall)
        ],
        transitions=[
            Door(direction='south', area=1.880625, type=_garageDoor)
        ]
    ),
    Room(
        name='FF Boxroom',
        temperatureSensorItem='Temperature_FF_Boxroom',
        volume=4.72615 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=5.734025, type=_groundFloor),
            Wall(direction='ceiling', area=5.734025, type=_groundCeiling),
            Wall(direction='west', area=8.5388, type=_inner17Wall, bound="FF Livingroom"),
            Wall(direction='north', area=4.57765, type=_inner17Wall, bound="FF Livingroom"),
            Wall(direction='east', area=10.31765, type=_inner11Wall, bound="FF Utilityroom"),
            Wall(direction='south', area=4.57765, type=_garageWall)
        ]
    ),
    Room(
        name='FF Livingroom',
        temperatureSensorItem='Temperature_FF_Livingroom',
        temperatureTargetItem='Temperature_FF_Livingroom_Target',
        heatingBufferItem='Heating_FF_Livingroom_Charged',
        heatingCircuitItem='Heating_FF_Livingroom_Circuit',
        heatingArea=37.9957 + 10.7406,
        volume=37.9957 * _firstFloorHeight + 10.7406 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=12.999225, type=_groundFloor),
            Wall(direction='ceiling', area=12.999225, type=_groundCeiling),
            Wall(direction='east', area=8.789925, type=_inner17Wall, bound="FF Boxroom"),
            Wall(direction='south', area=3.0, type=_garageWall),
            Wall(direction='south', area=7.1311, type=_outerWall),
            Wall(direction='west', area=8.069575, type=_outerWall),
            #Wall(direction='north', area=4.57765, type=_inner17Wall),

            Wall(direction='floor', area=42.4732875, type=_groundFloor),
            Wall(direction='ceiling', area=42.4732875, type=_groundCeiling),
            Wall(direction='south', area=3.393775, type=_outerWall),
            Wall(direction='west', area=9.292675, type=_outerWall),
            Wall(direction='north', area=18.92765, type=_outerWall),
            Wall(direction='east', area=17.93755, type=_inner17Wall, bound="FF Floor"), # TODO better calculation
            #Wall(direction='east', area=10.31765, type=_inner17Wall, bound="FF Guestroom"), # TODO better calculation
            Wall(direction='south', area=6.177675, type=_inner17Wall, bound="FF Boxroom")
        ],
        transitions=[
            Window(direction='west', area=2.2, type=_outerWindow, contactItem='Window_FF_Kitchen', shutterItem='Shutters_FF_Kitchen', shutterArea=0.2992, radiationArea=0.645*1.01*2.0, sunProtectionItem="State_Sunprotection_Livingroom"),
            Window(direction='west', area=5.8232, type=_outerWindow, contactItem='Window_FF_Livingroom_Terrace', shutterItem='Shutters_FF_Livingroom_Terrace', shutterArea=0.4267, radiationArea=0.625*2.13*3.0),
            Window(direction='west', area=4.0832, type=_outerWindow, contactItem='Window_FF_Livingroom_Couch', shutterItem='Shutters_FF_Livingroom_Couch', shutterArea=0.2992, radiationArea=0.625*2.13*2.0)
        ]
    ),
    Room(
        name='FF Guestroom',
        temperatureSensorItem='Temperature_FF_Guestroom',
        temperatureTargetItem='Temperature_FF_Guestroom_Target',
        heatingBufferItem='Heating_FF_Guestroom_Charged',
        heatingCircuitItem='Heating_FF_Guestroom_Circuit',
        heatingArea=11.53445,
        volume=11.53445 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=13.5891, type=_groundFloor),
            Wall(direction='ceiling', area=13.5891, type=_groundCeiling),
            Wall(direction='west', area=10.31765, type=_inner17Wall, bound="FF Livingroom"),
            Wall(direction='north', area=10.8486, type=_outerWall),
            Wall(direction='east', area=7.9847, type=_outerWall),
            Wall(direction='south', area=9.06975, type=_inner17Wall, bound="FF Floor")
        ],
        transitions=[
            Window(direction='east', area=2.07625, type=_outerWindow, contactItem='Window_FF_Guestroom', shutterItem='Shutters_FF_Guestroom', shutterArea=0.2567)
        ]
    ),
    Room(
        name='FF Floor',
        temperatureSensorItem='Temperature_FF_Floor',
        temperatureTargetItem='Temperature_FF_Floor_Target',
        heatingBufferItem='Heating_FF_Floor_Charged',
        heatingCircuitItem='Heating_FF_Floor_Circuit',
        heatingArea=5.6538,
        volume=11.3076 * _firstFloorHeight,
        walls=[
            Wall(direction='floor', area=12.9843, type=_groundFloor),
            Wall(direction='ceiling', area=2.0524125, type=_groundCeiling),
            Wall(direction='west', area=7.0746, type=_inner17Wall, bound="FF Livingroom"),
            Wall(direction='north', area=9.06975, type=_inner17Wall, bound="FF Guestroom"),
            Wall(direction='east', area=5.19525, type=_outerWall),
            Wall(direction='south', area=7.54215, type=_inner17Wall, bound="FF Guest WC")   # TODO better calculation
            #Wall(direction='south', area=7.54215, type=_inner17Wall, bound="FF Utilityroom")
        ],
        transitions=[
            Door(direction='east', area=4.6632, type=_mainDoor, contactItem='Door_FF_Floor')
        ]
    ),
    Room(
        name='SF Floor',
        temperatureSensorItem='Temperature_SF_Floor',
        temperatureTargetItem='Temperature_SF_Floor_Target',
        heatingBufferItem='Heating_SF_Floor_Charged',
        heatingCircuitItem='Heating_SF_Floor_Circuit',
        heatingArea=4.0,
        volume=18.1926 * _secondFloorHeight - 4.3968,
        walls=[
            Wall(direction='floor', area=9.2315625, type=_firstFloor),
            Wall(direction='ceiling', area=14.1436125, type=_firstCeiling),
            Wall(direction='west', area=7.77045, type=_inner11Wall),
            Wall(direction='north', area=10.2148, type=_inner17Wall),
            Wall(direction='east', area=3.435, type=_outerWall),
            Wall(direction='east', area=8.026, type=_firstSlopingCeiling),
            Wall(direction='south', area=11.99365, type=_inner17Wall)
        ],
        transitions=[
            Window(direction='east', area=0.7676, type=_firstSlopingWindow)
        ]
    ),
    Room(
        name='SF Child 1',
        temperatureSensorItem='Temperature_SF_Child1',
        temperatureTargetItem='Temperature_SF_Child1_Target',
        heatingBufferItem='Heating_SF_Child1_Charged',
        heatingCircuitItem='Heating_SF_Child1_Circuit',
        heatingArea=13.036325,
        volume=13.036325 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=16.626875, type=_firstFloor),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling),
            Wall(direction='west', area=9.9941, type=_inner11Wall),
            Wall(direction='north', area=8.1533, type=_outerWall),
            Wall(direction='east', area=3.595, type=_outerWall),
            Wall(direction='east', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='south', area=8.51865, type=_inner17Wall)
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='Window_SF_Child1', shutterItem='Shutters_SF_Child1', shutterArea=0.2567)
        ]
    ),
    Room(
        name='SF Child 2',
        temperatureSensorItem='Temperature_SF_Child2',
        temperatureTargetItem='Temperature_SF_Child2_Target',
        heatingBufferItem='Heating_SF_Child2_Charged',
        heatingCircuitItem='Heating_SF_Child2_Circuit',
        heatingArea=14.99575,
        volume=14.99575 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=17.07625, type=_firstFloor),
            Wall(direction='ceiling', area=10.7760125, type=_firstCeiling),
            Wall(direction='west', area=3.595, type=_outerWall),
            Wall(direction='west', area=9.2032, type=_firstSlopingCeiling),
            Wall(direction='north', area=8.5008, type=_outerWall),
            Wall(direction='east', area=9.9941, type=_inner11Wall),
            Wall(direction='south', area=8.86615, type=_inner17Wall)
        ],
        transitions=[
            Window(direction='north', area=1.8875, type=_outerWindow, contactItem='Window_SF_Child2', shutterItem='Shutters_SF_Child2', shutterArea=0.2567)
        ]
    ),
    Room(
        name='SF Bedroom',
        temperatureSensorItem='Temperature_SF_Bedroom',
        temperatureTargetItem='Temperature_SF_Bedroom_Target',
        heatingBufferItem='Heating_SF_Bedroom_Charged',
        heatingCircuitItem='Heating_SF_Bedroom_Circuit',
        heatingArea=14.3929,
        volume=14.3929 * _secondFloorHeight,
        walls=[
            Wall(direction='floor', area=16.3125, type=_firstFloor),
            Wall(direction='ceiling', area=16.3125, type=_firstCeiling),
            Wall(direction='west', area=5.9851, type=_outerWall),
            Wall(direction='north', area=12.51, type=_inner17Wall),
            Wall(direction='east', area=8.03455, type=_inner11Wall),
            Wall(direction='south', area=3.28735, type=_outerWall),
            Wall(direction='south', area=0.5, type=_firstSlopingCeiling)
        ],
        transitions=[
            Window(direction='west', area=3.1375, type=_outerWindow, contactItem='Window_SF_Bedroom', shutterItem='Shutters_SF_Bedroom', shutterArea=0.4267, radiationArea=0.615*1.00*3.0, sunProtectionItem="State_Sunprotection_Bedroom")
        ]
    ),
    Room(
        name='SF Dressingroom',
        temperatureSensorItem='Temperature_SF_Dressingroom',
        temperatureTargetItem='Temperature_SF_Dressingroom_Target',
        heatingBufferItem='Heating_SF_Dressingroom_Charged',
        heatingCircuitItem='Heating_SF_Dressingroom_Circuit',
        heatingArea=14.88435,
        volume=14.88435 * _secondFloorHeight - 4.6016,
        walls=[
            Wall(direction='floor', area=16.660625, type=_firstFloor),
            Wall(direction='ceiling', area=10.40850625, type=_firstCeiling),
            Wall(direction='west', area=3.5075, type=_outerWall),
            Wall(direction='west', area=8.9792, type=_firstSlopingCeiling),
            Wall(direction='north', area=3.63485, type=_inner17Wall),
            Wall(direction='east', area=9.9941, type=_inner11Wall),
            Wall(direction='south', area=9.0333, type=_outerWall)
        ],
        transitions=[
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='Window_SF_Dressingroom', shutterItem='Shutters_SF_Dressingroom', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="State_Sunprotection_Dressingroom")
        ]
    ),
    Room(
        name='SF Bathroom',
        temperatureSensorItem='Temperature_SF_Bathroom',
        temperatureTargetItem='Temperature_SF_Bathroom_Target',
        heatingBufferItem='Heating_SF_Bathroom_Charged',
        heatingCircuitItem='Heating_SF_Bathroom_Circuit',
        heatingArea=6.0,
        volume=12.51273 * _secondFloorHeight - 2.5884,
        walls=[
            Wall(direction='floor', area=14.469875, type=_firstFloor),
            Wall(direction='ceiling', area=10.3266375, type=_firstCeiling),
            Wall(direction='west', area=9.9941, type=_inner11Wall),
            Wall(direction='north', area=7.4633, type=_inner17Wall),
            Wall(direction='east', area=5.033, type=_outerWall),
            Wall(direction='east', area=5.1768, type=_firstSlopingCeiling),
            Wall(direction='south', area=7.63045, type=_outerWall)
        ],
        transitions=[
            Window(direction='south', area=1.41875, type=_outerWindow, contactItem='Window_SF_Bathroom', shutterItem='Shutters_SF_Bathroom', shutterArea=0.19295, radiationArea=0.86*1.00, sunProtectionItem="State_Sunprotection_Bathroom")
        ]
    ),
    Room(
        name='SF Attic',
        temperatureSensorItem='Temperature_SF_Attic',
        volume=54.0702 * _atticFloorHeight / 2.0,
        walls=[
            Wall(direction='floor', area=59.871875, type=_atticFloor),
            Wall(direction='ceiling', area=49.9872093014803 + 49.9872093014803, type=_firstSlopingCeiling),
            Wall(direction='west', area=9.9941, type=_outerWall),
            Wall(direction='north', area=5.91675, type=_outerWall),
            #Wall(direction='east', area=5.033, type=_outerWall),
            Wall(direction='south', area=5.01995, type=_outerWall)
        ],
        transitions=[
            Window(direction='east', area=0.7676, type=_firstSlopingWindow),
            Window(direction='south', area=0.7676, type=_outerWindow, contactItem='Window_SF_Attic', shutterItem='Shutters_SF_Attic', shutterArea=0.19295, radiationArea=0.72*1.00, sunProtectionItem="State_Sunprotection_Attic")
        ]
    )
]

Heating.allowedRooms = {'FF Kitchen': True, 'FF Livingroom': True}
                       
Heating.init()

@rule("heating_control_new.py")
class TestRule():
    def __init__(self):
        self.triggers = [CronTrigger("*/15 * * * * ?")]
        self.activeHeatingOperatingMode = -1

    def execute(self, module, input):
        now = getNow()
        currentOperatingMode = getItemState("Heating_Operating_Mode").intValue()
        lastHeatingChange = getItemLastUpdate("Heating_Demand")

        heating = Heating(self.log)
        cr, hhs = heating.calculate(currentOperatingMode == 2,lastHeatingChange, 60/15)    
        
        heatingNeeded = hhs.isHeatingNeeded()
        
        for room in filter( lambda room: room.getHeatingCircuitItem() != None,Heating.rooms):
            
            rs = cr.getRoomState(room.getName())
            # update heating buffer
            totalChargeLevel = rs.getHeatingBuffer()
            #postUpdateIfChanged( room.getHeatingBufferItem(), 0 )
            postUpdateIfChanged( room.getHeatingBufferItem(), totalChargeLevel )

            rhs = hhs.getHeatingState(room.getName())
            if not heatingNeeded or rhs.getHeatingDemandEnergy() > 0:
                #postUpdateIfChanged(room.getHeatingCircuitItem(),ON)
                pass
            else:
                #postUpdateIfChanged(room.getHeatingCircuitItem(),OFF)
                pass
              
        heatingDemand = ON if heatingNeeded else OFF
        #postUpdateIfChanged("Heating_Demand", heatingDemand )

        lastUpdateBeforeInMinutes = int( round( ( now.getMillis() - lastHeatingChange.getMillis() ) / 1000.0 / 60.0 ) )
        lastHeatingChangeFormatted = OFFSET_FORMATTER.print(lastHeatingChange)
        lastUpdateBeforeFormatted = lastUpdateBeforeInMinutes if lastUpdateBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastUpdateBeforeInMinutes, 60));
        self.log.info(u"\tDemand  : {} since {} • {} min. ago".format(heatingDemand, lastHeatingChangeFormatted, lastUpdateBeforeFormatted) )
        
        self.setSunStates(cr)
        
        # TODO enable control heating system
        #self.controlHeating(currentOperatingMode,heatingNeeded)  

    def setSunStates(self, cr ):
      
        effectiveSouthRadiation = cr.getSunSouthRadiation() / 60.0
        effectiveWestRadiation = cr.getSunWestRadiation() / 60.0
        
        #self.log.info(u"{} {}".format(effectiveSouthRadiation,effectiveWestRadiation))
        
        if effectiveSouthRadiation > 0.0 or effectiveWestRadiation > 0.0:

            currentOutdoorTemperature = cr.getReferenceTemperature()

            fallbackTargetTemperature = cr.getRoomState("FF Livingroom").getTargetTemperature()
          
            for room in Heating.rooms:
                rs = cr.getRoomState(room.getName())
              
                for transition in room.transitions:
                    if not isinstance(transition,Window) or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
                        continue
                      
                    currentRoomTemperature = rs.getCurrentTemperature()

                    targetRoomTemperature = rs.getTargetTemperature()
                    if targetRoomTemperature == None:
                        targetRoomTemperature = fallbackTargetTemperature
                        
                    targetRoomTemperature = targetRoomTemperature - 1.0
                    
                    effectiveRadiation = effectiveSouthRadiation if transition.getDirection() == 'south' else effectiveWestRadiation

                    if getItemState(transition.getSunProtectionItem()) == ON:
                        if effectiveRadiation < 3.7 or currentRoomTemperature < targetRoomTemperature or currentOutdoorTemperature < targetRoomTemperature:
                            postUpdate(transition.getSunProtectionItem(), OFF )
                            self.log.info(u"DEBUG: SP switching off")
                        #else:
                        #    self.log.info(u"SP still needed")
                    elif effectiveRadiation > 3.8 and currentRoomTemperature >= targetRoomTemperature and currentOutdoorTemperature >= targetRoomTemperature:
                        postUpdate(transition.getSunProtectionItem(), ON )
                        self.log.info(u"DEBUG: SP switching on")
                    #else:
                    #   self.log.info(u"SP not needed")

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
        
        currentOperatingModeUpdate = getItemLastUpdate("Heating_Operating_Mode")
        lastUpdateBeforeInMinutes = int( round( ( now.getMillis() - currentOperatingModeUpdate.getMillis() ) / 1000.0 / 60.0 ) )
        lastHeatingChangeFormatted = OFFSET_FORMATTER.print(currentOperatingModeUpdate)
        lastUpdateBeforeFormatted = lastUpdateBeforeInMinutes if lastUpdateBeforeInMinutes < 60 else '{:02d}:{:02d}'.format(*divmod(lastUpdateBeforeInMinutes, 60));
        
        self.log.info(u"Active  : {} • since {} • {} min. ago".format(Transformation.transform("MAP", "heating_de.map", str(currentOperatingMode) ),lastHeatingChangeFormatted,lastUpdateBeforeFormatted) )
        
        # Nur WW
        if currentOperatingMode == 1:
            # Temperatur sollte seit XX min nicht OK sein und 'Nur WW' sollte mindestens XX min aktiv sein um 'flattern' zu vermeiden
            if isHeatingRequested:
                isRunningLongEnough = itemLastUpdateOlderThen("Heating_Operating_Mode", now.minusMinutes(Heating.minOnlyWwTime))
                
                if forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode", self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.minOnlyWwTime - int( round( ( now.getMillis() - currentOperatingModeUpdate.getMillis() ) / 1000.0 / 60.0 ) )
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Heizen mit WW{}{}".format(delayedMsg,forceRetryMsg))

        # Heizen mit WW
        elif currentOperatingMode == 2:
            currentPowerState = getItemState("Heating_Power").intValue()
            
            # Wenn Heizkreispumpe auf 0 dann ist Heizen zur Zeit komplett deaktiviert (zu warm draussen) oder Brauchwasser wird aufgeheizt
            #if Heating_Circuit_Pump_Speed.state > 0:
            # Temperatur sollte seit XX min OK sein und Brenner sollte entweder nicht laufen oder mindestens XX min am Stück gelaufen sein
            if not isHeatingRequested:
                isRunningLongEnough = itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(Heating.minHeatingTime))
                
                if currentPowerState == 0 or forceRetry or isRunningLongEnough:
                    self.activeHeatingOperatingMode = 1
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                else:
                    runtimeToGo = Heating.minHeatingTime - int( round( ( now.getMillis() - currentOperatingModeUpdate.getMillis() ) / 1000.0 / 60.0 ) )
                    delayedMsg = u" in {} min.".format(runtimeToGo)

                self.log.info(u"Switch  : Nur WW{}{}".format(delayedMsg,forceRetryMsg))
                  
            # Brenner läuft nicht
            elif currentPowerState == 0:
                forceReducedMsg = None
                
                # No burner starts since a while
                if itemLastUpdateOlderThen("Heating_Power",now.minusMinutes(5)) and itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(5)):
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
                self.log.info(u"Switch  : Nur WW. Temperature reached max value{}".format(forceRetryMsg))
            else:
                lastReducedRuntime = self.getLastReductionTime( currentOperatingModeUpdate )
                if lastReducedRuntime > 0:
                    targetReducedTime = int( round(lastReducedRuntime * 2.0 / 1000.0 / 60.0, 0) )
                    if targetReducedTime > Heating.maxReducedTime:
                        targetReducedTime = Heating.maxReducedTime
                    elif targetReducedTime < Heating.minReducedTime:
                        # SHOULD NEVER HAPPEN !!!
                        self.log.error(u"MIN_REDUCED_TIME less then allowed. Was {}".format(targetReducedTime))
                        targetReducedTime = Heating.minReducedTime
                else:
                    targetReducedTime = Heating.minReducedTime
                                
                #self.log.info(u"E {}".format(targetReducedTime))
                    
                # Dauernd reduziert läuft seit mindestens XX Minuten
                if forceRetry or itemLastUpdateOlderThen("Heating_Operating_Mode",now.minusMinutes(targetReducedTime) ):
                    self.activeHeatingOperatingMode = 2
                    sendCommand("Heating_Operating_Mode",self.activeHeatingOperatingMode)
                elif not forceRetry:
                    runtimeToGo = targetReducedTime - int( round( ( now.getMillis() - currentOperatingModeUpdate.getMillis() ) / 1000.0 / 60.0 ) )
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
            if lastHeatingTime < MIN_HEATING_TIME * 60 * 1000:
                # mode before was "Reduziert"
                previousOperatingMode = getHistoricItemEntry("Heating_Operating_Mode",lastOperatingModeUpdate.minusSeconds(1))
                #self.log.info(u"C {}".format(previousOperatingMode.getState().intValue()))

                if previousOperatingMode.getState().intValue() == 3:
                    # letzt calculate last "reduziert" runtime and increase it by 2
                    previousOperatingModeUpdate = DateTime( previousOperatingMode.getTimestamp().getTime() ) 
                    lastReducedRuntime = lastOperatingModeUpdate.getMillis() - previousOperatingModeUpdate.getMillis()
                    
                    return lastReducedRuntime
        return 0  
                                                
             
