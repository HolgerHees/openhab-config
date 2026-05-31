from openhab import Registry, logger

from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper
from custom.flags import FlagHelper
from custom.heating.house import Window, ThermalBridgeType
from custom.heating.state import RoomState, HouseState, HeatingState #, RoomHeatingState, HouseHeatingState
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
    LAZY_NIGHT_TIME = 15 # 'Heizen mit WW' should be active at least for 15 min.
    LAZY_OFFSET = 60 # Offset time until any heating has an effect

    HEATING_MIN_PIPE_TEMPERATURE = 25 # 37
    HEATING_MAX_PIPE_TEMPERATURE = 45 # 60

    HEATING_MAX_OUTDOOR_TEMPERATURE = 20
    HEATING_MIN_OUTDOOR_TEMPERATURE = -20

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
    forecast_temperature_item_name = None

    current_cloud_cover_item_name = None
    current_temperature_garden_item_name = None

    ventilation_level_item_name = None
    ventilation_outgoing_temperature_item_name = None
    ventilation_incomming_temperature_item_name = None
    
    heating_state_item_name = None
    heating_temperature_pipe_out_item_name = None
    heating_temperature_pipe_in_item_name = None

    precence_status_item_name = None
    holiday_status_item_name = None
    heating_mode_item_name = None

    total_volume = 0
    total_heating_volume = None
    
    temperature_sensor_item_name_placeholder = None
    temperature_target_item_name_placeholder = None
    
    heating_hk_item_name_placeholder = None
    heating_circuit_item_name_placeholder = None
    heating_buffer_item_name_placeholder = None
    heating_demand_item_name_placeholder = None
    heating_target_temperature_item_name_placeholder = None

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

    @staticmethod
    def getCurrentTemperatureSensorItemName(room):
        return Heating.temperature_sensor_item_name_placeholder.format(room.getName()[1:])

    @staticmethod
    def getTargetTemperatureItemName(room):
        return Heating.temperature_target_item_name_placeholder.format(room.getName()[1:])

    def __init__(self,logger, time):
        self.logger = logger
        self.now = time
        self.cache = {}

    def getCachedStableItemAsDouble(self, item_name, stable_since=10):
        key = u"stable-{}-{}".format(item_name, stable_since)
        if key not in self.cache:
            self.cache[key] = ToolboxHelper.getStableState(item_name, stable_since, self.now)
        return self.cache[key].doubleValue()
      
    def getVentilationEnergy(self, temp_diff_offset):
        # *** Calculate power loss by ventilation ***
        _ventilationLevel = Registry.getItemState(self.ventilation_level_item_name)
        if _ventilationLevel != scope.UNDEF:
            _ventilation_temp_diff = Registry.getItemState(self.ventilation_outgoing_temperature_item_name).doubleValue() - Registry.getItemState(self.ventilation_incomming_temperature_item_name).doubleValue()

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

    def getCoolingEnergy(self, area, current_temperature, garden_temperature, type, bound):
        if type.getUValue() != None:
            reference_temperature = self.getCachedStableItemAsDouble(Heating.getCurrentTemperatureSensorItemName(Heating.getRoom(bound))) if bound != None else garden_temperature
            temperature_difference = current_temperature - reference_temperature
            cooling_per_kelvin =( type.getUValue() + type.getUOffset() ) * area * type.getFactor()
            cooling_total = cooling_per_kelvin * temperature_difference
            return cooling_total * -1 if cooling_total != 0 else 0.0
        else:
            return 0.0
        
    def calculateWallCoolingAndRadiations(self, current_temperature, garden_temperature, sun_south_radiation, sun_west_radiation, walls):
        outdoor_wall_cooling = indoor_wall_cooling = outdoor_wall_radiation = room_capacity = 0
        for wall in walls:
            cooling = self.getCoolingEnergy(wall.getArea(), current_temperature, garden_temperature, wall.getType(),wall.getBound())
            if wall.getBound() == None:
                outdoor_wall_cooling += cooling
            else:
                indoor_wall_cooling += cooling
            
            if wall.getBound() == None:
                if wall.getDirection() == 'south':
                    outdoor_wall_radiation = outdoor_wall_radiation + SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_south_radiation)
                elif wall.getDirection() == 'west':
                    outdoor_wall_radiation = outdoor_wall_radiation + SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_west_radiation)

            capacity = ( wall.getArea() * wall.getType().getCapacity() ) / 3.6 # converting kj into watt

            room_capacity = room_capacity + capacity

        return indoor_wall_cooling, outdoor_wall_cooling, outdoor_wall_radiation, room_capacity
        
    def calculateWindowCoolingAndRadiations(self, current_temperature, garden_temperature, sun_south_radiation, sun_west_radiation, transitions, is_forecast):
        window_energy = window_radiation = open_window_count = 0
        for transition in transitions:
            if not is_forecast and transition.getContactItem() != None and Registry.getItemState(transition.getContactItem()) == scope.OPEN and Registry.getItem(transition.getContactItem()).getLastStateChange() < self.now - timedelta(2):
                window_energy += self.getCoolingEnergy(transition.getArea(), current_temperature, garden_temperature, ThermalBridgeType( uValue=10.0, uOffset=0.1, factor=1.0 ), None)
                open_window_count = open_window_count + 1
            else:
                # TODO maybe increase uValue if rollershutter is closed
                window_energy += self.getCoolingEnergy(transition.getArea(), current_temperature, garden_temperature, transition.getType(), transition.getBound())

            if isinstance(transition,Window) and transition.getRadiationArea() != None:
                _shutterOpen = (is_forecast or transition.getShutterItem() == None or Registry.getItemState(transition.getShutterItem()).intValue() == 0)
                if _shutterOpen:
                    if transition.getDirection() == 'south':
                        window_radiation += SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_south_radiation)
                    elif transition.getDirection() == 'west':
                        window_radiation += SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_west_radiation)
        
        return window_energy, window_radiation, open_window_count
          
    def calculatePossibleHeatingEnergy(self, is_forecast, outdoor_temp, states_data):
        temperatures = []
        for room in filter( lambda room: room.getHeatingVolume() != None, Heating.rooms):
            if is_forecast or room.getHeatingVolume() == None or states_data[room.getName()]["heating_circuit_state"] == scope.ON:
                temperatures.append(states_data[room.getName()]["current_temperature"])
        
        if len(temperatures) == 0:
            # Fallback is avg of all target temperatures
            for room in filter( lambda room: room.getHeatingVolume() != None, Heating.rooms):
                temperatures.append(states_data[room.getName()]["target_temperature"])

        temperature_pipe_in = reduce( lambda x,y: x+y, temperatures ) / len(temperatures) + 1.5

        # 0.6 steilheit
        # niveau 12k
        # 20° => 37°                => 0 => 0°
        # -20^ => 60°               => 40 => 23°

        outdoor_temperatur_diff = Heating.HEATING_MAX_OUTDOOR_TEMPERATURE - Heating.HEATING_MIN_OUTDOOR_TEMPERATURE
        pipe_temperature_diff = Heating.HEATING_MAX_PIPE_TEMPERATURE - Heating.HEATING_MIN_PIPE_TEMPERATURE

        if outdoor_temp > Heating.HEATING_MAX_OUTDOOR_TEMPERATURE:
            temperature_pipe_out = Heating.HEATING_MIN_PIPE_TEMPERATURE
        elif outdoor_temp < Heating.HEATING_MIN_OUTDOOR_TEMPERATURE:
            temperature_pipe_out = Heating.HEATING_MAX_PIPE_TEMPERATURE
        else:
            temperature_pipe_out = ( ( ( (outdoor_temp - Heating.HEATING_MAX_OUTDOOR_TEMPERATURE)  * -1 ) * pipe_temperature_diff / outdoor_temperatur_diff ) + Heating.HEATING_MIN_PIPE_TEMPERATURE ) * 0.95


        if temperature_pipe_out > Heating.HEATING_MAX_PIPE_TEMPERATURE:
            temperature_pipe_out = Heating.HEATING_MAX_PIPE_TEMPERATURE
                
        circulation_diff = temperature_pipe_out - temperature_pipe_in
            
        pump_speed = 100.0
        
        #debug_info = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulation_diff,1),round(temperature_pipe_out,1),round(temperature_pipe_in,1),pump_speed)
        #self.logger.info(debug_info)

        return circulation_diff, pump_speed

    def calculateHeatingEnergy(self, is_forecast):
        if not is_forecast and Registry.getItemState(self.heating_state_item_name) == scope.ON:
            temperature_pipe_out = Registry.getItemState(self.heating_temperature_pipe_out_item_name).doubleValue()
            temperature_pipe_in = Registry.getItemState(self.heating_temperature_pipe_in_item_name).doubleValue()
            if temperature_pipe_out - temperature_pipe_in > 1.0:
                pump_speed = 100.0
                circulation_diff = temperature_pipe_out - temperature_pipe_in
                #Diff 9.6°C • VL 38.9°C • RL 29.3°C • 85% (0.42 m³)
                debug_info = u"Diff {}°C • VL {}°C • RL {}°C • {}%".format(round(circulation_diff,1),round(temperature_pipe_out,1),round(temperature_pipe_in,1),pump_speed)
                return circulation_diff, pump_speed, debug_info
        return 0, 0, ""

    def calculateHeatingRadiation(self, heating_volume_factor, room_heating_volume, circulation_diff, pump_speed):
        if room_heating_volume != None:
            pump_volume = ( room_heating_volume * heating_volume_factor * pump_speed ) / 100.0
            
            # pump_volume / 1000.0 => convert liter => m³
            heating_energy = self.HEATING_REFERENCE_ENERGY * (pump_volume / 1000.0) * circulation_diff
            
            return pump_volume, heating_energy
        else:
            return 0.0, 0.0
          
    def calculateHeatingVolumeFactor(self, is_forecast, states_data):
        #if not is_forecast:
        #    active_heating_volume = 0
        
        #    for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
        #        if states_data[room.getName()]["heating_circuit_state"] == scope.ON:
        #            active_heating_volume = active_heating_volume + room.getHeatingVolume()
                
        #    if active_heating_volume > 0:
        #        # if all circuits are active => then 100% of Heating.total_heating_volume are possible
        #        # if >0% of the circuits volume is active then 30.0% of self.total_heating_volume at 100%
        #        # if 50% of the circuits volume is active then 65.0% of self.total_heating_volume at 100%
        #        possible_heating_volume_in_percent = ( active_heating_volume * 70.0 / Heating.total_heating_volume ) + 30.0

        #        #self.logger.info(u"{} {} {}".format(possible_heating_volume_in_percent,active_heating_volume,Heating.total_heating_volume))

        #        return possible_heating_volume_in_percent / 100.0

        # TODO maybe reverse factor. if all are open, 100% is possible. if just a few are open, 50% more for each circuit is possible
        # first, validate, that the heating circuit pump doesn't eventually stabilize itself.
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
        
        _holidays_active = Registry.getItemState(self.holiday_status_item_name) == scope.ON
        
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
      
    def isNightMode(self, rs, is_night_mode_active):
        if self.now.hour > 19:
            if is_night_mode_active:
                diff = round(rs.getHeatingTargetTemperature() - rs.getCurrentTemperature(), 1)
                if diff <= 0: # early night mode only possible if the room is not too cold
                    offset = self.LAZY_OFFSET
                    if diff < 0:
                        max_additional_offset = self.LAZY_OFFSET * 2
                        if rs.getPassiveSaldo() > 0:
                            offset += max_additional_offset
                        else:
                            duration = ((diff * rs.getBufferCapacity()) / rs.getPassiveSaldo() ) * 60
                            offset += max_additional_offset if duration > max_additional_offset else duration
                else:
                    offset = 0
                return self.isNightModeTime( offset )
            return True
        
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
        
        _presence_state_away = Registry.getItemState(Heating.precence_status_item_name) == PresenceHelper.STATE_AWAY
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

    def getCoolingAndRadiations(self, time, ref_garden_temperature, garden_temperature, cloud_cover, sun_radiation=None):
        states_data = {}
        for room in Heating.rooms:
            # set room values
            current_temperature = self.getCachedStableItemAsDouble(Heating.getCurrentTemperatureSensorItemName(room))
            #if room.getName() == "lGF_Guesttoilet":
            if room.getHeatingVolume() is not None:
                target_temperature = Registry.getItemState(Heating.getTargetTemperatureItemName(room)).doubleValue()
                heating_target_temperature = Registry.getItemState(Heating.getHeatingTargetTemperatureItemName(room)).doubleValue()
                heating_circuit_state = Registry.getItemState(Heating.getHeatingCircuitItemName(room))
                heating_last_changed = Registry.getItem(Heating.getHeatingDemandItemName(room)).getLastStateUpdate()
            else:
                target_temperature = heating_target_temperature = current_temperature
                heating_circuit_state = scope.OFF
                heating_last_changed = None

            states_data[room.getName()] = {
                "current_temperature": current_temperature,
                "target_temperature": target_temperature,
                "heating_target_temperature": heating_target_temperature,
                "heating_circuit_state": heating_circuit_state,
                "heating_last_changed": heating_last_changed
            }

        is_forecast = time != self.now
        temp_diff_offset = ref_garden_temperature - garden_temperature

        possible_heating_circulation_diff, possible_heating_pump_speed = self.calculatePossibleHeatingEnergy(is_forecast, garden_temperature, states_data)
        heating_circulation_diff, heating_pump_speed, heating_debug_info = self.calculateHeatingEnergy(is_forecast)
        heating_volume_factor = self.calculateHeatingVolumeFactor(is_forecast, states_data)
        
        current_total_ventilation_energy = self.getVentilationEnergy(temp_diff_offset) / 3.6 # converting kj into watt
        sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info = SunRadiation.getSunPowerPerHour(time, cloud_cover, sun_radiation)
        sun_south_radiationMax, sun_west_radiationMax, sun_radiation_max, sun_max_debug_info = SunRadiation.getSunPowerPerHour(time, 0)

        states = {}
        for room in Heating.rooms:            
            _state_data = states_data[room.getName()]
                          
            # *** WALL COOLING AND RADIATION ***
            indoor_wall_energy, outdoor_wall_energy, outdoor_wall_radiation, room_capacity = self.calculateWallCoolingAndRadiations(_state_data["current_temperature"], garden_temperature, sun_south_radiation, sun_west_radiation, room.getWalls())

            # *** WINDOW COOLING AND RADIATION ***
            window_energy, window_radiation, open_window_count = self.calculateWindowCoolingAndRadiations(_state_data["current_temperature"], garden_temperature, sun_south_radiation, sun_west_radiation, room.getTransitions(), is_forecast)
            
            if room.getHeatingVolume() != None:
                # *** HEATING RADIATION ***
                if heating_pump_speed == 0 or _state_data["heating_circuit_state"] != scope.ON:
                    heating_volume, heating_radiation = 0.0, 0.0
                else:
                    heating_volume, heating_radiation = self.calculateHeatingRadiation(heating_volume_factor, room.getHeatingVolume(), heating_circulation_diff, heating_pump_speed)
                
                possible_heating_volume, possible_heating_radiation = self.calculateHeatingRadiation(1.0, room.getHeatingVolume(), possible_heating_circulation_diff, possible_heating_pump_speed)
            else:
                heating_volume, heating_radiation = 0.0, 0.0
                possible_heating_volume, possible_heating_radiation = 0.0, 0.0

            # *** VENTILATION COOLING ***
            ventilation_energy = room.getVolume() * current_total_ventilation_energy / Heating.total_volume
            leak_energy = self.getLeakingEnergy(room.getVolume(), _state_data["current_temperature"], garden_temperature) / 3.6 # converting kj into watt
            
            states[room.getName()] = RoomState(
                room.getName(),

                current_temperature = _state_data["current_temperature"],
                target_temperature = _state_data["target_temperature"],
                heating_target_temperature = _state_data["heating_target_temperature"],
                heating_circuit_state = _state_data["heating_circuit_state"],
                heating_last_changed = _state_data["heating_last_changed"],

                buffer_capacity = room_capacity,

                indoor_wall_energy = indoor_wall_energy,
                outdoor_wall_energy = outdoor_wall_energy,
                outdoor_wall_radiation = outdoor_wall_radiation,

                ventilation_energy = ventilation_energy,
                leak_energy = leak_energy,

                window_energy = window_energy,
                window_radiation = window_radiation,
                open_window_count = open_window_count,

                possible_heating_volume = possible_heating_volume,
                possible_heating_radiation = possible_heating_radiation,
                heating_volume = heating_volume,
                heating_radiation = heating_radiation
            )

        house = HouseState(
            room_states = states,

            reference_temperature = garden_temperature,

            heating_pump_speed = heating_pump_speed,
            heating_volume_factor = heating_volume_factor,
            heating_debug_info = heating_debug_info,

            cloud_cover = cloud_cover,
            sun_radiation = sun_radiation,
            sun_radiation_max = sun_radiation_max,
            sun_south_radiation = sun_south_radiation,
            sun_south_radiation_max = sun_south_radiationMax,
            sun_west_radiation = sun_west_radiation,
            sun_west_radiation_max = sun_west_radiationMax,
            sun_debug_info = sun_debug_info
        )
        #print(sun_south_radiation, sun_west_radiation, house.getIndoorWallEnergy(), house.getOutdoorWallEnergy(), house.getOutdoorWallRadiation())
        return house

    def getHeatingDemand(self, room, rs, outdoor_reduction, night_reduction):
        forced_reduction = Registry.getItemState(Heating.heating_mode_item_name).intValue()
        hs = HeatingState(night_reduction, outdoor_reduction, forced_reduction)

        # check for open windows (long and short)
        for transition in room.getTransitions():
            if transition.getContactItem() != None:
                open_duration_in_seconds = None
                closed_duration_in_seconds = None
                # *** check open state
                if Registry.getItemState(transition.getContactItem()) == scope.OPEN:
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

                hs.setDemandEnergy(None)
                hs.setDemandTime(None)
                if open_duration_in_seconds > Heating.LONG_OPEN_WINDOW_START_DURATION * 60:
                    hs.setOpenWindowState(2)
                    break
                else:
                    hs.setOpenWindowState(1)

        current_temperature = round(rs.getCurrentTemperature(),1)
        target_temperature = round(rs.getTargetTemperature() - night_reduction - outdoor_reduction - forced_reduction, 1)

        charged = rs.getHeatingChargedBuffer()
        
        # check for upcoming charge level changes => see "charge level changes" for the final one
        if room.getName() in Heating._stable_temperature_references:
            _last_temp = Heating._stable_temperature_references[room.getName()]
            if current_temperature != _last_temp and charged > 0:
                charged, _ = self.adjustChargeLevel(rs, current_temperature, _last_temp,charged)
                hs.setAdjustedChargedBuffer(charged)

        if hs.hasOpenWindow():
            hs.setInfo("WINDOW")
        else:
            missing_degrees = target_temperature - current_temperature
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
                        needed_time = self.calculateHeatingDemandTime(needed_energy, rs.getActiveSaldo() if rs.getHeatingRadiation() > 0 else rs.getActivePossibleSaldo() )

                        hs.setDemandEnergy(needed_energy)
                        hs.setDemandTime(needed_time)
                        
                    hs.setLazyReduction(round(lazy_reduction, 2))

                if missing_degrees == 0:
                    # Stop buffer heating if buffer more than 75% charged
                    if charged >= max_buffer:
                        hs.setInfo("LOADED")
                    # No heating needed if buffer is changed more than minBufferChargeLevel
                    elif charged > 0 and rs.getHeatingCircuitState() == scope.OFF:
                        hs.setInfo("UNLOAD")
                    # Currently no buffer heating
                    else:
                        temperatur_sensor_item = Registry.getItem(Heating.getCurrentTemperatureSensorItemName(room))
                        raw_current_temperature = temperatur_sensor_item.getState().doubleValue()
                        raw_previous_temperature = temperatur_sensor_item.getPersistence("jdbc").persistedState(temperatur_sensor_item.getLastStateChange()).getState().doubleValue()
                        cooldown_time = int( (rs.getBufferSlotCapacity() / abs(rs.getPassiveSaldo()) / 5) * 60 )
                        print("NAME: {}, CurrentTemp: {}, PrevTemp: {}, CooldownTime: {}, Saldo: {}, LastChanged: {}".format(room.getName(), raw_current_temperature, raw_previous_temperature, cooldown_time, rs.getPassiveSaldo(), temperatur_sensor_item.getLastStateChange()))

                        if raw_previous_temperature > raw_current_temperature and (rs.getPassiveSaldo() > 0 or temperatur_sensor_item.getLastStateChange() > self.now - timedelta(minutes=cooldown_time)):
                            hs.setInfo("COOLDOWN")
                        else:
                            needed_energy = max_buffer - charged
                            needed_time = self.calculateHeatingDemandTime(needed_energy, rs.getActiveSaldo() if rs.getHeatingRadiation() > 0 else rs.getActivePossibleSaldo())

                            hs.setInfo("CHARGE")
                            hs.setDemandEnergy(needed_energy)
                            hs.setDemandTime(needed_time)

        #temperatur_sensor_item = Registry.getItem(Heating.getCurrentTemperatureSensorItemName(room))
        #raw_previous_temperature = temperatur_sensor_item.getPersistence("jdbc").persistedState(temperatur_sensor_item.getLastStateChange()).getState().doubleValue()
        #cooldown_time = int( (rs.getBufferSlotCapacity() / abs(rs.getPassiveSaldo()) / 5) * 60 )
        #print("NAME: {}, CurrentTemp: {}, PrevTemp: {}, CooldownTime: {}, Saldo: {}, LastChanged: {}".format(room.getName(), raw_current_temperature, raw_previous_temperature, cooldown_time, rs.getPassiveSaldo(), temperatur_sensor_item.getLastStateChange()))

        hs.setChargedReserveBuffer(charged)

        return hs, target_temperature
                
    def adjustChargeLevel(self, rs, current_temp, last_temp, charge_level):
        heated_up_temp_diff = abs(current_temp - last_temp)
        charge_diff = ( rs.getBufferCapacity() * heated_up_temp_diff )
        if charge_diff > charge_level:
            charge_diff = charge_level
        charge_level = charge_level - charge_diff
        return charge_level, charge_diff
        
    def calculateChargeLevel(self, room, rs):
        charge_level = Registry.getItemState(Heating.getHeatingBufferItemName(room)).doubleValue()
        charge_diff = 0
        debug_info = None
        
        current_temp = round(self.getCachedStableItemAsDouble(Heating.getCurrentTemperatureSensorItemName(room), 20), 1)
        if room.getName() in Heating._stable_temperature_references:
            last_temp = Heating._stable_temperature_references[room.getName()]
            name = room.getName().replace("room","")
            #if current_temp < last_temp:
            #    debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C decreased".format(name,last_temp,current_temp)
            #elif current_temp > last_temp:
            if current_temp != last_temp:
                is_increased = current_temp > last_temp
                if charge_level > 0:
                    new_charge_level, charge_diff = self.adjustChargeLevel(rs, current_temp,last_temp, charge_level)
                    debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C {} and Charged from {} to {} W adjusted".format(name,last_temp,current_temp, "increased" if is_increased else "decreased", int(round(charge_level)), int(round(new_charge_level)) )
                    charge_level = new_charge_level
                else:
                    debug_info = u"Cleanup : {:10s} • Reference from {} to {} °C {}".format(name,last_temp,current_temp, "increased" if is_increased else "decreased")
        Heating._stable_temperature_references[room.getName()] = current_temp

        # detech last runtime and change calculated values to that timespan_in_seconds
        # all calculations are normally per minute
        timespan_in_seconds = 30.0 if Heating.last_runtime is None else (self.now - Heating.last_runtime).total_seconds()

        charge_level = charge_level + ( rs.getActiveSaldo() / 60 / 60 * timespan_in_seconds )
        if charge_level < 0.0: charge_level = 0.0
        
        return charge_level, charge_diff, debug_info
      
    def calculateHeatingDemandTime(self, needed_energy, active_possible_saldo):
        if active_possible_saldo <= 0:
            return Heating.INFINITE_HEATING_TIME
        return needed_energy / active_possible_saldo

    def limitHeatingDemandTime(self, roomName, hating_demand_time, limit ):
        if hating_demand_time > limit:
            self.logger.info(u"        : WARNING heating time for '{}' was limited from {} min to {} min".format(roomName,int(round(hating_demand_time*60)),int(round(limit*60))))
            return limit
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
        debug_info = u"🌍 Az {}° • El {}{}° ⛅ Clouds {:.1f} 🌞 Sun {}{} W/min{}{}".format(sdi["azimut"], sdi["elevation"], sdi["min_elevation"], cr.getCloudCover(), sdi["effective_radiation"], lazy_radiation_msg, light_level_msg, sdi["active"])

        self.logger.info(u"{}: {}".format(prefix, debug_info))
        
        self.logger.info(u"        : 💨 Wall {} ({}☀) W/min • Air {} W/min • Leak {} W/min • Window {} ({}☀) W/min".format(
            self.formatEnergy(cr.getWallEnergy()),
            self.formatEnergy(cr.getWallRadiation()),
            self.formatEnergy(cr.getVentilationEnergy()),
            self.formatEnergy(cr.getLeakEnergy()),
            self.formatEnergy(cr.getWindowEnergy()),
            self.formatEnergy(cr.getWindowRadiation())
        ))
        msg = u"{} W/min".format(self.formatEnergy(cr.getHeatingRadiation())) if cr.getHeatingRadiation() > 0 else u"{} W/min (FC)".format(self.formatEnergy(cr.getPossibleHeatingRadiation()))
        self.logger.info(u"        : 🏠 ↑↓ {} W/min ({}°C) 🔥 HU {}".format(self.formatEnergy(cr.getPassiveSaldo()),round(cr.getReferenceTemperature(),1), msg ))
        self.logger.info(u"        : ---")
                  
    def logHeatingStates(self, cr):
        if cr.getHeatingVolume() > 0:
            self.logger.info(u"        : {} ({} m³) • Factor {}".format(cr.getHeatingDebugInfo(),round(cr.getHeatingVolume() / 1000.0,3),round(cr.getHeatingVolumeFactor(),2)))
            self.logger.info(u"        : ---")
        
        if len(cr.getChargeLevelDebugInfos()) > 0:
            for charge_level_debug_info in cr.getChargeLevelDebugInfos():
                self.logger.info(charge_level_debug_info)
            self.logger.info(u"        : ---")

        for room in Heating.rooms:
            self.logHeatingState(room, cr)
        
    def logHeatingState(self, room, cr):
        rs = cr.getRoomState(room.getName())
        hs = rs.getHeatingState()
                        
        name = room.getName().replace("room","")
        info_msg = u"{:11s} • {}°C".format(name,round(rs.getCurrentTemperature(),1))
        
        if hs is not None:
            info_msg = u"{} ({})".format(info_msg, rs.getHeatingTargetTemperature())

            infoValue = hs.getInfo()
            if hs.getForcedInfo() != None:
                infoValue = u"{} ({})".format(infoValue, hs.getForcedInfo())
            info_msg = u"{} {:6s}".format(info_msg, infoValue)
        else:
            info_msg = u"{}              ".format(info_msg)

        details = []
        #details.append(u"{:4.1f}i".format(self.formatEnergy(rs.getIndoorWallEnergy())))
        if cr.getSunSouthRadiation() > 0 or cr.getSunWestRadiation() > 0:
            details.append(u"{:3.1f}☀".format(self.formatEnergy(rs.getOutdoorWallRadiation()+rs.getWindowRadiation())))
                           
        details_msg = u" ({})".format(u", ".join(details)) if len(details) > 0 else u""
        info_msg = u"{} • ↑↓ {:4.1f}{} W/min".format(info_msg, self.formatEnergy(rs.getPassiveSaldo()), details_msg)

        # **** DEBUG ****
        #info_msg = u"{} • DEBUG {} {}".format(info_msg, rs.getPossibleHeatingRadiation(), rs.getPossibleHeatingVolume())

        if hs is not None:
            # show heating details per room if total heating is active
            if cr.getHeatingRadiation() > 0:
                info_msg = u"{} • HU {:3.1f} W/min".format(info_msg, self.formatEnergy(rs.getHeatingRadiation()))
                
            adjustedBuffer = u""
            if hs.getChargedReserveBuffer() != rs.getHeatingChargedBuffer() or hs.getAdjustedChargedBuffer() != None:
                if hs.getChargedReserveBuffer() != rs.getHeatingChargedBuffer():
                    adjustedBuffer = u"{}{}".format(adjustedBuffer, int(round(rs.getHeatingChargedBuffer())) )
                if hs.getAdjustedChargedBuffer() != None:
                    adjustedBuffer = u"{} => {}".format(adjustedBuffer, int(round(hs.getAdjustedChargedBuffer())) )
                adjustedBuffer = u" ({})".format(adjustedBuffer)
            
            percent = int(round(hs.getChargedReserveBuffer() * 100 / rs.getBufferSlotCapacity() ))
            info_msg = u"{} • BF {}%, {}{} W".format(info_msg, percent, int(round(hs.getChargedReserveBuffer())), adjustedBuffer)

            reduction_msg = []
            if hs.getOutdoorReduction() > 0:
                reduction_msg.append(u"OR {}".format(hs.getOutdoorReduction()))
            if hs.getNightReduction() > 0:
                reduction_msg.append(u"NR {}".format(hs.getNightReduction()))
            if hs.getLazyReduction() > 0:
                reduction_msg.append(u"LR {}".format(hs.getLazyReduction()))
            if hs.getForcedReduction() > 0:
                reduction_msg.append(u"FR {}".format(hs.getForcedReduction()))
            if len(reduction_msg) > 0:
                info_msg = u"{} • {}".format(info_msg, ", ".join(reduction_msg))
                
            debug_msg = u" • ({})".format(hs.getDebugInfo()) if hs.getDebugInfo() != None else u""
      
            if hs.getDemandTime() > 0:
                info_msg = u"{} • HU {} W in {} min".format(
                    info_msg,
                    round(hs.getDemandEnergy(),1) if hs.getDemandEnergy() != None else u"~",
                    Heating.visualizeHeatingDemandTime( hs.getDemandTime() )
                )
                self.logger.info(u"  {} : {}{}".format("   ON" if rs.getHeatingCircuitState() == scope.ON else " (ON)", info_msg, debug_msg))
            elif hs.getDemandTime() == 0:
                self.logger.info(u"  {} : {}{}".format("  OFF" if rs.getHeatingCircuitState() == scope.OFF else "(OFF)", info_msg, debug_msg))
            else:
                self.logger.info(u"SKIPPED : {}{}".format(info_msg, debug_msg))
        else:
            self.logger.info(u"        : {}".format(info_msg))
                
    def calculate(self, is_night_mode_active, is_heating_demand, sun_radiation):
        now_4 = self.now + timedelta(minutes=240)
        now_8 = self.now + timedelta(minutes=480)

        temperature_forecast = Registry.resolveItem(self.forecast_temperature_item_name).getPersistence("jdbc")
        temperature = self.getCachedStableItemAsDouble(self.current_temperature_garden_item_name)
        temperature_4 = temperature_forecast.persistedState(now_4)
        temperature_8 = temperature_forecast.persistedState(now_8)

        cloud_forecast = Registry.resolveItem(self.forecast_cloud_cover_item_name).getPersistence("jdbc")
        cloud_cover = cloud_forecast.persistedState(self.now)
        cloud_cover_4 = cloud_forecast.persistedState(now_4)
        cloud_cover_8 = cloud_forecast.persistedState(now_8)

        # handle outdated forecast values
        if temperature_4 is None or temperature_8 is None or cloud_cover_4 is None or cloud_cover_8 is None:
            temperature_4 = temperature_8 = temperature
            cloud_cover = cloud_cover_4 = cloud_cover_8 = Java_DecimalType(9)
        else:
            temperature_4 = temperature_4.getState().floatValue()
            temperature_8 = temperature_8.getState().floatValue()
            cloud_cover = cloud_cover.getState().floatValue()
            cloud_cover_4 = cloud_cover_4.getState().floatValue()
            cloud_cover_8 = cloud_cover_8.getState().floatValue()

        # *** 8 HOUR FORECAST ***
        cr8 = self.getCoolingAndRadiations(now_8, temperature, temperature_8, cloud_cover_8)
        # *** 4 HOUR FORECAST ***
        cr4 = self.getCoolingAndRadiations(now_4, temperature, temperature_4, cloud_cover_4)
        # *** CURRENT ***
        cr = self.getCoolingAndRadiations(self.now, temperature, temperature, cloud_cover, sun_radiation)

        heating_requested = False
        charge_level_debug_infos = []
        
        month = self.now.month
        is_summer_mode_priorized = ( month >= 5 and month <= 10 )

        for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
            rs = cr.getRoomState(room.getName())

            # NIGHT MODE DETECTION
            night_mode_active = self.isNightMode(rs, is_night_mode_active)
            night_reduction = self.DEFAULT_NIGHT_REDUCTION if night_mode_active else 0.0

            rs.setNightMode(night_mode_active)

            # CLEAN CHARGE LEVEL
            total_charge_level, charge_level_diff, charge_level_debug_info = self.calculateChargeLevel(room, rs)
            rs.setHeatingChargedBuffer(total_charge_level)
            if charge_level_debug_info != None:
                charge_level_debug_infos.append(charge_level_debug_info)

            # *** CLEAN OR RESTORE FORCED HEATING ***
            if room.getName() in Heating._forced_heatings:
                fh = Heating._forced_heatings[room.getName()]
                if fh['heating_state'].getDemandEnergy() != None:
                    # PRE heating should only be active during NightMode
                    # Check is needed
                    # - because maybe there is not enough demand to start heating. So we will never reach needed energy level
                    # - or operation mode can flip between "Heizen mit WWW" and "Reduziert". So we will never reach needed charge level
                    if not night_mode_active:
                        needed_time = -1
                    else:
                        if charge_level_diff > 0:
                            fh['forced_demand_energy'] -= charge_level_diff
                        needed_energy = fh['forced_demand_energy'] - rs.getHeatingChargedBuffer()
                        needed_time = self.calculateHeatingDemandTime(needed_energy,rs.getActivePossibleSaldo()) if needed_energy > 0 else -1
                else:
                    run_time = (fh['forced_started'] - self.now).total_seconds() / 60.0 / 60.0 # convert seconds to hours
                    needed_time = ( fh['forced_demand_time'] - run_time )

                if needed_time < 0:
                    self.logger.info("DEBUG: cleanup forced heating {}, getDemandEnergy: {}, getDemandTime: {}, needed_time: {}".format(room.getName(), fh['heating_state'].getDemandEnergy(), fh['heating_state'].getDemandTime(), needed_time))
                    del Heating._forced_heatings[room.getName()]
                else:
                    self.logger.info("DEBUG: continue forced heating {}, getDemandEnergy: {}, getDemandTime: {}, needed_time: {}".format(room.getName(), fh['heating_state'].getDemandEnergy(), fh['heating_state'].getDemandTime(), needed_time))
                    fh['heating_state'].setDemandEnergy(needed_energy)
                    fh['heating_state'].setDemandTime(needed_time)
                    rs.setHeatingState(fh['heating_state'], fh['target_temperature'])

            # *** CALCULATE HEATING DEMAND ***
            if room.getName() not in Heating._forced_heatings:
                # *** OUTDOOR REDUCTION ***
                outdoor_reduction = self.calculateOutdoorReduction(rs.getPassiveSaldo(), cr4.getRoomState(room.getName()).getPassiveSaldo(), cr8.getRoomState(room.getName()).getPassiveSaldo())

                # *** HEATING DEMAND CALCULATION ***
                hs, _target_temperature = self.getHeatingDemand(room, rs, outdoor_reduction, night_reduction)
                rs.setHeatingState(hs, _target_temperature)

                if hs.getDemandTime() == 0 and not is_heating_demand:
                    last_heating_change = rs.getHeatingLastChanged()

                    fh_info_type_r = {'not needed':[], 'wrong time': [], 'other': []}
                    
                    count = 0
                    if cr.getReferenceTemperature() > rs.getHeatingTargetTemperature():
                        count += 1
                    if cr4.getReferenceTemperature() > rs.getHeatingTargetTemperature():
                        count += 1
                    if cr8.getReferenceTemperature() > rs.getHeatingTargetTemperature():
                        count += 1
                    if is_summer_mode_priorized:
                        count += 1

                    #if rs.getCurrentTemperature() > rs.getHeatingTargetTemperature() + 2.0 and cr.getReferenceTemperature():
                    if count >= 2 and rs.getCurrentTemperature() > rs.getHeatingTargetTemperature():
                        fh_info_type_r["other"].append(u"'PRE' & 'CF' summer mode")
                    else:
                        # *** CHECK FOR PRE HEATING IN THE MORNING ***
                        if night_mode_active and self.now.hour < 12:
                            _hs, _target_temperature = self.getHeatingDemand(room, rs, outdoor_reduction, 0)
                            if _hs.getDemandTime() > 0:
                                if not self.isNightModeTime( int(round(self.limitHeatingDemandTime( room.getName(), _hs.getDemandTime(), 1.5 ) * 60, 0)) ):
                                    hs = _hs
                                    hs.setForcedInfo('PRE')
                                    rs.setHeatingState(hs, _target_temperature)
                                else:
                                    fh_info_type_r['other'].append(u"'PRE' too early for {} W in {} min".format(round(_hs.getDemandEnergy(), 1), Heating.visualizeHeatingDemandTime(_hs.getDemandTime())))
                            else:
                                fh_info_type_r["not needed"].append('PRE')
                        else:
                            fh_info_type_r["wrong time"].append('PRE')

                        # *** CHECK FOR COLD FLOOR HEATING ***
                        if self.now - timedelta(minutes=180) < last_heating_change:
                            fh_info_type_r["not needed"].append('CF')
                        elif self.possibleColdFloorHeating(night_mode_active,last_heating_change):
                            needed_time = self.getColdFloorHeatingTime(last_heating_change)
                            if hs.getDemandTime() < needed_time:
                                if not self.isNightModeTime( int(round(self.limitHeatingDemandTime( room.getName(), needed_time, 1.5 ) * 60, 0)) ):
                                    hs.setDemandEnergy(None)
                                    hs.setDemandTime(needed_time)
                                    hs.setForcedInfo('CF')
                                else:
                                    fh_info_type_r['other'].append(u"'CF' too early for {} min".format(Heating.visualizeHeatingDemandTime(needed_time)))
                            else:
                                fh_info_type_r["not needed"].append('CF')
                        else:
                            fh_info_type_r["wrong time"].append('CF')
                    
                    if hs.getForcedInfo() is not None:
                        if room.getName() not in Heating._forced_heatings:
                            self.logger.info("DEBUG: activate forced heating {}".format(room.getName()))
                            Heating._forced_heatings[room.getName()] = { 'heating_state': hs, 'target_temperature': rs.getHeatingTargetTemperature(), 'forced_started': self.now, 'forced_demand_energy': hs.getDemandEnergy(), 'forced_demand_time': hs.getDemandTime()}
                    else:
                        fh_info_r = []
                        for info_type in fh_info_type_r:
                            if len(fh_info_type_r[info_type]) == 0:
                                continue
                            
                            if info_type == 'other':
                                fh_info_r.append( ", ".join(fh_info_type_r[info_type]) )
                            else:
                                fh_info_r.append( "{} {}".format(" & ".join(fh_info_type_r[info_type]),info_type) )
                        hs.setDebugInfo( ", ".join(fh_info_r) )

        # *** REGISTER FORCED HEATINGS IF HEATING IS POSSIBLE
        #if heating_requested:
        #    for room in filter( lambda room: room.getHeatingVolume() != None,Heating.rooms):
        #        rs = cr.getRoomState(room.getName())
        #cr.setHeatingRequested(heating_requested)

        cr.setChargeLevelDebugInfos(charge_level_debug_infos)
        
        Heating.last_runtime = self.now

        return cr, cr4, cr8
