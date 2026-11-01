from openhab import Registry
from shared.toolbox import ToolboxHelper
from custom.suncalculation import SunRadiation
from custom.heating2.model.state import HouseState, RoomState

from custom.heating.house import ThermalBridgeType

from datetime import datetime, timedelta

import scope

class Heating:
    GROUND_TEMPERATURES_PER_MONTH = {1: 6, 2: 5, 3: 5.5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 13, 11: 11, 12: 9} # Month / AVG °C

    OPEN_WINDOW_START_DURATION = 2
    LONG_OPEN_WINDOW_START_DURATION = 5

    # To warmup 1 liter of water you need 4,182 Kilojoule
    # 1 Wh == 3,6 kJ
    # 1000 l * 4,182 kJ / 3,6kJ = 1161,66666667
    HEATING_REFERENCE_ENERGY = 1162 # per Watt je m³/K

    HEATING_CURVE_START_TEMPERATURE = 25
    HEATING_CURVE_SLOPE = 0.3

    DENSITY_AIR = 1.2041
    C_AIR = 1.005

    # http://www.luftdicht.de/Paul-Luftvolumenstrom_durch_Undichtheiten.pdf
    LEAKING_N50 = 1.0
    LEAKING_E = 0.07
    LEAKING_F = 15.0

    def __init__(self,
                 rooms,
                 data_item_name,
                 forecast_cloud_cover_item_name, forecast_temperature_item_name,
                 ventilation_volume_item_name, ventilation_outgoing_temperature_item_name, ventilation_incoming_temperature_item_name,
                 heating_state_item_name, heating_temperature_pipe_out_item_name, heating_temperature_pipe_in_item_name,
                 presence_status_item_name, heating_reduction_item_name,
                 temperature_sensor_item_name_placeholder, temperature_target_item_name_placeholder,
                 heating_hk_item_name_placeholder, heating_circuit_item_name_placeholder, heating_demand_item_name_placeholder, heating_target_temperature_item_name_placeholder ):
        self.rooms = {}

        self.total_heating_volume = 0.0
        for room in rooms:
            room_id = room.getName()[1:]
            self.rooms[room_id] = room

            if room.getHeatingVolume() is not None:
                self.total_heating_volume += room.getHeatingVolume()

        self.total_ventilation_volume = sum(room.getVolume() for room in self.rooms.values() if room.hasVentilation())

        self.data_item_name = data_item_name

        self.forecast_cloud_cover_item_name = forecast_cloud_cover_item_name
        self.forecast_temperature_item_name = forecast_temperature_item_name

        self.ventilation_volume_item_name = ventilation_volume_item_name
        self.ventilation_outgoing_temperature_item_name = ventilation_outgoing_temperature_item_name
        self.ventilation_incoming_temperature_item_name = ventilation_incoming_temperature_item_name

        self.heating_state_item_name = heating_state_item_name
        self.heating_temperature_pipe_out_item_name = heating_temperature_pipe_out_item_name
        self.heating_temperature_pipe_in_item_name = heating_temperature_pipe_in_item_name

        self.presence_status_item_name = presence_status_item_name
        self.heating_reduction_item_name = heating_reduction_item_name

        self.temperature_sensor_item_name_placeholder = temperature_sensor_item_name_placeholder
        self.temperature_target_item_name_placeholder = temperature_target_item_name_placeholder

        self.heating_hk_item_name_placeholder = heating_hk_item_name_placeholder
        self.heating_circuit_item_name_placeholder = heating_circuit_item_name_placeholder
        self.heating_demand_item_name_placeholder = heating_demand_item_name_placeholder
        self.heating_target_temperature_item_name_placeholder = heating_target_temperature_item_name_placeholder

        self.now = None
        self.current_temperature_garden_item_name = None
        self.active_total_heating_volume = None

        self.ventilation_temp_diff = self.ventilation_volume = None

        self.room_open_window_states_map = self.open_transitions_map = None
        self._open_window_contacts = {} # state map

        self.forecast_temperature_4 = self.forecast_temperature_8 = self.forecast_cloud_cover_0 = self.forecast_cloud_cover_4 = self.forecast_cloud_cover_8 = None
        self.refreshForecastInterval()

        # Load or initialize state structure
        json_data = Registry.getItemState(self.data_item_name)
        if json_data == scope.NULL:
            room_states = {}

            for room_id, room in self.rooms.items():
                temperature_item = Registry.getItem(self.temperature_sensor_item_name_placeholder.format(room_id))
                last_temperature_value = round(temperature_item.getLastState().doubleValue(), 1)
                last_temperature_change = temperature_item.getLastStateChange()

                room_state = RoomState(room_id, last_temperature_value, last_temperature_change)
                room_states[room_id] = room_state
            self.house_state = HouseState(room_states)
        else:
            #print(json_data)
            self.house_state = HouseState.load(str(json_data))


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

    def refreshHeatingInterval(self, current_temperature_garden_item_name, now):
        self.current_temperature_garden_item_name = current_temperature_garden_item_name
        self.now = now
        self.now_4 = now + timedelta(minutes=240)
        self.now_8 = now + timedelta(minutes=480)
        self.open_window_start_time = self.now - timedelta(minutes=self.OPEN_WINDOW_START_DURATION)

        # Update state structure with current data
        self.active_total_heating_volume = 0.0
        for room_id, state in self.house_state.getRoomStates().items():
            room = self.rooms[room_id]

            current_temperature = round( ToolboxHelper.getStableState(self.temperature_sensor_item_name_placeholder.format(room_id), 120, self.now).doubleValue(), 1)

            if room.getHeatingVolume() is not None:
                target_temperature = round(Registry.getItemState(self.temperature_target_item_name_placeholder.format(room_id)).doubleValue(), 1)
                heating_target_temperature = round(Registry.getItemState(self.heating_target_temperature_item_name_placeholder.format(room_id)).doubleValue(), 1)
                heating_circuit_state = Registry.getItemState(self.heating_circuit_item_name_placeholder.format(room_id)) == scope.ON
                heating_demand_last_changed = Registry.getItem(self.heating_demand_item_name_placeholder.format(room_id)).getLastStateUpdate()

                if heating_circuit_state:
                     self.active_total_heating_volume += room.getHeatingVolume()
            else:
                target_temperature = heating_target_temperature = heating_demand_last_changed = None
                heating_circuit_state = False

            if state.refresh(self.now, current_temperature, target_temperature, heating_target_temperature, heating_circuit_state, heating_demand_last_changed):
                print(f"Room {room_id} changed from {state.last_temperature} to {state.current_temperature}")

        ventilation_volume = Registry.getItemState(self.ventilation_volume_item_name)
        if ventilation_volume != scope.UNDEF:
            self.ventilation_volume = ventilation_volume.intValue()
            self.ventilation_temp_diff = Registry.getItemState(self.ventilation_outgoing_temperature_item_name).doubleValue() - Registry.getItemState(self.ventilation_incoming_temperature_item_name).doubleValue()
        else:
            self.ventilation_temp_diff = self.ventilation_volume = 0

        self.room_open_window_states_map, self.open_transitions_map = self._calculateOpenWindowStates()

    def _calculateOpenWindowStates(self):
        room_open_window_states_map = {}
        open_transitions_map = {}

        for room_id, room in self.rooms.items():
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

    # *********** PASSIVE COOLING/HEATING ************
    def updateEnergySlotStates(self, slot, now, cloud_cover, outdoor_temperature_base, outdoor_temperature_current, sun_radiation):
        is_forecast = outdoor_temperature_base != outdoor_temperature_current

        current_total_ventilation_energy = self.getVentilationEnergy(outdoor_temperature_base - outdoor_temperature_current)

        sun_east_radiation, sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info = SunRadiation.getSunPowerPerHour(now, cloud_cover, sun_radiation)
        sun_east_radiation_max, sun_south_radiation_max, sun_west_radiation_max, sun_radiation_max, sun_max_debug_info = SunRadiation.getSunPowerPerHour(now, 0)

        possible_heating_circulation_diff = self.calculatePossibleHeatingCirculationDiff(outdoor_temperature_current)

        total_possible_heating_volume = total_possible_heating_radiation = 0
        for room_id, state in self.house_state.getRoomStates().items():
            room = self.rooms[room_id]

            # *** WALL COOLING AND RADIATION ***
            indoor_wall_energy, ground_energy, outdoor_wall_energy, outdoor_wall_radiation = self.getWallCoolingAndRadiations(state.current_temperature, outdoor_temperature_current, sun_east_radiation, sun_south_radiation, sun_west_radiation, room)

            # *** WINDOW COOLING AND RADIATION ***
            window_energy, window_radiation = self.getWindowCoolingAndRadiations(state.current_temperature, outdoor_temperature_current, sun_east_radiation, sun_south_radiation, sun_west_radiation, room, is_forecast)

            # *** VENTILATION COOLING ***
            if room.hasVentilation():
                ventilation_energy = room.getVolume() * current_total_ventilation_energy / self.total_ventilation_volume
            else:
                ventilation_energy = 0

            leak_energy = self.getLeakingEnergy(room.getVolume(), state.current_temperature, outdoor_temperature_current)

            if room.getHeatingVolume() is not None:
                possible_heating_volume, possible_heating_radiation = self.calculateHeatingRadiation(1, room.getHeatingVolume(), possible_heating_circulation_diff)
                total_possible_heating_volume += possible_heating_volume
                total_possible_heating_radiation += possible_heating_radiation
            else:
                possible_heating_volume = possible_heating_radiation = 0

            state.setEnergySlotData(slot,
                possible_heating_volume, possible_heating_radiation,
                indoor_wall_energy, ground_energy, outdoor_wall_energy, outdoor_wall_radiation,
                window_energy, window_radiation,
                ventilation_energy,
                leak_energy
            )

        self.house_state.setEnergySlotData(slot, total_possible_heating_volume, total_possible_heating_radiation, outdoor_temperature_current, cloud_cover, sun_east_radiation, sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info)

    def getCoolingEnergy(self, area, current_temperature, outdoor_temperature, thermal_type, bound):
        if thermal_type is not None and thermal_type.getUValue() is not None:
            # outdoor temperature is only relevant for walls "bounded" to outside (is None)
            reference_temperature = outdoor_temperature if bound is None else self.house_state.getRoomState(bound[1:]).current_temperature
            temperature_difference = current_temperature - reference_temperature
            cooling_per_kelvin =( thermal_type.getUValue() + thermal_type.getUOffset() ) * area
            cooling_total = cooling_per_kelvin * temperature_difference
            return cooling_total * -1 if cooling_total != 0 else 0.0
        else:
            return 0.0

    def getWindowCoolingAndRadiations(self, current_temperature, garden_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room, is_forecast):
        window_energy = window_radiation = 0
        for transition in room.getTransitions():
            if not is_forecast and transition in self.open_transitions_map:
                window_energy += self.getCoolingEnergy(transition.getArea(), current_temperature, garden_temperature, ThermalBridgeType( uValue=10.0, uOffset=0.1 ), None)
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

        return window_energy, window_radiation

    def getWallCoolingAndRadiations(self, current_temperature, outdoor_temperature, sun_east_radiation, sun_south_radiation, sun_west_radiation, room):
        ground_cooling = outdoor_wall_cooling = indoor_wall_cooling = outdoor_wall_radiation = 0
        for wall in room.getWalls():
            # is used only by ground floor calculation, because getCoolingEnergy checks for bound is None (=> to outside) too
            outdoor_temperature_ref = self.GROUND_TEMPERATURES_PER_MONTH[self.now.month] if wall.getDirection() == 'floor' else outdoor_temperature
            cooling = self.getCoolingEnergy(wall.getArea(), current_temperature, outdoor_temperature_ref, wall.getType(), wall.getBound())

            if wall.getBound() is None:
                if wall.getDirection() == 'floor':
                    ground_cooling += cooling
                else:
                    outdoor_wall_cooling += cooling
                    if wall.getDirection() == 'east':
                        outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_east_radiation)
                    elif wall.getDirection() == 'south':
                        outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_south_radiation)
                    elif wall.getDirection() == 'west':
                        outdoor_wall_radiation += SunRadiation.getWallSunPowerPerHour(wall.getArea(), sun_west_radiation)
            else:
                indoor_wall_cooling += cooling

        return indoor_wall_cooling, ground_cooling, outdoor_wall_cooling, outdoor_wall_radiation

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

    # *********** ACTIVE HEATING ************
    def updateActiveRoomStates(self):
        active_heating_volume_factor = self.calculateHeatingVolumeFactor(self.active_total_heating_volume)
        active_heating_circulation_diff, active_heating_circulation_debug_info = self.calculateActiveHeatingCirculationDiff()

        total_active_heating_volume = total_active_heating_radiation = 0
        for room_id, state in self.house_state.getRoomStates().items():
            room = self.rooms[room_id]

            if room.getHeatingVolume() is not None:
                if state.heating_circuit_state:
                    active_heating_volume, active_heating_radiation = self.calculateHeatingRadiation(active_heating_volume_factor, room.getHeatingVolume(), active_heating_circulation_diff)
                    total_active_heating_volume += active_heating_volume
                    total_active_heating_radiation += active_heating_radiation
                else:
                    active_heating_volume, active_heating_radiation = 0.0, 0.0
            else:
                active_heating_volume = active_heating_radiation = None

            state.setActiveEnergyData(active_heating_volume, active_heating_radiation)

        self.house_state.setActiveEnergyData(total_active_heating_volume, total_active_heating_radiation, active_heating_circulation_debug_info)

    def calculatePossibleHeatingCirculationDiff(self, outdoor_temperature):
        temperature_pipe_in = self.HEATING_CURVE_START_TEMPERATURE #sum(temperatures) / float(len(temperatures)) + 1.5
        if outdoor_temperature > self.HEATING_CURVE_START_TEMPERATURE:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE
        else:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE + ((outdoor_temperature - self.HEATING_CURVE_START_TEMPERATURE) * -1 * self.HEATING_CURVE_SLOPE)
        return temperature_pipe_out - temperature_pipe_in

    def calculateActiveHeatingCirculationDiff(self):
        if Registry.getItemState(self.heating_state_item_name) == scope.OFF:
            return 0, ""
        temperature_pipe_out = round(Registry.getItemState(self.heating_temperature_pipe_out_item_name).doubleValue(), 1)
        temperature_pipe_in = round(Registry.getItemState(self.heating_temperature_pipe_in_item_name).doubleValue(), 1)
        circulation_diff = round(temperature_pipe_out - temperature_pipe_in, 2)
        return circulation_diff, f"Diff {circulation_diff:0.2f}°C • VL {temperature_pipe_out:0.1f}°C • RL {temperature_pipe_in:0.1f}°C"

    def calculatePossibleHeatingCirculationDiff(self, outdoor_temperature):
        temperature_pipe_in = self.HEATING_CURVE_START_TEMPERATURE + 1.5 #sum(temperatures) / float(len(temperatures)) + 1.5
        if outdoor_temperature > self.HEATING_CURVE_START_TEMPERATURE:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE
        else:
            temperature_pipe_out = self.HEATING_CURVE_START_TEMPERATURE + ((outdoor_temperature - self.HEATING_CURVE_START_TEMPERATURE) * -1 * self.HEATING_CURVE_SLOPE)
        circulation_diff = temperature_pipe_out - temperature_pipe_in

        return circulation_diff

    def calculateHeatingRadiation(self, heating_volume_factor, room_heating_volume, circulation_diff):
        pump_volume = room_heating_volume * heating_volume_factor
        # pump_volume / 1000.0 => convert liter => m³
        heating_energy = Heating.HEATING_REFERENCE_ENERGY * (pump_volume / 1000.0) * circulation_diff
        return pump_volume, heating_energy

    def calculateHeatingVolumeFactor(self, active_heating_volume):
        # Data are measured
        # actives volumen => factor real volumen
        # 0.75 => x2
        # 11.75 => x1
        # self.total_heating_volume => 12.05
        ratio = (((active_heating_volume / 60) - 0.75) * 1) / ((self.total_heating_volume / 60) - 0.75)
        return round(max(min(2 - ratio, 2), 1), 2)

    def processBuffer(self):
        timespan_in_hours = (30.0 if self.house_state.last_runtime is None else (self.now - self.house_state.last_runtime).total_seconds()) / 60 / 60
        passive_energy_slot = self.house_state.getPassiveEnergySlot("0")

        for room_id, room_state in self.house_state.getRoomStates().items():
            #room_state.buffer_ground = 0
            #room_state.buffer_volume = 0
            #room_state.buffer_inner_wall = 0
            #room_state.buffer_outer_wall = 0

            #if room_state.active_heating_volume is None or room_state.active_heating_volume == 0:
            #    continue

            _data = room_state.passive_energy_slots["0"]
            _room = self.rooms[room_id]

            ground_outside_lost_per_kelvin = 0
            ground_inside_lost_per_kelvin = 0
            ground_area = 0
            ground_capacity = 0

            wall_inner_lost_per_kelvin = 0
            wall_inner_area = 0
            wall_inner_capacity = 0

            wall_outer_outside_lost_per_kelvin = 0
            wall_outer_inside_lost_per_kelvin = 0
            wall_outer_area = 0
            wall_outer_capacity = 0

            volume_capacity = _room.getVolume() * self.DENSITY_AIR * self.C_AIR * 5 # Faktor 5 (Standardwert für normale Räume)

            for wall in _room.getWalls():
                if wall.getDirection() == "floor":
                    if wall.getType().getUValueInner() is not None:
                        ground_outside_lost_per_kelvin += wall.getType().getUValueOuter() * wall.getArea()
                        ground_inside_lost_per_kelvin += wall.getType().getUValueInner() * wall.getArea()
                    else:
                        _ground_lost = wall.getType().getUValue() * wall.getArea()
                        ground_outside_lost_per_kelvin += _ground_lost / 2
                        ground_inside_lost_per_kelvin += _ground_lost / 2

                    ground_area += wall.getArea()
                    ground_capacity += wall.getCapacityInWattHours() * wall.getArea()
                elif wall.getBound() is None:
                    _wall_outer_lost = wall.getType().getUValue() * wall.getArea()
                    wall_outer_outside_lost_per_kelvin += _wall_outer_lost / 2
                    wall_outer_inside_lost_per_kelvin += _wall_outer_lost / 2

                    wall_outer_area += wall.getArea()
                    wall_outer_capacity += wall.getCapacityInWattHours() * wall.getArea()
                else:
                    _wall_inner_lost = wall.getType().getUValue() * wall.getArea()
                    wall_inner_lost_per_kelvin += _wall_inner_lost / 2

                    wall_inner_area += wall.getArea()
                    wall_inner_capacity += wall.getCapacityInWattHours() * wall.getArea()

            # ***** Ground *****
            if room_state.active_heating_radiation is not None and room_state.active_heating_radiation > 0:
                room_state.buffer_ground += room_state.active_heating_radiation * timespan_in_hours

            ground_temperature_offset = room_state.buffer_ground / ground_capacity
            ground_inner_lost = ground_temperature_offset * ground_inside_lost_per_kelvin
            #ground_outer_lost = ground_temperature_offset * ground_outside_lost_per_kelvin

            saldo_ground = (ground_inner_lost * -1) + _data.ground_energy
            room_state.buffer_ground += saldo_ground * timespan_in_hours
            if room_state.buffer_ground < 0:
                room_state.buffer_ground = 0
            # ******************

            # ***** Volume *****
            volume_temperature_offset = room_state.buffer_volume / volume_capacity
            volume_inner_lost = volume_temperature_offset * wall_inner_lost_per_kelvin
            volume_outer_inner_lost = volume_temperature_offset * wall_outer_inside_lost_per_kelvin

            saldo_volume = ((volume_inner_lost + volume_outer_inner_lost) * -1) + ground_inner_lost + _data.window_energy + _data.window_radiation + _data.ventilation_energy + _data.leak_energy
            # ******************

            # *** Inner Walls **
            saldo_inner_wall = volume_inner_lost + _data.indoor_wall_energy
            room_state.buffer_inner_wall += saldo_inner_wall * timespan_in_hours
            if room_state.buffer_inner_wall < 0:
                room_state.buffer_inner_wall = 0

            if wall_inner_capacity > 0:
                wall_inner_temperature_offset = room_state.buffer_inner_wall / wall_inner_capacity
                wall_inner_lost = wall_inner_temperature_offset * wall_inner_lost_per_kelvin

                saldo_volume += wall_inner_lost
            # ******************

            # *** Outer Walls **
            saldo_outer_wall = volume_outer_inner_lost + _data.outdoor_wall_energy + _data.outdoor_wall_radiation
            room_state.buffer_outer_wall += saldo_outer_wall * timespan_in_hours
            if room_state.buffer_outer_wall < 0:
                room_state.buffer_outer_wall = 0

            if wall_outer_capacity > 0:
                wall_outer_temperature_offset = room_state.buffer_outer_wall / wall_outer_capacity
                wall_outer_inner_lost = wall_outer_temperature_offset * wall_outer_inside_lost_per_kelvin
                #wall_outer_outer_lost = wall_outer_temperature_offset * wall_outer_outside_lost_per_kelvin

                saldo_volume += wall_outer_inner_lost
            # ******************

            room_state.buffer_volume += saldo_volume * timespan_in_hours
            if room_state.buffer_volume < 0:
                room_state.buffer_volume = 0

            heating_msg = f"{int(round(room_state.active_heating_radiation,0))}" if room_state.active_heating_radiation is not None else "0"
            ground_msg = f"{int(round(room_state.buffer_ground,0))} (Δ{int(round(saldo_ground,0))})"
            volume_msg = f"{int(round(room_state.buffer_volume,0))} (Δ{int(round(saldo_volume,0))})"
            wall_inner_msg = f"{int(round(room_state.buffer_inner_wall,0))} (Δ{int(round(saldo_inner_wall,0))})"
            wall_outer_msg = f"{int(round(room_state.buffer_outer_wall,0))} (Δ{int(round(saldo_outer_wall,0))})"

            print(f"DEBUG   : {room_id:<18}, HR: {heating_msg:<3}, Ground: {ground_msg:<15}, Volume: {volume_msg:<15}, Wall (Inner): {wall_inner_msg:<15}, Wall (Outer): {wall_outer_msg:<15}")
            #print("    VOLUME", ground_inner_lost, _data.window_energy, _data.window_radiation, _data.ventilation_energy, _data.leak_energy)
            #print("    WALL", volume_outer_inner_lost, _data.outdoor_wall_radiation)

            #indoor_wall_energy, ground_energy, outdoor_wall_energy

        print("        : ---")

        self.house_state.last_runtime = self.now

    def calculate(self, sun_radiation):
        temperature = round( ToolboxHelper.getStableState(self.current_temperature_garden_item_name, 120, self.now).doubleValue(), 1)
        # handle outdated forecast values
        if self.forecast_temperature_4 is None or self.forecast_temperature_8 is None:
            temperature_4 = temperature_8 = temperature
        else:
            temperature_4 = self.forecast_temperature_4
            temperature_8 = self.forecast_temperature_8

        self.updateEnergySlotStates("0", self.now, self.forecast_cloud_cover_0, temperature, temperature, sun_radiation)
        self.updateEnergySlotStates("4", self.now_4, self.forecast_cloud_cover_4, temperature, temperature_4, 0)
        self.updateEnergySlotStates("8", self.now_8, self.forecast_cloud_cover_8, temperature, temperature_8, 0)

        self.updateActiveRoomStates()

        self.processBuffer()

        # Persist House State
        json_data = HouseState.dump(self.house_state)
        #print(json_data)
        Registry.getItem(self.data_item_name).postUpdate(json_data)

class HeatingLogHelper:
    @staticmethod
    def formatEnergy(energy, precision=1):
        return round(energy/60.0, precision)

    @staticmethod
    def logCoolingAndRadiations(logger, heating, prefix, slot, sun_radiation_lazy = None, sun_light_level = None):
        passive_energy_data = heating.house_state.getPassiveEnergySlot(slot)

        sdi = passive_energy_data.sun_debug_info

        lazy_radiation_msg = f" (∾ {round(sun_radiation_lazy / 60.0, 1)})" if sun_radiation_lazy is not None else ""
        light_level_msg = f", {int(sun_light_level)} lux" if sun_light_level is not None else ""
        debug_info = f"🌍 Az {sdi["azimut"]}° • El {sdi["elevation"]}{sdi["min_elevation"]}° ⛅ Clouds {passive_energy_data.cloud_cover:0.1f} 🌞 Sun {sdi["effective_radiation"]}{lazy_radiation_msg} W/min{light_level_msg}{sdi["active"]}"
        logger.info(f"{prefix}: {debug_info}")

        outdoor_wall_energy = outdoor_wall_radiation = ventilation_energy = leak_energy = window_energy = window_radiation = 0
        for room_id, room_state in heating.house_state.getRoomStates().items():
            _data = room_state.passive_energy_slots[slot]
            outdoor_wall_energy += _data.ground_energy + _data.outdoor_wall_energy
            outdoor_wall_radiation += _data.outdoor_wall_radiation
            ventilation_energy += _data.ventilation_energy
            leak_energy += _data.leak_energy
            window_energy += _data.window_energy
            window_radiation += _data.window_radiation
        logger.info(f"        : 💨 Wall {HeatingLogHelper.formatEnergy(outdoor_wall_energy)} ({HeatingLogHelper.formatEnergy(outdoor_wall_radiation)}☀) W/min • Air {HeatingLogHelper.formatEnergy(ventilation_energy)} W/min • Leak {HeatingLogHelper.formatEnergy(leak_energy)} W/min • Window {HeatingLogHelper.formatEnergy(window_energy)} ({HeatingLogHelper.formatEnergy(window_radiation)}☀) W/min")

        passive_saldo = outdoor_wall_energy + outdoor_wall_radiation + ventilation_energy + leak_energy + window_energy + window_radiation

        if slot == "0" and heating.house_state.active_heating_radiation > 0:
            msg = f"{HeatingLogHelper.formatEnergy(heating.house_state.active_heating_radiation)} W/min"
        else:
            msg = f"{HeatingLogHelper.formatEnergy(passive_energy_data.possible_heating_radiation)} W/min (FC)"
        logger.info(f"        : 🏠 ↑↓ {HeatingLogHelper.formatEnergy(passive_saldo)} W/min ({passive_energy_data.outdoor_temperature:0.1f}°C) 🔥 HU {msg}")
        logger.info("        : ---")









