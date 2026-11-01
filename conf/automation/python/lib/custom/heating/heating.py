from openhab import Registry

from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper
from custom.heating.house import ThermalBridgeType
from custom.heating.state import RoomState, HouseState, HeatingState #, RoomHeatingState, HouseHeatingState
from custom.suncalculation import SunRadiation
from custom.weather import WeatherHelper

from datetime import datetime, timedelta
import math

import scope


class Heating():
    NIGHT_HOURS = {  # weekdays: (night ends at endet um, night starts at)
        0: (5, 22), 1: (5, 22), 2: (5, 22), 3: (5, 22),
        4: (5, 23), 5: (7, 23), 6: (7, 22),
    }

    GROUND_TEMPERATURES_PER_MONTH = {1: 6, 2: 5, 3: 5.5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 13, 11: 11, 12: 9} # Month / AVG °C

    INFINITE_HEATING_TIME = 999.0 # const value for an infinite heating time
    
    DEFAULT_NIGHT_REDUCTION = 2.0
    LAZY_OFFSET = 60 # Offset time until any heating has an effect

    HEATING_CURVE_START_TEMPERATURE = 25
    HEATING_CURVE_SLOPE = 0.3

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

    forecast_cloud_cover_item_name = "pOutdoor_WeatherService_Cloud_Cover"
    forecast_temperature_item_name = "pOutdoor_WeatherService_Temperature"

    current_temperature_garden_item_name = WeatherHelper.getTemperatureItemName()

    ventilation_volume_item_name = "pGF_Utilityroom_Ventilation_Clime_Outgoing_Airflow"
    ventilation_outgoing_temperature_item_name = "pGF_Utilityroom_Ventilation_Extract_Temperature" #"pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"
    ventilation_incoming_temperature_item_name = "pGF_Utilityroom_Ventilation_Supply_Temperature" #"pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"
    
    heating_state_item_name = "pGF_Utilityroom_Heatpump_HK2_State"
    heating_temperature_pipe_out_item_name = "pGF_Utilityroom_Heatpump_HK2_Temperature_Pipe_Out"
    heating_temperature_pipe_in_item_name = "pGF_Utilityroom_Heatpump_HK2_Temperature_Pipe_In"

    presence_status_item_name = "pOther_Presence_State"
    heating_reduction_item_name = "pOther_Manual_State_Heating"
    
    temperature_sensor_item_name_placeholder = "p{}_Air_Sensor_Temperature_Value"
    temperature_target_item_name_placeholder = "p{}_Temperature_Desired"
    
    heating_hk_item_name_placeholder = "p{}_Heating_HK"
    heating_circuit_item_name_placeholder = "p{}_Heating_Circuit"
    heating_buffer_item_name_placeholder = "p{}_Heating_Charged"
    heating_demand_item_name_placeholder = "p{}_Heating_Demand"
    heating_target_temperature_item_name_placeholder = "p{}_Heating_Temperature_Target"

    def __init__(self, rooms):
        self.rooms = rooms

        self.rooms_by_name = {}
        for room in rooms:
            self.rooms_by_name[room.getName()] = room

        self.heated_rooms = list(filter( lambda room: room.getHeatingVolume() is not None, self.rooms))
    
        self.total_volume = sum(room.getVolume() for room in self.rooms)
        self.total_heating_volume = sum(room.getHeatingVolume() for room in self.rooms if room.getHeatingVolume() is not None)
        self.total_ventilation_volume = sum(room.getVolume() for room in self.rooms if room.hasVentilation())

        self.forecast_temperature_4 = self.forecast_temperature_8 = self.forecast_cloud_cover_0 = self.forecast_cloud_cover_4 = self.forecast_cloud_cover_8 = None
        self.refreshForecastInterval()

        self.last_runtime = None

        self.debug_logged = False

        self.logger = None
        self.now = None
        self.cache = None

        self.room_open_window_states_map = {}
        self.room_states = {}
        self.total_active_heating_volume = 0

        self._forced_heatings = {}
        self._stable_temperature_references = {}
        # tmp status variables
        self._open_window_contacts= {}


        #for room in self.heated_rooms:
        #    wallLeak = floorLeak = capacity = 0
        #    for wall in room.getWalls():
        #        capacity += wall.getCapacityInWattHours()

        #        if wall.getType() is None or wall.getBound() is not None:
        #            continue

        #        if wall.getDirection() == "floor":
        #            floorLeak += ( wall.getType().getUValue() + wall.getType().getUOffset() ) * wall.getArea()
        #        else:
        #            wallLeak += ( wall.getType().getUValue() + wall.getType().getUOffset() ) * wall.getArea()

        #    for transition in room.getTransitions():
        #        if transition.getType() is None or transition.getBound() is not None:
        #            continue
        #        wallLeak += ( transition.getType().getUValue() + transition.getType().getUOffset() ) * transition.getArea()

        #    print("Name: {}, Capacity: {}, Floor Leak: {}, Wall Leak: {}".format(room.getName(), round(capacity, 0), round(floorLeak, 2), round(wallLeak, 2)))

    def refreshForecastInterval(self):
        now = datetime.now().astimezone()

        now_4 = now + timedelta(minutes=240)
        now_8 = now + timedelta(minutes=480)

        temperature_forecast = Registry.getItem(self.forecast_temperature_item_name).getPersistence("jdbc")
        forecast_temperature_4 = temperature_forecast.persistedState(now_4)
        self.forecast_temperature_4 = forecast_temperature_4.getState().doubleValue() if forecast_temperature_4 is not None else None
        forecast_temperature_8 = temperature_forecast.persistedState(now_8)
        self.forecast_temperature_8 = forecast_temperature_8.getState().doubleValue() if forecast_temperature_8 is not None else None

        cloud_forecast_item = Registry.getItem(self.forecast_cloud_cover_item_name)
        cloud_forecast = cloud_forecast_item.getPersistence("jdbc")
        forecast_cloud_cover_0 = cloud_forecast_item
        forecast_cloud_cover_4 = cloud_forecast.persistedState(now_4)
        forecast_cloud_cover_8 = cloud_forecast.persistedState(now_8)

                # handle outdated forecast values
        if forecast_cloud_cover_0 is None or forecast_cloud_cover_4 is None or forecast_cloud_cover_8 is None:
            self.forecast_cloud_cover_0 = self.forecast_cloud_cover_4 = self.forecast_cloud_cover_8 = 9.0
        else:
            self.forecast_cloud_cover_0 = forecast_cloud_cover_0.getState().floatValue()
            self.forecast_cloud_cover_4 = forecast_cloud_cover_4.getState().floatValue()
            self.forecast_cloud_cover_8 = forecast_cloud_cover_8.getState().floatValue()

    def refreshHeatingInterval(self, logger, time, current_temperature_garden_item_name):
        self.logger = logger
        self.now = time
        self.now_4 = self.now + timedelta(minutes=240)
        self.now_8 = self.now + timedelta(minutes=480)

        self.cold_floor_timeout = self.now - timedelta(minutes=180)
        self.open_window_start_time = self.now - timedelta(minutes=self.OPEN_WINDOW_START_DURATION)

        self.current_temperature_garden_item_name = current_temperature_garden_item_name

        self.cache = {}

        self.room_open_window_states_map, self.open_transitions_map = self._calculateOpenWindowStates()
        self.room_states, self.total_active_heating_volume = self._calculateRoomStates()

        self.forced_heating_reduction = Registry.getItemState(self.heating_reduction_item_name).intValue()

        ventilation_volume = Registry.getItemState(self.ventilation_volume_item_name)
        if ventilation_volume != scope.UNDEF:
            self.ventilation_volume = ventilation_volume.intValue()
            self.ventilation_temp_diff = Registry.getItemState(self.ventilation_outgoing_temperature_item_name).doubleValue() - Registry.getItemState(self.ventilation_incoming_temperature_item_name).doubleValue()
        else:
            self.ventilation_temp_diff = self.ventilation_volume = 0

    def _calculateOpenWindowStates(self):
        room_open_window_states_map = {}
        open_transitions_map = {}

        for room in self.rooms:
            room_open_window_states_map[room.getName()] = []

            # check for open windows (long and short)
            for transition in room.getTransitions():
                if transition.getContactItem() is None:
                    continue

                contact_item_name = transition.getContactItem()
                open_duration_in_seconds = None
                closed_duration_in_seconds = None

                # *** check open state
                if Registry.getItemState(contact_item_name) == scope.OPEN:
                    # *** register open window if it is open long enough
                    if contact_item_name not in self._open_window_contacts:
                        open_since = Registry.getItem(contact_item_name).getLastStateChange()
                        if open_since < self.open_window_start_time:
                            open_duration_in_seconds = (self.now - open_since).total_seconds()
                            self._open_window_contacts[contact_item_name] = open_since
                        else:
                            continue
                    else:
                        open_duration_in_seconds = (self.now - self._open_window_contacts[contact_item_name]).total_seconds()
                    open_transitions_map[transition] = True
                # *** if the window was open
                elif contact_item_name in self._open_window_contacts:
                    # *** check if it is closed long enough to unregister it
                    closed_since = Registry.getItem(contact_item_name).getLastStateChange()
                    closed_duration_in_seconds = (self.now - closed_since).total_seconds()
                    open_duration_in_seconds = (closed_since - self._open_window_contacts[contact_item_name]).total_seconds()
                    ending_threshold = open_duration_in_seconds * 2.0
                    # 1 hour
                    if ending_threshold > 60 * 60:
                        ending_threshold = 60 * 60
                    if closed_duration_in_seconds > ending_threshold:
                        del self._open_window_contacts[contact_item_name]
                        continue
                else:
                    continue

                room_open_window_states_map[room.getName()].append([open_duration_in_seconds, closed_duration_in_seconds])
        return room_open_window_states_map, open_transitions_map

    def _calculateRoomStates(self):
        total_active_heating_volume = 0
        room_states = {}

        for room in self.rooms:
            # set room values
            current_temperature = self.getCachedStableItemAsDouble(self._getCurrentTemperatureSensorItemName(room))
            #if room.getName() == "lGF_Guesttoilet":
            if room.getHeatingVolume() is not None:
                target_temperature = Registry.getItemState(self._getTargetTemperatureItemName(room)).doubleValue()
                heating_target_temperature = Registry.getItemState(self.getHeatingTargetTemperatureItemName(room)).doubleValue()
                heating_circuit_state = Registry.getItemState(self.getHeatingCircuitItemName(room))
                heating_last_changed = Registry.getItem(self.getHeatingDemandItemName(room)).getLastStateUpdate()
            else:
                target_temperature = heating_target_temperature = current_temperature
                heating_circuit_state = scope.OFF
                heating_last_changed = None

            room_states[room.getName()] = {
                "current_temperature": current_temperature,
                "target_temperature": target_temperature,
                "heating_target_temperature": heating_target_temperature,
                "heating_circuit_state": heating_circuit_state,
                "heating_last_changed": heating_last_changed
            }

            if heating_circuit_state == scope.ON:
                total_active_heating_volume += room.getHeatingVolume()
        return room_states, total_active_heating_volume

    def getRooms(self):
        return self.rooms

    def getHeatedRooms(self):
        return self.heated_rooms

    def getTotalHeatingVolume(self):
        return self.total_heating_volume

    def getHeatingBufferItemName(self, room):
        return self._preparePlaceholderItem(self.heating_buffer_item_name_placeholder, room)
      
    def getHeatingCircuitItemName(self, room):
        return self._preparePlaceholderItem(self.heating_circuit_item_name_placeholder, room)
      
    def getHeatingHKItemName(self, room):
        return self._preparePlaceholderItem(self.heating_hk_item_name_placeholder, room)

    def getHeatingTargetTemperatureItemName(self, room):
        return self._preparePlaceholderItem(self.heating_target_temperature_item_name_placeholder, room)
      
    def getHeatingDemandItemName(self, room):
        return self._preparePlaceholderItem(self.heating_demand_item_name_placeholder, room)

    def _getCurrentTemperatureSensorItemName(self, room):
        return self._preparePlaceholderItem(self.temperature_sensor_item_name_placeholder, room)

    def _getTargetTemperatureItemName(self, room):
        return self._preparePlaceholderItem(self.temperature_target_item_name_placeholder, room)

    def _preparePlaceholderItem(self, placeholder, room):
        return placeholder.format(room.getName()[1:])

    def getRoomState(self, room):
        return self.room_states[room.getName()]

    def getTotalActiveHeatingVolume(self):
        return self.total_active_heating_volume

    def getCachedStableItemAsDouble(self, item_name, stable_since=120):
        key = f"stable-{item_name}-{stable_since}"
        if key not in self.cache:
            self.cache[key] = round( ToolboxHelper.getStableState(item_name, stable_since, self.now).doubleValue(), 1)
        return self.cache[key]

    def getVentilationEnergy(self, temp_diff_offset):
        # *** Calculate power loss by ventilation ***
        if self.ventilation_volume > 0:
            _ventilation_temp_diff = self.ventilation_temp_diff

            # apply 25% of outdoor temperature changes (now until 4 or 8 hours) as an offset on top of '_ventilation_temp_diff'
            if temp_diff_offset != 0:
                _ventilation_temp_diff = max(_ventilation_temp_diff + temp_diff_offset / 4, 0)

            _ventilation_u_value = self.DENSITY_AIR * self.C_AIR  / 3.6 # converting kj into watt
            _ventilation_energy_in_watt = self.ventilation_volume * _ventilation_u_value * _ventilation_temp_diff

            return _ventilation_energy_in_watt * -1 if _ventilation_energy_in_watt != 0 else 0.0
        else:
            return 0.0
    
    def getLeakingEnergy(self, volume, current_temperature, outdoor_temperature):
        _leaking_temperature_diff = current_temperature - outdoor_temperature
        _leaking_volume = ( volume * self.LEAKING_N50 * self.LEAKING_E ) / ( 1 + ( self.LEAKING_F / self.LEAKING_E ) * ( ( ( 0.1 * 0.4 ) / self.LEAKING_N50 ) * ( ( 0.1 * 0.4 ) / self.LEAKING_N50 ) ) )
        _leaking_u_value = self.DENSITY_AIR * self.C_AIR / 3.6 # converting kj into watt
        _leaking_energy_in_watt = _leaking_volume * _leaking_u_value * _leaking_temperature_diff
        return _leaking_energy_in_watt * -1 if _leaking_energy_in_watt != 0 else 0.0

    def getCoolingEnergy(self, area, current_temperature, outdoor_temperature, thermal_type, bound):
        if thermal_type is not None and thermal_type.getUValue() is not None:
            # outdoor temperature is only relevant for walls "bounded" to outside (is None)
            reference_temperature = outdoor_temperature if bound is None else self.room_states[bound]["current_temperature"]
            temperature_difference = current_temperature - reference_temperature
            cooling_per_kelvin =( thermal_type.getUValue() + thermal_type.getUOffset() ) * area
            cooling_total = cooling_per_kelvin * temperature_difference
            return cooling_total * -1 if cooling_total != 0 else 0.0
        else:
            return 0.0
        
    def calculateWallCoolingAndRadiations(self, current_temperature, garden_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room):
        outdoor_wall_cooling = indoor_wall_cooling = outdoor_wall_radiation = room_capacity = 0
        for wall in room.getWalls():
            # is used only by ground floor calculation, because getCoolingEnergy checks for bound is None (=> to outside) too
            outdoor_temperature_ref = self.GROUND_TEMPERATURES_PER_MONTH[self.now.month] if wall.getDirection() == 'floor' else garden_temperature
            cooling = self.getCoolingEnergy(wall.getArea(), current_temperature, outdoor_temperature_ref, wall.getType(), wall.getBound())

            if wall.getBound() is None:
                outdoor_wall_cooling += cooling
                if wall.getDirection() == 'east':
                    outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_east_radiation)
                elif wall.getDirection() == 'south':
                    outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_south_radiation)
                elif wall.getDirection() == 'west':
                    outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_west_radiation)
            else:
                indoor_wall_cooling += cooling

            room_capacity += wall.getCapacityInWattHours()

        # air volume capacity
        room_capacity+= room.getVolume() * self.DENSITY_AIR * self.C_AIR / 3.6 # converting kj into watt

        return indoor_wall_cooling, outdoor_wall_cooling, outdoor_wall_radiation, room_capacity
        
    def calculateWindowCoolingAndRadiations(self, current_temperature, garden_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room, is_forecast):
        window_energy = window_radiation = open_window_count = 0
        for transition in room.getTransitions():
            if not is_forecast and transition in self.open_transitions_map:
                window_energy += self.getCoolingEnergy(transition.getArea(), current_temperature, garden_temperature, ThermalBridgeType( uValue=10.0, uOffset=0.1 ), None)
                open_window_count = open_window_count + 1
            else:
                # TODO maybe increase uValue if rollershutter is closed
                window_energy += self.getCoolingEnergy(transition.getArea(), current_temperature, garden_temperature, transition.getType(), transition.getBound())

            if transition.isWindow() and transition.getRadiationArea() is not None:
                _shutterOpen = (is_forecast or transition.getShutterItem() is None or Registry.getItemState(transition.getShutterItem()).intValue() == 0)
                if _shutterOpen:
                    if transition.getDirection() == 'east':
                        window_radiation += SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_east_radiation)
                    elif transition.getDirection() == 'south':
                        window_radiation += SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_south_radiation)
                    elif transition.getDirection() == 'west':
                        window_radiation += SunRadiation.getWindowSunPowerPerHour(transition.getRadiationArea(), sun_west_radiation)

        return window_energy, window_radiation, open_window_count
          
    def calculatePossibleHeatingEnergy(self, outdoor_temp):
        temperature_pipe_in = self.HEATING_CURVE_START_TEMPERATURE #sum(temperatures) / float(len(temperatures)) + 1.5

        if outdoor_temp > self.HEATING_CURVE_START_TEMPERATURE:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE
        else:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE + ((outdoor_temp - self.HEATING_CURVE_START_TEMPERATURE) * -1 * self.HEATING_CURVE_SLOPE)
                
        pump_speed = 100.0
        circulation_diff = temperature_pipe_out - temperature_pipe_in

        return circulation_diff, pump_speed

    def calculateHeatingEnergy(self, is_forecast):
        if is_forecast or Registry.getItemState(self.heating_state_item_name) == scope.OFF:
            return 0, 0, ""

        temperature_pipe_out = Registry.getItemState(self.heating_temperature_pipe_out_item_name).doubleValue()
        temperature_pipe_in = Registry.getItemState(self.heating_temperature_pipe_in_item_name).doubleValue()

        pump_speed = 100.0
        circulation_diff = temperature_pipe_out - temperature_pipe_in
        #Diff 9.6°C • VL 38.9°C • RL 29.3°C • 85% (0.42 m³)
        debug_info = f"Diff {circulation_diff:0.1f}°C • VL {temperature_pipe_out:0.1f}°C • RL {temperature_pipe_in:0.1f}°C • {pump_speed}%"
        return circulation_diff, pump_speed, debug_info

    def calculateHeatingVolumeFactor(self, active_heating_volume):
        # Data are measured
        # actives volumen => factor real volumen
        # 0.75 => x2
        # 11.75 => x1
        # self.total_heating_volume => 12.05
        ratio = (((active_heating_volume / 60) - 0.75) * 1) / ((self.total_heating_volume / 60) - 0.75)
        return max(min(2 - ratio,2),1)

    def calculateHeatingRadiation(self, heating_volume_factor, room_heating_volume, circulation_diff, pump_speed):
        if room_heating_volume is not None:
            pump_volume = ( room_heating_volume * heating_volume_factor * pump_speed ) / 100.0
            
            # pump_volume / 1000.0 => convert liter => m³
            heating_energy = self.HEATING_REFERENCE_ENERGY * (pump_volume / 1000.0) * circulation_diff
            
            return pump_volume, heating_energy
        else:
            return 0.0, 0.0
          
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
        # Closed cooling forecast should count 80%
        _outdoor_reduction_fc4 = self.getOutdoorDependingReduction(cooling_energy_fc4) * 0.8
        # Cooling forecast in 8 hours should count 60%
        _outdoor_reduction_fc8 = self.getOutdoorDependingReduction(cooling_energy_fc8) * 0.6
        
        _outdoor_reduction = _outdoor_reduction + _outdoor_reduction_fc4 + _outdoor_reduction_fc8
        
        return round( _outdoor_reduction, 2 )
      
    def isNightModeTime(self, offset=None):
        ref = self.now + timedelta(minutes=offset) if offset is not None else self.now
        ends, starts = self.NIGHT_HOURS[ref.weekday()]
        return ref.hour < ends or ref.hour >= starts

    def isNightMode(self, rs, is_night_mode):
        if self.now.hour > 19:
            if not is_night_mode:
                diff = round(rs.getHeatingTargetTemperature() - rs.getCurrentTemperature(), 1)
                if diff <= 0: # early night mode only possible if the room is not too cold
                    offset = self.LAZY_OFFSET
                    if diff < 0:
                        max_additional_offset = self.LAZY_OFFSET * 2
                        if rs.getPassiveSaldo() >= 0:
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
        
        _presence_state_away = Registry.getItemState(self.presence_status_item_name) == PresenceHelper.STATE_AWAY
        _evening_start_hours = (17 if day <= 4 and _presence_state_away else 16)
        is_evening = (hour == _evening_start_hours)
        if is_evening:
            _had_evening_heating = _had_today_heating and last_heating_change.hour >= _evening_start_hours
            return not _had_evening_heating
        
        return False
      
    def getColdFloorHeatingTime(self, last_update):
        # when was the last heating job
        last_update_before_in_minutes = int((self.now - last_update).total_seconds() / 60)
       
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
        is_forecast = time != self.now
        temp_diff_offset = ref_garden_temperature - garden_temperature

        possible_heating_circulation_diff, possible_heating_pump_speed = self.calculatePossibleHeatingEnergy(garden_temperature)
        heating_circulation_diff, active_heating_pump_speed, active_heating_debug_info = self.calculateHeatingEnergy(is_forecast)

        current_total_ventilation_energy = self.getVentilationEnergy(temp_diff_offset)
        sun_east_radiation, sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info = SunRadiation.getSunPowerPerHour(time, cloud_cover, sun_radiation)
        sun_east_radiationMax, sun_south_radiationMax, sun_west_radiationMax, sun_radiation_max, sun_max_debug_info = SunRadiation.getSunPowerPerHour(time, 0)

        active_heating_volume_factor = self.calculateHeatingVolumeFactor(self.getTotalActiveHeatingVolume())

        states = {}
        for room in self.rooms:
            _state_data = self.room_states[room.getName()]
                          
            # *** WALL COOLING AND RADIATION ***
            indoor_wall_energy, outdoor_wall_energy, outdoor_wall_radiation, room_capacity = self.calculateWallCoolingAndRadiations(_state_data["current_temperature"], garden_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room)

            # *** WINDOW COOLING AND RADIATION ***
            window_energy, window_radiation, open_window_count = self.calculateWindowCoolingAndRadiations(_state_data["current_temperature"], garden_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room, is_forecast)
            
            if room.getHeatingVolume() is not None:
                # *** HEATING RADIATION ***
                if active_heating_pump_speed == 0 or _state_data["heating_circuit_state"] != scope.ON:
                    active_heating_volume, active_heating_radiation = 0.0, 0.0
                else:
                    active_heating_volume, active_heating_radiation = self.calculateHeatingRadiation(active_heating_volume_factor, room.getHeatingVolume(), heating_circulation_diff, active_heating_pump_speed)

                possible_heating_volume, possible_heating_radiation = self.calculateHeatingRadiation(active_heating_volume_factor, room.getHeatingVolume(), possible_heating_circulation_diff, possible_heating_pump_speed)
            else:
                active_heating_volume = active_heating_radiation = possible_heating_volume = possible_heating_radiation = 0.0

            # *** VENTILATION COOLING ***
            ventilation_energy = room.getVolume() * current_total_ventilation_energy / self.total_ventilation_volume if room.hasVentilation() else 0
            leak_energy = self.getLeakingEnergy(room.getVolume(), _state_data["current_temperature"], garden_temperature)

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

                active_heating_volume = active_heating_volume,
                active_heating_radiation = active_heating_radiation,

                # just temporary, will be calculated again at the end of "calculate("
                possible_heating_volume = possible_heating_volume,
                possible_heating_radiation = possible_heating_radiation
            )

            #print(room.getName(), ventilation_energy)
            #if room.getName() in ["lGF_Livingroom","lGF_Workroom"]:
            #    print(room.getName(), indoor_wall_energy, outdoor_wall_energy, ventilation_energy, leak_energy, window_energy)
            #    print(states[room.getName()].getPassiveSaldo())

        house = HouseState(
            room_states = states,

            reference_temperature = garden_temperature,

            active_heating_pump_speed = active_heating_pump_speed,
            active_heating_volume_factor = active_heating_volume_factor,
            active_heating_debug_info = active_heating_debug_info,

            possible_heating_pump_speed = possible_heating_pump_speed,
            possible_heating_circulation_diff = possible_heating_circulation_diff,

            cloud_cover = cloud_cover,
            sun_radiation = sun_radiation,
            sun_radiation_max = sun_radiation_max,
            sun_east_radiation = sun_east_radiation,
            sun_east_radiation_max = sun_east_radiationMax,
            sun_south_radiation = sun_south_radiation,
            sun_south_radiation_max = sun_south_radiationMax,
            sun_west_radiation = sun_west_radiation,
            sun_west_radiation_max = sun_west_radiationMax,
            sun_debug_info = sun_debug_info
        )
        #print(sun_south_radiation, sun_west_radiation, house.getIndoorWallEnergy(), house.getOutdoorWallEnergy(), house.getOutdoorWallRadiation())
        return house

    def getHeatingDemand(self, room, rs, outdoor_reduction, night_reduction):
        hs = HeatingState(night_reduction, outdoor_reduction, self.forced_heating_reduction)

        # check for open windows (long and short)
        for open_duration_in_seconds, closed_duration_in_seconds in self.room_open_window_states_map[room.getName()]:
            # *** window is open or is closed not long enough
            debug_info = f"OPEN {int(round(open_duration_in_seconds / 60.0))} min."
            if closed_duration_in_seconds is not None:
                debug_info = f"{debug_info} & CLOSED {int(round(closed_duration_in_seconds / 60.0))} min."
            hs.setDebugInfo(f"{debug_info} ago")

            hs.setDemandEnergy(None)
            hs.setDemandTime(None)
            if open_duration_in_seconds > self.LONG_OPEN_WINDOW_START_DURATION * 60:
                hs.setOpenWindowState(2)
                break
            else:
                hs.setOpenWindowState(1)

        current_temperature = round(rs.getCurrentTemperature(),1)
        target_temperature = round(rs.getTargetTemperature() - night_reduction - outdoor_reduction - self.forced_heating_reduction, 1)

        charged = rs.getHeatingChargedBuffer()
        
        # check for upcoming charge level changes => see "charge level changes" for the final one
        if room.getName() in self._stable_temperature_references:
            _last_temp = self._stable_temperature_references[room.getName()]
            if current_temperature != _last_temp and charged > 0:
                charged, _ = self.adjustChargeLevel(rs, current_temperature, _last_temp, charged)
                hs.setAdjustedChargedBuffer(charged)

        if hs.hasOpenWindow():
            hs.setInfo("WINDOW")
        else:
            missing_degrees = target_temperature - current_temperature
            if missing_degrees < 0:
                hs.setInfo("WARM")
            else:                
                # A buffer slot is based on 0.1°C
                # Max buffer is 80% of this 0.1°C Slot.
                max_buffer = rs.getBufferSlotCapacity() * 0.8

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
                        needed_time = self.calculateHeatingDemandTime(needed_energy, rs.getActiveSaldo() if rs.getActiveHeatingRadiation() > 0 else rs.getActivePossibleSaldo() )

                        hs.setDemandEnergy(needed_energy)
                        hs.setDemandTime(needed_time)
                        
                    hs.setLazyReduction(round(lazy_reduction, 2))

                #cooldown_time = int( (rs.getBufferSlotCapacity() / abs(rs.getPassiveSaldo()) / 5) * 60 )
                #print(room.getName(), rs.getBufferCapacity(), cooldown_time, rs.getPassiveSaldo())
                #print(rs.getBufferCapacity() / rs.getPassiveSaldo())
                #2026-10-30 07:56:30.082 [INFO ] [tion.pythonscripting.heating_control] - lFF_Bathroom 1070.8438940972221 14 -88.37715965807806
                #2026-10-30 07:56:30.082 [INFO ] [tion.pythonscripting.heating_control] - -12.1167493755197

                if missing_degrees == 0:
                    # Stop buffer heating if buffer more than 75% charged
                    if charged >= max_buffer:
                        hs.setInfo("LOADED")
                    # No heating needed if buffer is changed more than minBufferChargeLevel
                    elif charged > 0 and rs.getHeatingCircuitState() == scope.OFF:
                        hs.setInfo("UNLOAD")
                    # Currently no buffer heating
                    else:
                        temperatur_sensor_item = Registry.getItem(self._getCurrentTemperatureSensorItemName(room))
                        raw_current_temperature = round(temperatur_sensor_item.getState().doubleValue(), 1)
                        raw_previous_temperature = round(temperatur_sensor_item.getLastState().doubleValue(), 1)
                        if rs.getPassiveSaldo() >= 0:
                            cooldown_time = -1
                        else:
                            cooldown_time = int( (rs.getBufferSlotCapacity() / rs.getPassiveSaldo() / 5) * -60 )

                        # Delay heating if
                        # 1. Heating is not ON
                        # 2. AND raw current temp is >= target
                        # 3. AND prev temp > current temp (cool down)
                        # 4. AND there is positive passive saldo OR cool down time not reached
                        if rs.getHeatingCircuitState() == scope.OFF and raw_current_temperature >= target_temperature and raw_previous_temperature > raw_current_temperature and (cooldown_time == -1 or temperatur_sensor_item.getLastStateChange() > self.now - timedelta(minutes=cooldown_time)):
                            hs.setInfo("COOLDOWN")
                        # Set heating demand if
                        # 1. Circuite is already ON (just continue heating)
                        # 2. OR If current raw temp is <= target
                        elif rs.getHeatingCircuitState() == scope.ON or raw_current_temperature <= target_temperature:
                            needed_energy = max_buffer - charged
                            needed_time = self.calculateHeatingDemandTime(needed_energy, rs.getActiveSaldo() if rs.getActiveHeatingRadiation() > 0 else rs.getActivePossibleSaldo())

                            hs.setInfo("CHARGE")
                            hs.setDemandEnergy(needed_energy)
                            hs.setDemandTime(needed_time)
                        #else:
                        #    hs.setInfo("WARMING")

                        self.logDebug(f"Debug   : {hs.getInfo()} => {room.getName()}, CurrentTemp: {raw_current_temperature:0.1f} °C, PrevTemp: {raw_previous_temperature:0.1f} °C, CooldownTime: {cooldown_time} min, Saldo: {rs.getPassiveSaldo():0.2f} W/min, LastChanged: {datetime.strftime(temperatur_sensor_item.getLastStateChange(), "%H:%M")}")

        hs.setChargedReserveBuffer(charged)

        return hs, target_temperature
                
    def adjustChargeLevel(self, rs, current_temp, last_temp, charge_level):
        # adjust buffer only on heatup.
        # on cooldown, keep the buffer, because needed buffer is getting bigger
        if current_temp > last_temp:
            heated_up_temp_diff = current_temp - last_temp
            charge_diff = ( rs.getBufferCapacity() * heated_up_temp_diff )
            if charge_diff > charge_level:
                charge_diff = charge_level
            charge_level = charge_level - charge_diff
        else:
            charge_diff = 0
        return charge_level, charge_diff

        
    def calculateChargeLevel(self, room, rs):
        charge_level = Registry.getItemState(self.getHeatingBufferItemName(room)).doubleValue()
        charge_diff = 0
        debug_info = None
        
        current_temp = self.getCachedStableItemAsDouble(self._getCurrentTemperatureSensorItemName(room), 240)
        if room.getName() in self._stable_temperature_references:
            last_temp = self._stable_temperature_references[room.getName()]
            name = room.getName().replace("room","")
            if current_temp != last_temp:
                is_increased = current_temp > last_temp
                if charge_level > 0:
                    new_charge_level, charge_diff = self.adjustChargeLevel(rs, current_temp, last_temp, charge_level)
                    debug_info = f"Cleanup : {name:<10} • Reference from {last_temp} to {current_temp} °C {"increased" if is_increased else "decreased"} and Charged from {int(round(charge_level))} to {int(round(new_charge_level))} W adjusted"
                    charge_level = new_charge_level
                else:
                    debug_info = f"Cleanup : {name:<10} • Reference from {last_temp} to {current_temp} °C {"increased" if is_increased else "decreased"}"
        self._stable_temperature_references[room.getName()] = current_temp

        # detect last runtime and change calculated values to that timespan_in_seconds
        # all calculations are normally per minute
        timespan_in_seconds = 30.0 if self.last_runtime is None else (self.now - self.last_runtime).total_seconds()

        charge_level = charge_level + ( rs.getActiveSaldo() / 60 / 60 * timespan_in_seconds )
        if charge_level < 0.0: charge_level = 0.0
        
        return charge_level, charge_diff, debug_info
      
    def calculateHeatingDemandTime(self, needed_energy, active_possible_saldo):
        if active_possible_saldo <= 0:
            return Heating.INFINITE_HEATING_TIME
        return needed_energy / active_possible_saldo

    def limitHeatingDemandTime(self, roomName, heating_demand_time, limit ):
        if heating_demand_time > limit:
            self.logDebug(f"        : WARNING heating time for '{roomName}' was limited from {int(round(heating_demand_time*60))} min to {int(round(limit*60))} min")
            return limit
        return heating_demand_time

    def logDebug(self, msg):
        self.logger.info(msg)
        self.debug_logged = True

    def calculate(self, is_night_mode, is_heating_demand, sun_radiation):
        temperature = self.getCachedStableItemAsDouble(self.current_temperature_garden_item_name)

        # handle outdated forecast values
        if self.forecast_temperature_4 is None or self.forecast_temperature_8 is None:
            temperature_4 = temperature_8 = temperature
        else:
            temperature_4 = self.forecast_temperature_4
            temperature_8 = self.forecast_temperature_8

        # *** 8 HOUR FORECAST ***
        cr8 = self.getCoolingAndRadiations(self.now_8, temperature, temperature_8, self.forecast_cloud_cover_8)
        # *** 4 HOUR FORECAST ***
        cr4 = self.getCoolingAndRadiations(self.now_4, temperature, temperature_4, self.forecast_cloud_cover_4)
        # *** CURRENT ***
        cr = self.getCoolingAndRadiations(self.now, temperature, temperature, self.forecast_cloud_cover_0, sun_radiation)

        charge_level_debug_infos = []
        
        month = self.now.month
        is_summer_mode_priorized = ( month >= 5 and month <= 9 )

        active_heating_volume = 0
        for room in self.heated_rooms:
            rs = cr.getRoomState(room.getName())

            # NIGHT MODE DETECTION
            night_mode_active = self.isNightMode(rs, is_night_mode)
            night_reduction = self.DEFAULT_NIGHT_REDUCTION if night_mode_active else 0.0

            rs.setNightMode(night_mode_active)

            # CLEAN CHARGE LEVEL
            total_charge_level, charge_level_diff, charge_level_debug_info = self.calculateChargeLevel(room, rs)
            rs.setHeatingChargedBuffer(total_charge_level)
            if charge_level_debug_info is not None:
                charge_level_debug_infos.append(charge_level_debug_info)

            # *** CLEAN OR RESTORE FORCED HEATING ***
            if room.getName() in self._forced_heatings:
                fh = self._forced_heatings[room.getName()]
                if fh['heating_state'].getDemandEnergy() is not None:
                    # PRE heating should only be active during NightMode
                    # Check is needed
                    # - because maybe there is not enough demand to start heating. So we will never reach needed energy level
                    # - or operation mode can flip between "Heizen mit WWW" and "Reduziert". So we will never reach needed charge level
                    if not night_mode_active:
                        needed_energy = None
                        needed_time = -1
                    else:
                        if charge_level_diff > 0:
                            fh['forced_demand_energy'] -= charge_level_diff
                        needed_energy = fh['forced_demand_energy'] - rs.getHeatingChargedBuffer()
                        needed_time = self.calculateHeatingDemandTime(needed_energy,rs.getActivePossibleSaldo()) if needed_energy > 0 else -1
                else:
                    run_time = (self.now - fh['forced_started']).total_seconds() / 60.0 / 60.0 # convert seconds to hours
                    needed_energy = None
                    needed_time = ( fh['forced_demand_time'] - run_time )

                if needed_time < 0:
                    self.logDebug(f"DEBUG: cleanup forced heating {room.getName()}, getDemandEnergy: {fh['heating_state'].getDemandEnergy()}, getDemandTime: {fh['heating_state'].getDemandTime()}, needed_time: {needed_time}")
                    del self._forced_heatings[room.getName()]
                else:
                    self.logDebug(f"DEBUG: continue forced heating {room.getName()}, getDemandEnergy: {fh['heating_state'].getDemandEnergy()}, getDemandTime: {fh['heating_state'].getDemandTime()}, needed_time: {needed_time}")
                    fh['heating_state'].setDemandEnergy(needed_energy)
                    fh['heating_state'].setDemandTime(needed_time)
                    rs.setHeatingState(fh['heating_state'], fh['target_temperature'])

            # *** CALCULATE HEATING DEMAND ***
            if room.getName() not in self._forced_heatings:
                # *** OUTDOOR REDUCTION ***
                outdoor_reduction = self.calculateOutdoorReduction(rs.getPassiveSaldo(), cr4.getRoomState(room.getName()).getPassiveSaldo(), cr8.getRoomState(room.getName()).getPassiveSaldo())

                # *** HEATING DEMAND CALCULATION ***
                hs, _target_temperature = self.getHeatingDemand(room, rs, outdoor_reduction, night_reduction)
                rs.setHeatingState(hs, _target_temperature)

                if hs.getDemandTime() is not None and hs.getDemandTime() == 0 and not is_heating_demand:
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
                        fh_info_type_r["other"].append("'PRE' & 'CF' summer mode")
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
                                    fh_info_type_r['other'].append(f"'PRE' too early for {_hs.getDemandEnergy():0.1f} W in {HeatingLogHelper.visualizeHeatingDemandTime(_hs.getDemandTime())} min")
                            else:
                                fh_info_type_r["not needed"].append('PRE')
                        else:
                            fh_info_type_r["wrong time"].append('PRE')

                        # *** CHECK FOR COLD FLOOR HEATING ***
                        if last_heating_change > self.cold_floor_timeout:
                            fh_info_type_r["not needed"].append('CF')
                        elif self.possibleColdFloorHeating(night_mode_active,last_heating_change):
                            needed_time = self.getColdFloorHeatingTime(last_heating_change)
                            if hs.getDemandTime() < needed_time:
                                if not self.isNightModeTime( int(round(self.limitHeatingDemandTime( room.getName(), needed_time, 1.5 ) * 60, 0)) ):
                                    hs.setDemandEnergy(None)
                                    hs.setDemandTime(needed_time)
                                    hs.setForcedInfo('CF')
                                else:
                                    fh_info_type_r['other'].append(f"'CF' too early for {HeatingLogHelper.visualizeHeatingDemandTime(needed_time)} min")
                            else:
                                fh_info_type_r["not needed"].append('CF')
                        else:
                            fh_info_type_r["wrong time"].append('CF')
                    
                    if hs.getForcedInfo() is not None:
                        if room.getName() not in self._forced_heatings:
                            self.logDebug(f"DEBUG: activate forced heating {room.getName()}")
                            self._forced_heatings[room.getName()] = { 'heating_state': hs, 'target_temperature': rs.getHeatingTargetTemperature(), 'forced_started': self.now, 'forced_demand_energy': hs.getDemandEnergy(), 'forced_demand_time': hs.getDemandTime()}
                    else:
                        fh_info_r = []
                        for info_type in fh_info_type_r:
                            if len(fh_info_type_r[info_type]) == 0:
                                continue
                            
                            if info_type == 'other':
                                fh_info_r.append( ", ".join(fh_info_type_r[info_type]) )
                            else:
                                fh_info_r.append( f"{" & ".join(fh_info_type_r[info_type])} {info_type}" )
                        hs.setDebugInfo( ", ".join(fh_info_r) )

            hs = rs.getHeatingState()
            if hs.isHeatingRequested():
                active_heating_volume += room.getHeatingVolume()

        # calculate possible volumes late, because they depends on possible heating volume factor
        possible_heating_volume_factor = self.calculateHeatingVolumeFactor(active_heating_volume)
        possible_total_heating_volume = possible_total_heating_radiation = 0
        possible_total_heating_volume_4 = possible_total_heating_radiation_4 = 0
        possible_total_heating_volume_8 = possible_total_heating_radiation_8 = 0
        for room in self.heated_rooms:
            rs4 = cr4.getRoomState(room.getName())
            possible_heating_volume_4, possible_heating_radiation_4 = self.calculateHeatingRadiation(1, room.getHeatingVolume(), cr4.getPossibleHeatingCirculationDiff(), cr4.getPossibleHeatingPumpSpeed())
            possible_total_heating_volume_4 += possible_heating_volume_4
            possible_total_heating_radiation_4 += possible_heating_radiation_4
            rs4.setPossibleHeating(possible_heating_volume_4, possible_heating_radiation_4)

            rs8 = cr8.getRoomState(room.getName())
            possible_heating_volume_8, possible_heating_radiation_8 = self.calculateHeatingRadiation(1, room.getHeatingVolume(), cr8.getPossibleHeatingCirculationDiff(), cr8.getPossibleHeatingPumpSpeed())
            possible_total_heating_volume_8 += possible_heating_volume_8
            possible_total_heating_radiation_8 += possible_heating_radiation_8
            rs8.setPossibleHeating(possible_total_heating_volume_8, possible_heating_radiation_8)

            rs = cr.getRoomState(room.getName())
            hs = rs.getHeatingState()
            if not hs.isHeatingRequested():
                continue
            possible_heating_volume, possible_heating_radiation = self.calculateHeatingRadiation(possible_heating_volume_factor, room.getHeatingVolume(), cr.getPossibleHeatingCirculationDiff(), cr.getPossibleHeatingPumpSpeed())
            possible_total_heating_volume += possible_heating_volume
            possible_total_heating_radiation += possible_heating_radiation
            rs.setPossibleHeating(possible_heating_volume, possible_heating_radiation)

        cr.setPossibleHeating(possible_total_heating_volume, possible_total_heating_radiation)

        cr4.setPossibleHeating(possible_total_heating_volume_4, possible_total_heating_radiation_4)
        cr8.setPossibleHeating(possible_total_heating_volume_8, possible_total_heating_radiation_8)

        cr.setChargeLevelDebugInfos(charge_level_debug_infos)
        
        self.last_runtime = self.now

        if self.debug_logged:
            self.logger.info("        : ---")
            self.debug_logged = False

        return cr, cr4, cr8

class HeatingLogHelper:
    @staticmethod
    def visualizeHeatingDemandTime(heating_demand_time):
        if heating_demand_time < 0:
            return "<1"
        return "~" if heating_demand_time == Heating.INFINITE_HEATING_TIME else int(round(heating_demand_time*60))

    @staticmethod
    def formatEnergy(energy, precision=1):
        return round(energy/60.0, precision)

    @staticmethod
    def logCoolingAndRadiations(logger, prefix, cr, sun_radiation_lazy = None, sun_light_level = None):
        sdi = cr.getSunDebugInfo()

        lazy_radiation_msg = f" (∾ {round(sun_radiation_lazy / 60.0, 1)})" if sun_radiation_lazy is not None else ""
        light_level_msg = f", {int(sun_light_level)} lux" if sun_light_level is not None else ""
        debug_info = f"🌍 Az {sdi["azimut"]}° • El {sdi["elevation"]}{sdi["min_elevation"]}° ⛅ Clouds {cr.getCloudCover():0.1f} 🌞 Sun {sdi["effective_radiation"]}{lazy_radiation_msg} W/min{light_level_msg}{sdi["active"]}"

        logger.info(f"{prefix}: {debug_info}")

        logger.info(f"        : 💨 Wall {HeatingLogHelper.formatEnergy(cr.getWallEnergy())} ({HeatingLogHelper.formatEnergy(cr.getWallRadiation())}☀) W/min • Air {HeatingLogHelper.formatEnergy(cr.getVentilationEnergy())} W/min • Leak {HeatingLogHelper.formatEnergy(cr.getLeakEnergy())} W/min • Window {HeatingLogHelper.formatEnergy(cr.getWindowEnergy())} ({HeatingLogHelper.formatEnergy(cr.getWindowRadiation())}☀) W/min")

        msg = f"{HeatingLogHelper.formatEnergy(cr.getActiveHeatingRadiation())} W/min" if cr.getActiveHeatingRadiation() > 0 else f"{HeatingLogHelper.formatEnergy(cr.getPossibleHeatingRadiation())} W/min (FC)"
        logger.info(f"        : 🏠 ↑↓ {HeatingLogHelper.formatEnergy(cr.getPassiveSaldo())} W/min ({cr.getReferenceTemperature():0.1f}°C) 🔥 HU {msg}")
        logger.info("        : ---")

    @staticmethod
    def logHeatingStates(logger, heating, cr):
        if cr.getActiveHeatingVolume() > 0:
            logger.info(f"Heating : {cr.getActiveHeatingDebugInfo()} ({cr.getActiveHeatingVolume() / 1000.0:0.3f} m³) • Factor {cr.getActiveHeatingVolumeFactor():0.2f} • HU {HeatingLogHelper.formatEnergy(cr.getActiveHeatingRadiation()):0.1f} W/min")
            logger.info("        : ---")

        if len(cr.getChargeLevelDebugInfos()) > 0:
            for charge_level_debug_info in cr.getChargeLevelDebugInfos():
                logger.info(charge_level_debug_info)
            logger.info("        : ---")

        for room in heating.getRooms():
            HeatingLogHelper.logHeatingState(logger, room, cr)

    @staticmethod
    def logHeatingState(logger, room, cr):
        rs = cr.getRoomState(room.getName())
        hs = rs.getHeatingState()

        name = room.getName().replace("room","")
        info_msg = f"{name:<15} • {rs.getCurrentTemperature():0.1f}°C"

        if hs is not None:
            info_msg = f"{info_msg} ({rs.getHeatingTargetTemperature()})"

            state_msg = hs.getInfo()
            if hs.getForcedInfo() is not None:
                state_msg = f"{state_msg} ({hs.getForcedInfo()})"
        else:
            state_msg = None
            info_msg = f"{info_msg}       "

        details = []
        #details.append("{:4.1f}i".format(HeatingLogHelper.formatEnergy(rs.getIndoorWallEnergy())))
        if cr.getSunSouthRadiation() > 0 or cr.getSunWestRadiation() > 0:
            details.append(f"{HeatingLogHelper.formatEnergy(rs.getOutdoorWallRadiation()+rs.getWindowRadiation(),1)}☀")

        details_msg = f" ({", ".join(details)})" if len(details) > 0 else ""
        heating_msg = f"↑↓ {HeatingLogHelper.formatEnergy(rs.getPassiveSaldo(), 1)}{details_msg} W/min"

        # COLD, WARM, UNLOAD etc
        info_msg = f"{info_msg} • {state_msg if state_msg else "      " if cr.getActiveHeatingRadiation() > 0 else "":<6}"

        info_msg = f"{info_msg} • {f"{heating_msg:<21}" if len(details) > 0 else f"{heating_msg:<14}"}"

        # **** DEBUG ****
        #info_msg = "{} • DEBUG {} {}".format(info_msg, rs.getPossibleHeatingRadiation(), rs.getPossibleHeatingVolume())

        if hs is not None:
            # show heating details per room if total heating is active
            if cr.getActiveHeatingRadiation() > 0:
                info_msg = f"{info_msg} • HU {HeatingLogHelper.formatEnergy(rs.getActiveHeatingRadiation(),1)} W/min"

            adjustedBuffer = ""
            if hs.getChargedReserveBuffer() != rs.getHeatingChargedBuffer() or hs.getAdjustedChargedBuffer() is not None:
                if hs.getChargedReserveBuffer() != rs.getHeatingChargedBuffer():
                    adjustedBuffer = f"{adjustedBuffer}{int(round(rs.getHeatingChargedBuffer()))}"
                if hs.getAdjustedChargedBuffer() is not None:
                    adjustedBuffer = f"{adjustedBuffer} => {int(round(hs.getAdjustedChargedBuffer()))}"
                adjustedBuffer = f" ({adjustedBuffer})"

            percent = int(round(hs.getChargedReserveBuffer() * 100 / rs.getBufferSlotCapacity() ))
            info_msg = f"{info_msg} • BF {percent}%, {int(round(hs.getChargedReserveBuffer()))}{adjustedBuffer} W"

            reduction_msg = []
            if hs.getOutdoorReduction() > 0:
                reduction_msg.append(f"OR {hs.getOutdoorReduction()}")
            if hs.getNightReduction() > 0:
                reduction_msg.append(f"NR {hs.getNightReduction()}")
            if hs.getLazyReduction() > 0:
                reduction_msg.append(f"LR {hs.getLazyReduction()}")
            if hs.getForcedReduction() > 0:
                reduction_msg.append(f"FR {hs.getForcedReduction()}")
            if len(reduction_msg) > 0:
                info_msg = f"{info_msg} • {", ".join(reduction_msg)}"

            debug_msg = f" • ({hs.getDebugInfo()})" if hs.getDebugInfo() is not None else ""

            if hs.getDemandTime() is not None:
                if hs.getDemandTime() > 0:
                    info_msg = f"{info_msg} • HU {round(hs.getDemandEnergy(),1) if hs.getDemandEnergy() is not None else "~"} W in {HeatingLogHelper.visualizeHeatingDemandTime( hs.getDemandTime() )} min"
                    logger.info(f"  {"   ON" if rs.getHeatingCircuitState() == scope.ON else " (ON)"} : {info_msg}{debug_msg}")
                else:
                    logger.info(f"  {"  OFF" if rs.getHeatingCircuitState() == scope.OFF else "(OFF)"} : {info_msg}{debug_msg}")
            else:
                logger.info(f"SKIPPED : {info_msg}{debug_msg}")
        else:
            logger.info(f"        : {info_msg}")
