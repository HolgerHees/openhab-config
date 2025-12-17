from openhab import Registry, logger

from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper
from custom.flags import FlagHelper
from custom.heating.house import Window
from custom.heating.state import RoomState, HouseState, RoomHeatingState, HouseHeatingState
from custom.suncalculation import SunRadiation

from datetime import datetime, timedelta
from functools import reduce
import math
import json

from org.openhab.core.library.types import DecimalType as Java_DecimalType

import scope


class Heating():
    INFINITE_HEATING_TIME = 999.0 # const value for an invifinte heating time
    
    DEFAULT_NIGHT_REDUCTION = 2.0
    LAZY_OFFSET = 90 # Offset time until any heating has an effect

    MIN_HEATING_TIME = 15 # 'Heizen mit WW' should be active at least for 15 min.
    MIN_ONLY_WW_TIME = 15 # 'Nur WW' should be active at least for 15 min.

    MIN_REDUCED_TIME = 5
    MAX_REDUCED_TIME = 30

    OPEN_WINDOW_START_DURATION = 2
    LONG_OPEN_WINDOW_START_DURATION = 5

    DENSITY_AIR = 1.2041
    C_AIR = 1.005

    # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
    LEAKING_N50 = 1.0
    LEAKING_E = 0.07
    LEAKING_F = 15.0

    # To warmup 1 liter of water you need 4,182 Kilojoule
    # 1 Wh == 3,6 kJ
    # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
    HEATING_REFERENCE_ENERGY = 1162 # per Watt je m³/K

    forecast_cloud_cover_item_name = None
    forecast_temperature_garden_item_name = None

    current_cloud_cover_item_name = None
    current_temperature_garden_item_name = None

    ventilation_filter_runtime_item_name = None
    ventilation_level_item_name = None
    ventilation_outgoing_temperature_item_name = None
    ventilation_incomming_temperature_item_name = None
    
    heating_circuit_pump_speed_item_name = None
    heating_temperature_pipe_out_item_name = None
    heating_temperature_pipe_in_item_name = None
    
    precence_status_item_name = None
    holiday_status_item_name = None
    heating_mode_item_name = None

    forced_states_item_name = None
    
    total_volume = 0
    total_heating_volume = None
    
    temperature_sensor_item_name_placeholder = u"p{}_Air_Sensor_Temperature_Value"
    temperature_target_item_name_placeholder = u"p{}_Temperature_Desired"
    
    heating_hk_item_name_placeholder = u"p{}_Heating_HK"
    heating_circuit_item_name_placeholder = u"p{}_Heating_Circuit"
    heating_buffer_item_name_placeholder = u"p{}_Heating_Charged"
    heating_demand_item_name_placeholder = u"p{}_Heating_Demand"
    heating_target_temperature_item_name_placeholder = u"p{}_Heating_Temperature_Target"

    last_runtime = None
    
    rooms = []

    _forced_heatings = {}

    _rooms_by_name = {}
            
    _stable_temperature_references = {}

    # static status variables
    _open_window_contacts= {}
    
    @staticmethod
    def init(rooms):
        Heating.rooms = rooms

        for room in rooms:
            Heating._rooms_by_name[room.getName()] = room
    
        Heating.total_volume = reduce( lambda x,y: x+y, map( lambda x: x.getVolume(), Heating.rooms ) )
        Heating.total_heating_volume = reduce( lambda x,y: x+y, map( lambda x: x.getHeatingVolume(), filter( lambda room: room.getHeatingVolume() != None, Heating.rooms) ) )
        
    @staticmethod
    def getRooms():
        return Heating.rooms
   
    @staticmethod
    def getRoom(roomName):
        return Heating._rooms_by_name[roomName]

    @staticmethod
    def getTemperatureSensorItemName(room):
        return Heating.temperature_sensor_item_name_placeholder.format(room.getName()[1:])
      
    @staticmethod
    def getTemperatureTargetItemName(room):
        return Heating.temperature_target_item_name_placeholder.format(room.getName()[1:])
      
    @staticmethod
    def getHeatingBufferItemName(room):
        return Heating.heating_buffer_item_name_placeholder.format(room.getName()[1:])
      
    @staticmethod
    def getHeatingCircuitItemName(room):
        return Heating.heating_circuit_item_name_placeholder.format(room.getName()[1:])
      
    @staticmethod
    def getHeatingHKItemName(room):
        return Heating.heating_hk_item_name_placeholder.format(room.getName()[1:])

    @staticmethod
    def getHeatingTargetTemperatureItemName(room):
        return Heating.heating_target_temperature_item_name_placeholder.format(room.getName()[1:])
      
    @staticmethod
    def getHeatingDemandItemName(room):
        return Heating.heating_demand_item_name_placeholder.format(room.getName()[1:])

    def __init__(self,logger):
        self.logger = logger
        self.cache = {}
        self.now = datetime.now().astimezone()

    def getCachedStableItemKey(self, item_name, stable_since=10):
        return u"stable-{}-{}".format(item_name, stable_since)
    
    def getCachedStableItemFloat(self, item_name, stable_since=10):
        return self.getCachedStableItemState(item_name, stable_since).floatValue()

    def getCachedStableItemState(self, item_name, stable_since=10):
        key = self.getCachedStableItemKey(item_name, stable_since)
        if key not in self.cache:
            self.cache[key] = ToolboxHelper.getStableState(item_name, stable_since, self.now)
        return self.cache[key]

    def getCachedItemFloat(self, item_name):
        return self.getCachedItemState(item_name).floatValue()

    def getCachedItemInt(self, item_name):
        return self.getCachedItemState(item_name).intValue()

    def getCachedItemState(self, item_name):
        if item_name not in self.cache:
            self.cache[item_name] = Registry.getItemState(item_name)
        return self.cache[item_name]
      
    def cachedItemLastChangeOlderThen(self, item_name, minutes):
        key = u"update-{}-{}".format(item_name,minutes)
        if key not in self.cache:
            self.cache[key] = Registry.getItem(item_name).getLastStateChange() < self.now - timedelta(minutes=minutes)
        return self.cache[key]

    def getVentilationEnergy(self, temp_diff_offset):
        # *** Calculate power loss by ventilation ***
        _ventilationLevel = self.getCachedItemState(self.ventilation_level_item_name)
        if _ventilationLevel != scope.UNDEF:
            _ventilation_temp_diff = self.getCachedItemFloat(self.ventilation_outgoing_temperature_item_name) - self.getCachedItemFloat(self.ventilation_incomming_temperature_item_name)

            # apply outdoor temperature changes to ventilation in / out difference
            if temp_diff_offset != 0:
                ventilation_diff = temp_diff_offset / 4
                if _ventilation_temp_diff + ventilation_diff > 0:
                    _ventilation_temp_diff = _ventilation_temp_diff + ventilation_diff

            # Ventilation Energy
            # 15% => 40m/h		XX => ?
            # 100% => 350m/h		85 => 310
            _ventilation_volume = ( ( ( _ventilationLevel.intValue() - 15.0 ) * 310.0 ) / 85.0 ) + 40.0
            _ventilation_u_value = _ventilation_volume * self.DENSITY_AIR * self.C_AIR
            _ventilation_energy_in_kj = _ventilation_u_value * _ventilation_temp_diff

            return _ventilation_energy_in_kj * -1 if _ventilation_energy_in_kj != 0 else 0.0
        else:
            return 0.0
    
    def getLeakingEnergy(self, volume, current_temperature, outdoor_temperature):
        _leaking_temperature_diff = current_temperature - outdoor_temperature
        _leaking_volume = ( volume * self.LEAKING_N50 * self.LEAKING_E ) / ( 1 + ( self.LEAKING_F / self.LEAKING_E ) * ( ( ( 0.1 * 0.4 ) / self.LEAKING_N50 ) * ( ( 0.1 * 0.4 ) / self.LEAKING_N50 ) ) )
        _leaking_u_value = _leaking_volume * self.DENSITY_AIR * self.C_AIR
        _leaking_energy_in_kj = _leaking_u_value * _leaking_temperature_diff
        return _leaking_energy_in_kj * -1 if _leaking_energy_in_kj != 0 else 0.0

    def getCoolingEnergy(self, area, current_temperature, type, bound):
        if type.getUValue() != None:
            referenced_temperatur_item = Heating.getTemperatureSensorItemName(Heating.getRoom(bound)) if bound != None else Heating.current_temperature_garden_item_name
            reference_temperature = self.getCachedStableItemFloat(referenced_temperatur_item)
            temperature_difference = current_temperature - reference_temperature
            cooling_per_kelvin =( type.getUValue() + type.getUOffset() ) * area * type.getFactor()
            cooling_total = cooling_per_kelvin * temperature_difference
            return cooling_total * -1 if cooling_total != 0 else 0.0
        else:
            return 0.0
        
    def calculateWallCoolingAndRadiations(self, current_temperature, sun_south_radiation, sun_west_radiation, walls):
        outdoor_wall_cooling = indoor_wall_cooling = outdoor_wall_radiation = room_capacity = 0
        for wall in walls:
            cooling = self.getCoolingEnergy(wall.getArea(),current_temperature,wall.getType(),wall.getBound())
            if wall.getBound() == None:
                outdoor_wall_cooling = outdoor_wall_cooling + cooling
            else:
                indoor_wall_cooling = indoor_wall_cooling + cooling
            
            if wall.getBound() == None:
                if wall.getDirection() == 'south':
                    outdoor_wall_radiation = outdoor_wall_radiation + SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_south_radiation)
                elif wall.getDirection() == 'west':
                    outdoor_wall_radiation = outdoor_wall_radiation + SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_west_radiation)

            capacity = ( wall.getArea() * wall.getType().getCapacity() ) / 3.6 # converting kj into watt

            room_capacity = room_capacity + capacity

        return indoor_wall_cooling, outdoor_wall_cooling, outdoor_wall_radiation, room_capacity
        
    def calculateWindowCoolingAndRadiations(self, current_temperature, sun_south_radiation, sun_west_radiation, transitions, wall_cooling, is_forecast):
        closed_window_energy = window_radiation = open_window_count = 0
        for transition in transitions:
            cooling = self.getCoolingEnergy(transition.getArea(),current_temperature,transition.getType(),transition.getBound())
            closed_window_energy = closed_window_energy + cooling

            if transition.getContactItem() != None and self.getCachedItemState(transition.getContactItem()) == scope.OPEN:
                if self.cachedItemLastChangeOlderThen(transition.getContactItem(), 10 if is_forecast else 2):
                    open_window_count = open_window_count + 1

            if isinstance(transition,Window) and transition.getRadiationArea() != None:
                _shutterOpen = (is_forecast or transition.getShutterItem() == None or self.getCachedItemState(transition.getShutterItem()).intValue() == 0)
                if _shutterOpen:
                    if transition.getDirection() == 'south':
                        window_radiation = window_radiation + SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_south_radiation)
                    elif transition.getDirection() == 'west':
                        window_radiation = window_radiation + SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_west_radiation)
        
        open_window_energy = 0 if is_forecast else wall_cooling * open_window_count
            
        return closed_window_energy, open_window_energy, window_radiation, open_window_count
          
    def calculatePossibleHeatingEnergy(self, is_forecast):
        temperatures = []
        for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
            if is_forecast or room.getHeatingVolume() == None or self.getCachedItemState( Heating.getHeatingCircuitItemName(room) ) == scope.ON:
                temperatures.append( self.getCachedStableItemFloat( Heating.getTemperatureSensorItemName(room) ) )
        
        if len(temperatures) == 0:
            # Fallback is avg of all target temperatures
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
                temperatures.append( self.getCachedItemFloat( Heating.getTemperatureTargetItemName(room) ) )
            
        temperature_pipe_in = reduce( lambda x,y: x+y, temperatures ) / len(temperatures) + 7.0
        
        # 0.6 steilheit
        # niveau 12k
        # 20° => 37°                => 0 => 0°
        # -20^ => 60°               => 40 => 23°
        
        current_outdoor_temp = self.getCachedItemFloat( self.current_temperature_garden_item_name )
        
        if current_outdoor_temp > 20.0:
            temperature_pipe_out = 37.0
        elif current_outdoor_temp < -20.0:
            temperature_pipe_out = 60.0
        else:
            temperature_pipe_out = ( ( ( ( current_outdoor_temp - 20.0 ) * -1 ) * 23.0 / 40.0 ) + 37.0 ) * 0.95
            #test = ( ( ( ( current_outdoor_temp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.9
            #self.logger.info(u"-----> {}".format(test))
            #test = ( ( ( ( current_outdoor_temp - 20.0 ) * -1 ) * 11.0 / 40.0 ) + 36.0 ) * 0.95
            #self.logger.info(u"-----> {}".format(test))
            
        if temperature_pipe_out > 50.0:
            temperature_pipe_out = 50.0
                
        circulation_diff = temperature_pipe_out - temperature_pipe_in
            
        pump_speed = 80.0
        
        #debug_info = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulation_diff,1),round(temperature_pipe_out,1),round(temperature_pipe_in,1),pump_speed)
        #self.logger.info(debug_info)
        
        return circulation_diff, pump_speed
    
    def calculateHeatingEnergy(self, is_forecast):
        power = self.getCachedItemInt(self.heatingPower)
        pump_speed = self.getCachedItemInt(self.heating_circuit_pump_speed_item_name)
        if power == 0 or pump_speed == 0 or is_forecast:
            circulation_diff = 0
            pump_speed = 0
            debug_info = ""
            #Diff 9.1°C • VL 37.5°C • RL 28.4°C • 85.0% (FC)
            #self.logger.info( u"Diff {}°C • VL {}°C • RL {}°C • {}% (FC)".format(round(circulation_diff,1),round(temperature_pipe_out,1),round(temperature_pipe_in,1),pump_speed))
        else:
            temperature_pipe_out = self.getCachedItemFloat(self.heating_temperature_pipe_out_item_name)
            temperature_pipe_in = self.getCachedItemFloat(self.heating_temperature_pipe_in_item_name)
            circulation_diff = temperature_pipe_out - temperature_pipe_in
            
            #Diff 9.6°C • VL 38.9°C • RL 29.3°C • 85% (0.42 m³)
            debug_info = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulation_diff,1),round(temperature_pipe_out,1),round(temperature_pipe_in,1),pump_speed)

        return circulation_diff, pump_speed, debug_info

    def calculateHeatingRadiation(self, heating_volume_factor, room_heating_volume, circulation_diff, pump_speed):

        if room_heating_volume != None:
            pump_volume = ( room_heating_volume * heating_volume_factor * pump_speed ) / 100.0
            
            # pump_volume / 1000.0 => convert liter => m³
            heating_energy = self.HEATING_REFERENCE_ENERGY * (pump_volume / 1000.0) * circulation_diff
            
            return pump_volume, heating_energy
        else:
            return 0.0, 0.0
          
    def calculateHeatingVolumeFactor(self, is_forecast):
        if not is_forecast:
            active_heating_volume = 0
        
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
                if self.getCachedItemState( Heating.getHeatingCircuitItemName(room) ) == scope.ON:
                    active_heating_volume = active_heating_volume + room.getHeatingVolume()
                
            if active_heating_volume > 0:
                # if all circuits are active => then 100% of Heating.total_heating_volume are possible
                # if >0% of the circuits volume is active then 30.0% of self.total_heating_volume at 100%
                # if 50% of the circuits volume is active then 65.0% of self.total_heating_volume at 100%
                possible_heating_volume_in_percent = ( active_heating_volume * 70.0 / Heating.total_heating_volume ) + 30.0

                #self.logger.info(u"{} {} {}".format(possible_heating_volume_in_percent,active_heating_volume,Heating.total_heating_volume))

                return possible_heating_volume_in_percent / 100.0

        return 1.0
    
    def getOutdoorDependingReduction(self, cooling_energy):
        # more than zeor means cooling => no reduction
        if cooling_energy <= 0: return 0.0

        # less than zero means - sun heating
        # 18000 Watt => 300 W/min => max reduction
        if cooling_energy > 18000: return 2.0

        return ( cooling_energy * 2.0 ) / 18000.0

    def calculateOutdoorReduction(self, cooling_energy, cooling_energy_fc4, cooling_energy_fc8):
        # Current cooling should count full
        _outdoor_reduction = self.getOutdoorDependingReduction(cooling_energy)
        # Closed cooling forecast should count 90%
        _outdoor_reduction_fc4 = self.getOutdoorDependingReduction(cooling_energy_fc4) * 0.8
        # Cooling forecast in 8 hours should count 80%
        _outdoor_reduction_fc8 = self.getOutdoorDependingReduction(cooling_energy_fc8) * 0.6
        
        _outdoor_reduction = _outdoor_reduction + _outdoor_reduction_fc4 + _outdoor_reduction_fc8
        
        #self.logger.info(u"{} {} {}".format(cooling_energy,cooling_energy_fc4,cooling_energy_fc8))
        #self.logger.info(u"{} {} {}".format(_outdoor_reduction,_outdoor_reduction_fc4,_outdoor_reduction_fc8))
        
        #if _outdoor_reduction > 0.0: _outdoor_reduction = _outdoor_reduction + 0.1
        
        return round( _outdoor_reduction, 2 )
      
    def isNightModeTime(self, offset = None):
        reference = self.now + timedelta(minutes=offset) if offset != None else self.now
      
        day    = reference.weekday() # monday 0 until sunday 6
        hour   = reference.hour
        minute = reference.minute

        _night_mode_active = False
        
        _holidays_active = self.getCachedItemState(self.holiday_status_item_name) == scope.ON
        
        _is_morning = True if hour < 12 else False
        
        # Wakeup
        if _is_morning:
            # Monday - Friday
            if not _holidays_active and day <= 4:
                if hour < 5:
                #if hour < 5 or ( hour == 5 and minute <= 30 ):
                    _night_mode_active = True
            # Saturday and Sunday
            else:
                if hour < 7:
                #if hour < 8 or ( hour == 8 and minute <= 30 ):
                    _night_mode_active = True
        # Evening
        else:
            # Monday - Thursday and Sunday
            if not _holidays_active and day <= 3 or day == 6:
                if hour >= 22:
                #if hour >= 23 or ( hour == 22 and minute >= 30 ):
                    _night_mode_active = True
            # Friday and Saturday
            else:
                if hour >= 23:
                    _night_mode_active = True

        return _night_mode_active
      
    def isNightMode(self, is_heating_active):
        if self.now.hour > 19:
            offset = self.LAZY_OFFSET
            if not is_heating_active:
                offset = offset + self.MIN_HEATING_TIME
            return self.isNightModeTime( offset )
        
        if self.now.hour < 10:
            return self.isNightModeTime()
          
        return False
      
    def possibleColdFloorHeating(self, night_mode_active, last_heating_change):
        day = self.now.weekday() # monday 0 until sunday 6
        hour = self.now.hour
        
        _had_today_heating = last_heating_change.weekday() == day

        is_morning = hour < 12 and night_mode_active
        if is_morning:
            _had_morning_heating = _had_today_heating
            return not _had_morning_heating
        
        _presence_state_away = self.getCachedItemState(Heating.precence_status_item_name) == PresenceHelper.STATE_AWAY
        _evening_start_hours = (17 if day <= 4 and _presence_state_away else 16)
        is_evening = (hour == _evening_start_hours)
        if is_evening:
            _had_evening_heating = _had_today_heating and last_heating_change.hour >= _evening_start_hours
            return not _had_evening_heating
        
        return False
      
    def getColdFloorHeatingTime(self, last_update):
        # when was the last heating job
        last_update_before_in_minutes = int((last_update - self.now).total_seconds() / 60)
       
        maxMinutes = 90.0 if self.now.hour < 12 else 45.0
        
        # 0 => 0
        # 10 => 1
        factor = ( last_update_before_in_minutes / 60.0 ) / 10.0
        if factor > 1.0: factor = 1.0

        #https://rechneronline.de/funktionsgraphen/
        multiplier = ( math.pow( (factor-1), 2.0 ) * -1 ) + 1      #(x-1)^2*-1+1
        #multiplier = math.pow( (factor-1), 3.0 ) + 1              #(x-1)^3+1
    
        return ( maxMinutes * multiplier ) / 60.0

    def getCoolingAndRadiations(self, ref_garden_temperature, garden_temperature, cloud_cover, sun_radiation=None):
        time = self.now

        is_forecast = ref_garden_temperature != garden_temperature
        temp_diff_offset = ref_garden_temperature - garden_temperature

        possible_heating_circulation_diff, possible_heating_pump_speed = self.calculatePossibleHeatingEnergy(is_forecast)
        heating_circulation_diff, heating_pump_speed, heating_debug_info = self.calculateHeatingEnergy(is_forecast)
        heating_volume_factor = self.calculateHeatingVolumeFactor(is_forecast)
        
        current_total_ventilation_energy = self.getVentilationEnergy(temp_diff_offset) / 3.6 # converting kj into watt
        sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info = SunRadiation.getSunPowerPerHour(time, cloud_cover, sun_radiation)
        sun_south_radiationMax, sun_west_radiationMax, sun_radiation_max, sun_max_debug_info = SunRadiation.getSunPowerPerHour(time, 0)
        
        total_open_window_count = 0
        
        total_indoor_wall_energy = 0
        total_outdoor_wall_energy = 0
        total_outdoor_wall_radiation = 0
        total_ventilation_energy = 0
        total_leak_energy = 0
        total_window_energy = 0
        total_window_radiation = 0
        
        total_heating_volume = 0
        total_heating_radiation = 0
        total_possible_heating_volume = 0
        total_possible_heating_radiation = 0
        
        total_buffer_capacity = 0
        
        states = {}

        for room in Heating.rooms:            
            current_temperature = self.getCachedStableItemFloat(Heating.getTemperatureSensorItemName(room))
                          
            # *** WALL COOLING AND RADIATION ***
            indoor_wall_energy, outdoor_wall_energy, outdoor_wall_radiation, room_capacity = self.calculateWallCoolingAndRadiations(current_temperature, sun_south_radiation, sun_west_radiation, room.getWalls())

            # *** WINDOW COOLING AND RADIATION ***
            closed_window_energy, open_window_energy, window_radiation, open_window_count = self.calculateWindowCoolingAndRadiations(current_temperature, sun_south_radiation, sun_west_radiation, room.getTransitions(), outdoor_wall_energy, is_forecast)
            outdoor_wall_energy = outdoor_wall_energy + closed_window_energy
            
            if room.getHeatingVolume() != None:
                # *** HEATING RADIATION ***
                if heating_pump_speed == 0 or self.getCachedItemState( Heating.getHeatingCircuitItemName(room) ) != scope.ON:
                    heating_volume, heating_radiation = 0.0, 0.0
                else:
                    heating_volume, heating_radiation = self.calculateHeatingRadiation(heating_volume_factor, room.getHeatingVolume(), heating_circulation_diff, heating_pump_speed)
                
                possible_heating_volume, possible_heating_radiation = self.calculateHeatingRadiation(1.0, room.getHeatingVolume(), possible_heating_circulation_diff, possible_heating_pump_speed)
            else:
                heating_volume, heating_radiation = 0.0, 0.0
                possible_heating_volume, possible_heating_radiation = 0.0, 0.0

            #self.logger.info(u"{} {} {}".format(room.getName(),possible_heating_radiation))
            #self.logger.info(u"{} {} {} {} {}".format(room.getName(),possible_heating_volume,possible_heating_radiation,heating_volume_factor,room.getHeatingVolume()))

            # *** VENTILATION COOLING ***
            ventilation_energy = room.getVolume() * current_total_ventilation_energy / Heating.total_volume
            leak_energy = self.getLeakingEnergy(room.getVolume(), current_temperature, garden_temperature) / 3.6 # converting kj into watt
            
            #self.logger.info(u"{} {} {}".format(room.getName(),ventilation_energy,leak_energy))
                
            # summarize room values
            total_open_window_count = total_open_window_count + open_window_count
            total_buffer_capacity = total_buffer_capacity + room_capacity
            total_indoor_wall_energy = total_indoor_wall_energy + indoor_wall_energy
            total_outdoor_wall_energy = total_outdoor_wall_energy + outdoor_wall_energy
            total_outdoor_wall_radiation = total_outdoor_wall_radiation + outdoor_wall_radiation
            total_ventilation_energy = total_ventilation_energy + ventilation_energy
            total_leak_energy = total_leak_energy + leak_energy
            total_window_energy = total_window_energy + open_window_energy
            total_window_radiation = total_window_radiation + window_radiation
            total_heating_volume = total_heating_volume + heating_volume
            total_heating_radiation = total_heating_radiation + heating_radiation
            total_possible_heating_volume = total_possible_heating_volume + possible_heating_volume
            total_possible_heating_radiation = total_possible_heating_radiation + possible_heating_radiation

            # set room values
            room_state = RoomState()
            room_state.setName(room.getName())

            room_state.setOpenWindowCount(open_window_count)

            room_state.setBufferCapacity(room_capacity)

            room_state.setIndoorWallEnergy(indoor_wall_energy)
            room_state.setOutdoorWallEnergy(outdoor_wall_energy)
            room_state.setOutdoorWallRadiation(outdoor_wall_radiation)
            room_state.setVentilationEnergy(ventilation_energy)
            room_state.setLeakEnergy(leak_energy)
            room_state.setWindowEnergy(open_window_energy)
            room_state.setWindowRadiation(window_radiation)

            room_state.setHeatingVolume(heating_volume)
            room_state.setHeatingRadiation(heating_radiation)
            room_state.setPossibleHeatingVolume(possible_heating_volume)
            room_state.setPossibleHeatingRadiation(possible_heating_radiation)
            
            room_state.setCurrentTemperature(current_temperature)

            states[room.getName()] = room_state

        # set house values
        house_state = HouseState()
        house_state.setRoomStates(states)
        house_state.setReferenceTemperature(garden_temperature)

        house_state.setOpenWindowCount(total_open_window_count)

        house_state.setBufferCapacity(total_buffer_capacity)

        house_state.setIndoorWallEnergy(total_indoor_wall_energy)
        house_state.setOutdoorWallEnergy(total_outdoor_wall_energy)
        house_state.setOutdoorWallRadiation(total_outdoor_wall_radiation)
        house_state.setVentilationEnergy(total_ventilation_energy)
        house_state.setLeakEnergy(total_leak_energy)
        house_state.setWindowEnergy(total_window_energy)
        house_state.setWindowRadiation(total_window_radiation)

        house_state.setHeatingPumpSpeed(heating_pump_speed)
        house_state.setHeatingVolume(total_heating_volume)
        house_state.setHeatingRadiation(total_heating_radiation)
        house_state.setPossibleHeatingVolume(total_possible_heating_volume)
        house_state.setPossibleHeatingRadiation(total_possible_heating_radiation)
        house_state.setHeatingVolumeFactor(heating_volume_factor)
        house_state.setHeatingDebugInfo(heating_debug_info)

        house_state.setCloudCover(cloud_cover)
        house_state.setSunRadiation(sun_radiation)
        house_state.setSunRadiationMax(sun_radiation_max)
        house_state.setSunSouthRadiation(sun_south_radiation)
        house_state.setSunSouthRadiationMax(sun_south_radiationMax)
        house_state.setSunWestRadiation(sun_west_radiation)
        house_state.setSunWestRadiationMax(sun_west_radiationMax)
        house_state.setSunDebugInfo(sun_debug_info)

        return house_state
        
    def getHeatingDemand(self, room, rs, outdoor_reduction, night_reduction, is_heating_active):

        hs = RoomHeatingState()
        hs.setName(room.getName())

        forced_reduction = self.getCachedItemInt(Heating.heating_mode_item_name)

        # check for open windows (long and short)
        for transition in room.getTransitions():
            if transition.getContactItem() != None:
                open_duration_in_seconds = None
                closed_duration_in_seconds = None
                # *** check open state
                if self.getCachedItemState(transition.getContactItem()) == scope.OPEN:
                    # *** register open window if it is open long enough
                    if transition.getContactItem() not in Heating._open_window_contacts:
                        open_since = Registry.getItem(transition.getContactItem()).getLastStateChange()
                        open_duration_in_seconds = (open_since - self.now).total_seconds()
                        if open_duration_in_seconds > Heating.OPEN_WINDOW_START_DURATION * 60:
                            Heating._open_window_contacts[transition.getContactItem()] = open_since
                        else:
                            continue
                    else:
                        open_duration_in_seconds = (Heating._open_window_contacts[transition.getContactItem()] - self.now).total_seconds()
                # *** if the window was open
                elif transition.getContactItem() in Heating._open_window_contacts:
                    # *** check if it is closed long enough to unregister it
                    closed_since = Registry.getItem(transition.getContactItem()).getLastStateChange()
                    closed_duration_in_seconds = (closed_since - self.now).total_seconds()
                    open_duration_in_seconds = (Heating._open_window_contacts[transition.getContactItem()] - closed_since).total_seconds()
                    ending_treshold = open_duration_in_seconds * 2.0
                    # 1 hour
                    if ending_treshold > 60 * 60:
                        ending_treshold = 60 * 60
                    if closed_duration_in_seconds > ending_treshold:
                        del Heating._open_window_contacts[transition.getContactItem()]
                        continue
                else:
                    continue
                
                # *** window is open or is closed not long enough
                debug_info = u"OPEN {} min.".format(int(round(open_duration_in_seconds / 60.0)))
                if closed_duration_in_seconds != None:
                    debug_info = u"{} & CLOSED {} min.".format(debug_info, int(round(closed_duration_in_seconds / 60.0)))
                debug_info = u"{} ago".format(debug_info)
                hs.setDebugInfo( debug_info )

                hs.setHeatingDemandEnergy(None)
                hs.setHeatingDemandTime(None)
                if open_duration_in_seconds > Heating.LONG_OPEN_WINDOW_START_DURATION * 60:
                    hs.setOpenWindowState(2)
                    break
                else:
                    hs.setOpenWindowState(1)
        
        hs.setNightReduction(night_reduction)
        hs.setOutdoorReduction(outdoor_reduction)
        hs.setForcedReduction(forced_reduction)
        
        current_temperature = round(self.getCachedStableItemFloat(Heating.getTemperatureSensorItemName(room)),1)

        # set active target temperature to room state
        target_temperature = self.getCachedItemFloat(Heating.getTemperatureTargetItemName(room)) - night_reduction - outdoor_reduction - forced_reduction
        hs.setHeatingTargetTemperature(round(target_temperature, 1))
        
        charged = rs.getChargedBuffer()
        
        # check for upcoming charge level changes => see "charge level changes" for the final one
        if room.getName() in Heating._stable_temperature_references:
            _last_temp = Heating._stable_temperature_references[room.getName()]
            if current_temperature > _last_temp and charged > 0:
                charged = self.adjustChargeLevel(rs, current_temperature, _last_temp,charged)
                if charged < 0.0: charged = 0.0
                hs.setAdjustedChargedBuffer(charged)
            
        if hs.hasOpenWindow():
            hs.setInfo("WINDOW")
        else:
            missing_degrees = target_temperature - current_temperature
            
            #self.logger.info("{} {} {} {}".format(room.getName(),current_temperature,outdoor_reduction,missing_degrees))

            if missing_degrees < 0:
                hs.setInfo("WARM")
            else:                
                # 75% of 0.1°C
                max_buffer = rs.getBufferSlotCapacity() * 0.75

                if missing_degrees > 0:
                    hs.setInfo("COLD")
                    
                    possibleDegrees = charged / rs.getBufferCapacity()
                    # We have more energy then needed. Means we already fill the buffer
                    if possibleDegrees - missing_degrees > 0:
                        lazy_reduction = missing_degrees
                        missing_degrees = 0
                        charged = charged - ( lazy_reduction * rs.getBufferCapacity() )
                    # We need more energy
                    else:
                        lazy_reduction = possibleDegrees
                        missing_degrees = missing_degrees - lazy_reduction
                        charged = 0
                        
                        # Needed energy for the missing lazy energy + the upcoming charging of the buffer 
                        needed_energy = ( missing_degrees * rs.getBufferCapacity() ) + max_buffer
                        needed_time = self.calculateHeatingDemandTime(needed_energy,rs.getActivePossibleSaldo())
                        hs.setHeatingDemandEnergy(needed_energy)
                        hs.setHeatingDemandTime(needed_time)
                        
                    hs.setLazyReduction(round(lazy_reduction, 2))

                if missing_degrees == 0:
                    #self.logger.info(u"{} {} {}".format(room.getName(),missing_degrees,bufferHeatingEnabled))

                    #self.logger.info(u"{} {} {}".format(room.getName(),charged,max_buffer))
                    
                    # Stop buffer heating if buffer more than 75% charged
                    if charged > max_buffer:
                        hs.setInfo("LOADED")
                    # No heating needed if buffer is changed more than minBufferChargeLevel
                    elif not is_heating_active and charged > 0:
                        hs.setInfo("UNLOAD")
                    # Currently no buffer heating
                    else:
                        hs.setInfo("CHARGE")
                        #self.logger.info(u"3")
                        needed_energy = max_buffer - charged
                        needed_time = self.calculateHeatingDemandTime(needed_energy,rs.getActivePossibleSaldo())
                        hs.setHeatingDemandEnergy(needed_energy)
                        hs.setHeatingDemandTime(needed_time)

        hs.setChargedReserveBuffer(charged)
            
        return hs
                
    def adjustChargeLevel(self, rs, current_temp, last_temp, charge_level):
        heated_up_temp_diff = current_temp - last_temp
        charge_level = charge_level - ( rs.getBufferCapacity() * heated_up_temp_diff )
        return charge_level
        
    def calculateChargeLevel(self, room, rs):
        total_charge_level = self.getCachedItemFloat(Heating.getHeatingBufferItemName(room))
        debug_info = None
        
        current_temp = round(self.getCachedStableItemFloat(Heating.getTemperatureSensorItemName(room),20),1)
        if room.getName() in Heating._stable_temperature_references:
            last_temp = Heating._stable_temperature_references[room.getName()]
            name = room.getName().replace("room","")
            if current_temp < last_temp:
                debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C decreased".format(name,last_temp,current_temp)
            elif current_temp > last_temp:
                if total_charge_level > 0:
                    new_total_charge_level = self.adjustChargeLevel(rs,current_temp,last_temp,total_charge_level)
                    if new_total_charge_level < 0.0: new_total_charge_level = 0.0
                    debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C increased and Charged from {} to {} W adjusted".format(name,last_temp,current_temp, int(round(total_charge_level)), int(round(new_total_charge_level)) )
                    total_charge_level = new_total_charge_level
                else:
                    debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C increased".format(name,last_temp,current_temp)
        Heating._stable_temperature_references[room.getName()]=current_temp

        # detech last runtime and change calculated values to that timespan_in_seconds
        # all calculations are normally per minute
        timespan_in_seconds = 30.0 if Heating.last_runtime is None else (Heating.last_runtime - self.now).total_seconds()
        devider = 60.0 / ( timespan_in_seconds if timespan_in_seconds > 0 else 1 )
        #self.logger.info(u"{} {}".format(room.getName(),devider))

        total_charge_level = total_charge_level + ( rs.getActiveSaldo() / 60.0 / devider )
        if total_charge_level < 0.0: total_charge_level = 0.0
        
        return total_charge_level, debug_info
      
    def calculateHeatingDemandTime(self, needed_energy, active_possible_saldo):
        if active_possible_saldo <= 0:
            return Heating.INFINITE_HEATING_TIME
        else:
            needed_time = needed_energy / active_possible_saldo
            return needed_time

    def limitHeatingDemandTime(self, roomName, hating_demand_time, limit = 1.5 ):
        if hating_demand_time > limit:
            self.logger.info(u"        : WARNING heating time for '{}' was limited from {} min to {} min".format(roomName,int(round(hating_demand_time*60)),int(round(limit*60))))
            return limit
        else:
            return hating_demand_time

    @staticmethod
    def visualizeHeatingDemandTime(hating_demand_time):
        if hating_demand_time < 0:
            return u"<1"
        return u"~" if hating_demand_time == Heating.INFINITE_HEATING_TIME else int(round(hating_demand_time*60))
        
        
        
        
        
        
        
    def formatEnergy(self, energy, precision=1):
        return round(energy/60.0, precision)
                
    def logCoolingAndRadiations(self,prefix, cr, sun_radiation_lazy = None, sun_light_level = None):
        
        sdi = cr.getSunDebugInfo()
        
        lazy_radiation_msg = u" (∾ {})".format( round(sun_radiation_lazy / 60.0, 1) ) if sun_radiation_lazy != None else ""
        light_level_msg = u", {} lux".format( int(sun_light_level) ) if sun_light_level != None else ""
        debug_info = u"Az {}° • El {}{}° • Clouds {} ⊗ • Sun {}{} W/min{}{}".format(sdi["azimut"], sdi["elevation"], sdi["min_elevation"], cr.getCloudCover(), sdi["effective_radiation"], lazy_radiation_msg, light_level_msg, sdi["active"])

        self.logger.info(u"{}: {}".format(prefix, debug_info))
        
        self.logger.info(u"        : Wall {} ({}☀) W/min • Air {} W/min • Leak {} W/min • Window {} ({}☀) W/min".format(
            self.formatEnergy(cr.getWallEnergy()),
            self.formatEnergy(cr.getWallRadiation()),
            self.formatEnergy(cr.getVentilationEnergy()),
            self.formatEnergy(cr.getLeakEnergy()),
            self.formatEnergy(cr.getWindowEnergy()),
            self.formatEnergy(cr.getWindowRadiation())
        ))
        msg = u"{} W/min".format(self.formatEnergy(cr.getHeatingRadiation())) if cr.getHeatingRadiation() > 0 else u"{} W/min (FC)".format(self.formatEnergy(cr.getPossibleHeatingRadiation()))
        self.logger.info(u"        : ↑↓ {} W/min ({}°C) • HU {}".format(self.formatEnergy(cr.getPassiveSaldo()),round(cr.getReferenceTemperature(),1), msg ))
        self.logger.info(u"        : ---")
                  
    def logHeatingStates(self, cr, hhs):
        if cr.getHeatingVolume() > 0:
            self.logger.info(u"        : {} ({} m³) • Factor {}".format(cr.getHeatingDebugInfo(),round(cr.getHeatingVolume() / 1000.0,3),round(cr.getHeatingVolumeFactor(),2)))
            self.logger.info(u"        : ---")
        
        if len(hhs.getChargeLevelDebugInfos()) > 0:
            for charge_level_debug_info in hhs.getChargeLevelDebugInfos():
                self.logger.info(charge_level_debug_info)
            self.logger.info(u"        : ---")

        for room in Heating.rooms:
            self.logHeatingState(room, cr, hhs)
        
    def logHeatingState(self, room, cr, hhs):
        rs = cr.getRoomState(room.getName())
        rhs = hhs.getHeatingState(room.getName()) if room.getHeatingVolume() != None else None
                        
        name = room.getName().replace("room","")
        info_msg = u"{:11s} • {}°C".format(name,round(self.getCachedStableItemFloat(Heating.getTemperatureSensorItemName(room)),1))
        
        if rhs != None:
            info_msg = u"{} ({})".format(info_msg,rhs.getHeatingTargetTemperature())

            infoValue = rhs.getInfo()
            if rhs.getForcedInfo() != None:
                infoValue = u"{} ({})".format(infoValue, rhs.getForcedInfo())
            info_msg = u"{} {:6s}".format(info_msg,infoValue)
        else:
            info_msg = u"{}              ".format(info_msg)
            
        details = []
        #details.append(u"{:4.1f}i".format(self.formatEnergy(rs.getIndoorWallEnergy())))
        if cr.getSunSouthRadiation() > 0 or cr.getSunWestRadiation() > 0:
            details.append(u"{:3.1f}☀".format(self.formatEnergy(rs.getWallRadiation()+rs.getWindowRadiation())))
                           
        details_msg = u" ({})".format(u", ".join(details)) if len(details) > 0 else u""
        info_msg = u"{} • ↑↓ {:4.1f}{} W/min".format(info_msg, self.formatEnergy(rs.getPassiveSaldo()), details_msg)

        # **** DEBUG ****
        #info_msg = u"{} • DEBUG {} {}".format(info_msg, rs.getPossibleHeatingRadiation(), rs.getPossibleHeatingVolume())

        if rhs != None:
            # show heating details per room if total heating is active
            if cr.getHeatingRadiation() > 0:
                info_msg = u"{} • HU {:3.1f} W/min".format(info_msg, self.formatEnergy(rs.getHeatingRadiation()))
                
            adjustedBuffer = u""
            if rhs.getChargedReserveBuffer() != rs.getChargedBuffer() or rhs.getAdjustedChargedBuffer() != None:
                if rhs.getChargedReserveBuffer() != rs.getChargedBuffer():
                    adjustedBuffer = u"{}{}".format(adjustedBuffer, int(round(rs.getChargedBuffer())) )
                if rhs.getAdjustedChargedBuffer() != None:
                    adjustedBuffer = u"{} => {}".format(adjustedBuffer, int(round(rhs.getAdjustedChargedBuffer())) )
                adjustedBuffer = u" ({})".format(adjustedBuffer)
            
            percent = int(round(rhs.getChargedReserveBuffer() * 100 / rs.getBufferSlotCapacity() ))
            info_msg = u"{} • BF {}%, {}{} W".format(info_msg, percent, int(round(rhs.getChargedReserveBuffer())), adjustedBuffer)

            reduction_msg = []
            if rhs.getOutdoorReduction() > 0:
                reduction_msg.append(u"OR {}".format(rhs.getOutdoorReduction()))
            if rhs.getNightReduction() > 0:
                reduction_msg.append(u"NR {}".format(rhs.getNightReduction()))
            if rhs.getLazyReduction() > 0:
                reduction_msg.append(u"LR {}".format(rhs.getLazyReduction()))
            if rhs.getForcedReduction() > 0:
                reduction_msg.append(u"FR {}".format(rhs.getForcedReduction()))
            if len(reduction_msg) > 0:
                info_msg = u"{} • {}".format(info_msg, ", ".join(reduction_msg))
                
            debug_msg = u" • ({})".format(rhs.getDebugInfo()) if rhs.getDebugInfo() != None else u""
      
            if rhs.getHeatingDemandTime() > 0:
                info_msg = u"{} • HU {} W in {} min".format(
                    info_msg,
                    round(rhs.getHeatingDemandEnergy(),1) if rhs.getHeatingDemandEnergy() != None else u"~",
                    Heating.visualizeHeatingDemandTime( rhs.getHeatingDemandTime() )
                )
                self.logger.info(u"     ON : {}{}".format(info_msg, debug_msg))
            elif rhs.getHeatingDemandTime() == 0:
                self.logger.info(u"    OFF : {}{}".format(info_msg, debug_msg))
            else:
                self.logger.info(u"SKIPPED : {}{}".format(info_msg, debug_msg))
        else:
            self.logger.info(u"        : {}".format(info_msg))
                
    def calculate(self, is_heating_active, sun_radiation):
        # handle outdated ventilation values
        if Registry.getItem(self.ventilation_filter_runtime_item_name).getLastStateUpdate() < self.now - timedelta(minutes=120):
            self.cache[self.ventilation_level_item_name] = Java_DecimalType(3)
            self.cache[self.ventilation_outgoing_temperature_item_name] = Java_DecimalType(0.0)
            self.cache[self.ventilation_incomming_temperature_item_name] = Java_DecimalType(0.0)
        else:
            # init ventilation level and check if it is undefined (communication problem)
            self.getCachedItemState(self.ventilation_level_item_name)

        now_4 = self.now + timedelta(minutes=240)
        now_8 = self.now + timedelta(minutes=480)

        temperature_forecast = Registry.resolveItem(self.forecast_temperature_garden_item_name).getPersistence("jdbc")
        temperature = self.getCachedItemState(self.current_temperature_garden_item_name).floatValue()
        temperature_4 = temperature_forecast.persistedState(now_4)
        temperature_8 = temperature_forecast.persistedState(now_8)

        cloud_forecast = Registry.resolveItem(self.forecast_cloud_cover_item_name).getPersistence("jdbc")
        cloud_cover = self.getCachedItemState(self.current_cloud_cover_item_name)
        cloud_cover_4 = cloud_forecast.persistedState(now_4)
        cloud_cover_8 = cloud_forecast.persistedState(now_8)

        # handle outdated forecast values
        if temperature_4 is None or temperature_8 is None or cloud_cover_4 is None or cloud_cover_8 is None:
            temperature_4 = temperature_8 = temperature
            cloud_cover = cloud_cover_4 = cloud_cover_8 = Java_DecimalType(9)
        else:
            temperature_4 = temperature_4.getState().floatValue()
            temperature_8 = temperature_8.getState().floatValue()
            cloud_cover_4 = cloud_cover_4.getState().floatValue()
            cloud_cover_8 = cloud_cover_8.getState().floatValue()

        # *** 8 HOUR FORECAST ***
        cr8 = self.getCoolingAndRadiations(temperature, temperature_8, cloud_cover_8)
        # *** 4 HOUR FORECAST ***
        cr4 = self.getCoolingAndRadiations(temperature, temperature_4, cloud_cover_4)
        # *** CURRENT ***
        cr = self.getCoolingAndRadiations(temperature, temperature, cloud_cover, sun_radiation)

        # *** NIGHT MODE DETECTION ***
        night_mode_active = self.isNightMode(is_heating_active)
        night_reduction = self.DEFAULT_NIGHT_REDUCTION if night_mode_active else 0.0
        
        hhs = HouseHeatingState()
        heating_requested = False
        charge_level_debug_infos = []
        
        month = self.now.month
        is_summer_mode_priorized = ( month >= 5 and month <= 10 )

        for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
            
            # CLEAN CHARGE LEVEL
            rs = cr.getRoomState(room.getName())
            total_charge_level, charge_level_debug_info = self.calculateChargeLevel(room,rs)
            #total_charge_level, _ = self.calculateChargeLevel(room,rs)
            rs.setChargedBuffer(total_charge_level)

            rs4 = cr4.getRoomState(room.getName())
            rs4.setChargedBuffer(total_charge_level)

            rs8 = cr8.getRoomState(room.getName())
            rs8.setChargedBuffer(total_charge_level)
            
            if charge_level_debug_info != None:
                charge_level_debug_infos.append(charge_level_debug_info)

            # *** HEATING STATE ***

            last_heating_change = Registry.getItem(Heating.getHeatingDemandItemName(room)).getLastStateUpdate() # can be "getLastUpdate" datetime, because it is changed only from heating rule

            rhs = None
            # *** CLEAN OR RESTORE FORCED HEATING ***
            if room.getName() in Heating._forced_heatings:
                fh = Heating._forced_heatings[room.getName()]
                rhs = fh['rhs']

                if fh['energy'] != None:
                    # PRE heating should only be active during NightMode
                    # Check is needed
                    # - because maybe there is not enough demand to start heating. So we will never reach needed energy level
                    # - or operation mode can flip between "Heizen mit WWW" and "Reduziert". So we will never reach needed charge level
                    if not night_mode_active:
                        needed_time = -1
                    else:
                        needed_energy = fh['energy'] - rs.getChargedBuffer()
                        needed_time = self.calculateHeatingDemandTime(needed_energy,rs.getActivePossibleSaldo()) if needed_energy > 0 else -1
                else:
                    demand_started = fh['since']
                    # CF heating should not take longer than two time more then expected
                    # Check is needed
                    # - because the operation mode can flip between "Heizen mit WWW" and "Reduziert". So we will never reach needed runtime
                    if (demand_started - self.now).total_seconds() > fh['time'] * 60.0 * 60.0 * 2:
                        needed_time = -1
                    else:
                        needed_energy = None
                        currentTime = self.now
                        run_time = 0
                        while  currentTime > demand_started:
                            currentItemEntry = ToolboxHelper.getPersistedEntry("pGF_Utilityroom_Heating_Operating_Mode", currentTime)
                            # mode is "Heizen mit WW"
                            if currentItemEntry.getState().intValue() == 2:
                                run_time += ( currentItemEntry.getTimestamp() - currentTime ).total_seconds()
                            currentTime = currentItemEntry.getTimestamp().minusNanos(1)
                            
                        run_time = run_time / 60.0 / 60.0 # convert seconds to hours
                        needed_time = ( fh['time'] - run_time )

                if needed_time < 0:
                    del Heating._forced_heatings[room.getName()]
                    rhs = None
                else:
                    rhs.setHeatingDemandEnergy(needed_energy)
                    rhs.setHeatingDemandTime(needed_time)
                    hhs.setHeatingState(room.getName(),rhs)

            if rhs == None:
                # *** OUTDOOR REDUCTION ***
                outdoor_reduction = self.calculateOutdoorReduction(rs.getPassiveSaldo(), rs4.getPassiveSaldo(), rs8.getPassiveSaldo())

                # *** HEATING DEMAND CALCULATION ***
                rhs = self.getHeatingDemand(room, rs, outdoor_reduction, night_reduction, is_heating_active)
            
                #needed_time = self.getColdFloorHeatingTime(last_heating_change)
                #needed_energy = needed_time * rs.getActivePossibleSaldo()
                #self.logger.info(u"{} saldo: {}, energy: {}, time: {}".format(room.getName(),round(rs.getActivePossibleSaldo(),1),round(needed_energy,1),Heating.visualizeHeatingDemandTime(needed_time)))
                
                if rhs.getHeatingDemandTime() == 0 and not is_heating_active:
                    fh_info_type_r = {'not needed':[], 'wrong time': [], 'other': []}
                    
                    count = 0
                    if cr.getReferenceTemperature() > rhs.getHeatingTargetTemperature():
                        count += 1
                    if cr4.getReferenceTemperature() > rhs.getHeatingTargetTemperature():
                        count += 1
                    if cr8.getReferenceTemperature() > rhs.getHeatingTargetTemperature():
                        count += 1
                    if is_summer_mode_priorized:
                        count += 1

                    if count >= 2 and rs.getCurrentTemperature() > rhs.getHeatingTargetTemperature():
                    #if rs.getCurrentTemperature() > rhs.getHeatingTargetTemperature() + 2.0 and cr.getReferenceTemperature():
                        fh_info_type_r["other"].append(u"'PRE' & 'CF' summer mode")
                    else:
                        # *** CHECK FOR PRE HEATING IN THE MORNING ***
                        if night_mode_active and self.now.hour < 12:
                            day_rhs = self.getHeatingDemand(room, rs, outdoor_reduction, 0, False)
                            if day_rhs.getHeatingDemandTime() > 0:
                                if not self.isNightModeTime( int(round(self.limitHeatingDemandTime( room.getName(), day_rhs.getHeatingDemandTime() ) * 60, 0)) ):
                                    rhs = day_rhs
                                    rhs.setForcedInfo('PRE')
                                else:
                                    fh_info_type_r['other'].append(u"'PRE' too early for {} W in {} min".format(round(day_rhs.getHeatingDemandEnergy(), 1), Heating.visualizeHeatingDemandTime(day_rhs.getHeatingDemandTime())))
                            else:
                                fh_info_type_r["not needed"].append('PRE')
                        else:
                            fh_info_type_r["wrong time"].append('PRE')

                        # *** CHECK FOR COLD FLOOR HEATING ***
                        if self.now - timedelta(minutes=180) < last_heating_change:
                            fh_info_type_r["not needed"].append('CF')
                        elif self.possibleColdFloorHeating(night_mode_active,last_heating_change):
                            needed_time = self.getColdFloorHeatingTime(last_heating_change)
                            if rhs.getHeatingDemandTime() < needed_time:
                                if not self.isNightModeTime( int(round(self.limitHeatingDemandTime( room.getName(), needed_time ) * 60, 0)) ):
                                    rhs.setHeatingDemandEnergy(None)
                                    rhs.setHeatingDemandTime(needed_time)
                                    rhs.setForcedInfo('CF')
                                else:
                                    fh_info_type_r['other'].append(u"'CF' too early for {} min".format(Heating.visualizeHeatingDemandTime(needed_time)))
                            else:
                                fh_info_type_r["not needed"].append('CF')
                        else:
                            fh_info_type_r["wrong time"].append('CF')
                    
                    if rhs.getForcedInfo() == None:
                        fh_info_r = []
                        for info_type in fh_info_type_r:
                            if len(fh_info_type_r[info_type]) == 0:
                                continue
                            
                            if info_type == 'other':
                                fh_info_r.append( ", ".join(fh_info_type_r[info_type]) )
                            else:
                                fh_info_r.append( "{} {}".format(" & ".join(fh_info_type_r[info_type]),info_type) )
                        
                        rhs.setDebugInfo( ", ".join(fh_info_r) )

            if rhs.getHeatingDemandTime() > 0.0:
                if is_heating_active or rhs.getHeatingDemandTime() * 60 > Heating.MIN_HEATING_TIME:
                    heating_requested = True

            hhs.setHeatingState(room.getName(),rhs)

        # *** REGISTER FORCED HEATINGS IF HEATING IS POSSIBLE
        if heating_requested:
            for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
                rhs = hhs.getHeatingState(room.getName())
                if rhs.getForcedInfo() != None and room.getName() not in Heating._forced_heatings:
                    #Heating._forced_heatings[room.getName()] = [ rhs, rs.getChargedBuffer() + rhs.getHeatingDemandEnergy() ]
                    Heating._forced_heatings[room.getName()] = { 'rhs': rhs, 'energy': rhs.getHeatingDemandEnergy(), 'time': rhs.getHeatingDemandTime(), 'since': self.now }

        hhs.setHeatingRequested(heating_requested)

        hhs.setChargeLevelDebugInfos(charge_level_debug_infos)
        
        Heating.last_runtime = self.now

        return cr, cr4, cr8, hhs
