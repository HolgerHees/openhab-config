class State(object):
    def __init__(self, buffer_capacity, indoor_wall_energy, outdoor_wall_energy, outdoor_wall_radiation, ventilation_energy, leak_energy, window_energy, window_radiation, open_window_count, heating_volume, heating_radiation, possible_heating_volume, possible_heating_radiation):
        self.buffer_capacity = buffer_capacity
        self.indoor_wall_energy = indoor_wall_energy
        self.outdoor_wall_energy = outdoor_wall_energy
        self.outdoor_wall_radiation = outdoor_wall_radiation
        self.ventilation_energy = ventilation_energy
        self.leak_energy = leak_energy
        self.window_energy = window_energy
        self.window_radiation = window_radiation
        self.open_window_count = open_window_count
        self.heating_volume = heating_volume
        self.heating_radiation = heating_radiation
        self.possible_heating_volume = possible_heating_volume
        self.possible_heating_radiation = possible_heating_radiation

    def getBufferCapacity(self):
        return self.buffer_capacity

    def getBufferSlotCapacity(self):
        return self.buffer_capacity * 0.1

    def getIndoorWallEnergy(self):
        return self.indoor_wall_energy

    def getOutdoorWallEnergy(self):
        return self.outdoor_wall_energy
        
    def getWallEnergy(self):
        return self.indoor_wall_energy + self.outdoor_wall_energy

    def getOutdoorWallRadiation(self):
        return self.outdoor_wall_radiation

    def getWallRadiation(self):
        return self.outdoor_wall_radiation

    def getVentilationEnergy(self):
        return self.ventilation_energy

    def getLeakEnergy(self):
        return self.leak_energy

    def getWindowEnergy(self):
        return self.window_energy

    def getWindowRadiation(self):
        return self.window_radiation

    def getOpenWindowCount(self):
        return self.open_window_count

    def getPassiveSaldo(self):
        return self.outdoor_wall_energy + self.indoor_wall_energy + self.outdoor_wall_radiation + self.ventilation_energy + self.leak_energy + self.window_energy + self.window_radiation
      
    def getActiveSaldo(self):
        return self.getPassiveSaldo() + self.getHeatingRadiation()
      
    def getActivePossibleSaldo(self):
        return self.getPassiveSaldo() + self.getPossibleHeatingRadiation()

    def getHeatingVolume(self):
        return self.heating_volume

    def getHeatingRadiation(self):
        return self.heating_radiation

    def getPossibleHeatingRadiation(self):
        return self.possible_heating_radiation

    def getPossibleHeatingVolume(self):
        return self.possible_heating_volume

class HouseState(State):
    def __init__(self,
            room_states, reference_temperature, heating_pump_speed, heating_volume_factor, heating_debug_info,
            cloud_cover, sun_radiation, sun_radiation_max, sun_south_radiation, sun_south_radiation_max, sun_west_radiation, sun_west_radiation_max, sun_debug_info
        ):

        indoor_wall_energy = outdoor_wall_energy = outdoor_wall_radiation = ventilation_energy = leak_energy = window_energy = window_radiation = 0
        heating_volume = heating_radiation = possible_heating_volume = possible_heating_radiation = 0
        open_window_count = buffer_capacity = 0

        for room_state in room_states.values():
            # summarize room values
            #indoor_wall_energy += room_state.getIndoorWallEnergy() # Not needed. A hous has no inner walls. Just outdoor walls.
            outdoor_wall_energy += room_state.getOutdoorWallEnergy()
            outdoor_wall_radiation += room_state.getOutdoorWallRadiation()
            ventilation_energy += room_state.getVentilationEnergy()
            leak_energy += room_state.getLeakEnergy()
            window_energy += room_state.getWindowEnergy()
            window_radiation += room_state.getWindowRadiation()
            open_window_count += room_state.getOpenWindowCount()

            heating_volume += room_state.getHeatingVolume()
            heating_radiation += room_state.getHeatingRadiation()
            possible_heating_volume += room_state.getPossibleHeatingVolume()
            possible_heating_radiation += room_state.getPossibleHeatingRadiation()

            buffer_capacity += room_state.getBufferCapacity()


        super().__init__(
            buffer_capacity = buffer_capacity,
            indoor_wall_energy = indoor_wall_energy,
            outdoor_wall_energy = outdoor_wall_energy,
            outdoor_wall_radiation = outdoor_wall_radiation,
            ventilation_energy = ventilation_energy,
            leak_energy = leak_energy,
            open_window_count = open_window_count,
            window_energy = window_energy,
            window_radiation = window_radiation,
            heating_volume = heating_volume,
            heating_radiation = heating_radiation,
            possible_heating_volume = possible_heating_volume,
            possible_heating_radiation = possible_heating_radiation
        )

        self.room_states = room_states
        self.reference_temperature = reference_temperature
        self.heating_pump_speed = heating_pump_speed
        self.heating_volume_factor = heating_volume_factor
        self.heating_debug_info = heating_debug_info
        self.cloud_cover = cloud_cover
        self.sun_radiation = sun_radiation
        self.sun_radiation_max = sun_radiation_max
        self.sun_south_radiation = sun_south_radiation
        self.sun_south_radiation_max = sun_south_radiation_max
        self.sun_west_radiation = sun_west_radiation
        self.sun_west_radiation_max = sun_west_radiation_max
        self.sun_debug_info = sun_debug_info

    def getRoomStates(self):
        return self.room_states

    def getRoomState(self,roomName):
        return self.room_states[roomName]

    def getReferenceTemperature(self):
        return self.reference_temperature

    def getHeatingPumpSpeed(self):
        return self.heating_pump_speed

    def getHeatingVolumeFactor(self):
        return self.heating_volume_factor

    def getHeatingDebugInfo(self):
        return self.heating_debug_info

    def getCloudCover(self):
        return self.cloud_cover

    def getSunRadiation(self):
        return self.sun_radiation

    def getSunRadiationMax(self):
        return self.sun_radiation_max

    def getSunSouthRadiation(self):
        return self.sun_south_radiation

    def getSunSouthRadiationMax(self):
        return self.sun_south_radiation_max

    def getSunWestRadiation(self):
        return self.sun_west_radiation

    def getSunWestRadiationMax(self):
        return self.sun_west_radiation_max

    def getSunDebugInfo(self):
        return self.sun_debug_info

    def setChargeLevelDebugInfos(self, value):
        self.charge_level_debug_infos = value

    def getChargeLevelDebugInfos(self):
        return self.charge_level_debug_infos

class RoomState(State):
    def __init__(self,
                 name, current_temperature, target_temperature, heating_target_temperature, heating_circuit_state, heating_last_changed,
                 buffer_capacity, indoor_wall_energy, outdoor_wall_energy, outdoor_wall_radiation, ventilation_energy, leak_energy, window_energy, window_radiation, open_window_count, heating_volume, heating_radiation, possible_heating_volume, possible_heating_radiation):
        super().__init__(
            buffer_capacity = buffer_capacity,
            indoor_wall_energy = indoor_wall_energy,
            outdoor_wall_energy = outdoor_wall_energy,
            outdoor_wall_radiation = outdoor_wall_radiation,
            ventilation_energy = ventilation_energy,
            leak_energy = leak_energy,
            window_energy = window_energy,
            window_radiation = window_radiation,
            open_window_count = open_window_count,
            heating_volume = heating_volume,
            heating_radiation = heating_radiation,
            possible_heating_volume = possible_heating_volume,
            possible_heating_radiation = possible_heating_radiation
        )

        self.name = name

        self.current_temperature = current_temperature
        self.target_temperature = target_temperature

        self.heating_target_temperature = heating_target_temperature
        self.heating_circuit_state = heating_circuit_state
        self.heating_last_changed = heating_last_changed

        self.heating_charged_buffer = 0
        self.heating_state = None

    def getName(self):
        return self.name

    def getCurrentTemperature(self):
        return self.current_temperature

    def getTargetTemperature(self):
        return self.target_temperature

    def getHeatingCircuitState(self):
        return self.heating_circuit_state

    def getHeatingTargetTemperature(self):
        return self.heating_target_temperature

    def getHeatingLastChanged(self):
        return self.heating_last_changed

    def setHeatingChargedBuffer(self, value):
        self.charged_buffer = value

    def getHeatingChargedBuffer(self):
        return self.charged_buffer

    def getHeatingState(self):
        return self.heating_state

    def setHeatingState(self, state, heating_target_temperature):
        self.heating_state = state
        self.heating_target_temperature = heating_target_temperature

    def setNightMode(self, night_mode_active):
        self.night_mode_active = night_mode_active

    def getNightMode(self):
        return self.night_mode_active

class HeatingState(State):
    def __init__(self, night_reduction, outdoor_reduction, forced_reduction):
        self.nightReduction = night_reduction
        self.outdoorReduction = outdoor_reduction
        self.forcedReduction = forced_reduction

        self.info = None
        self.forcedInfo = None
        self.debugInfo = None
        self.demandEnergy = 0
        self.demandTime = 0
        self.openWindowState = 0
        self.lazyReduction = 0

        #self.reserveBuffer = None
        self.adjusted_charged_buffer = None
        self.charged_reserve_buffer = None

    def setInfo(self,value):
        self.info = value

    def getInfo(self):
        return self.info

    def setForcedInfo(self,value):
        self.forcedInfo = value

    def getForcedInfo(self):
        return self.forcedInfo

    def setDebugInfo(self,value):
        self.debugInfo = value

    def getDebugInfo(self):
        return self.debugInfo

    def setDemandEnergy(self,value):
        self.demandEnergy = value

    def getDemandEnergy(self):
        return self.demandEnergy

    def setDemandTime(self,value):
        self.demandTime = value

    def getDemandTime(self):
        return self.demandTime

    def setOpenWindowState(self,state):
        self.openWindowState = state

    def hasOpenWindow(self):
        return self.openWindowState > 0

    def hasLongOpenWindow(self):
        return self.openWindowState > 1

    def setLazyReduction(self,value):
        self.lazyReduction = value

    def getLazyReduction(self):
        return self.lazyReduction

    def getOutdoorReduction(self):
        return self.outdoorReduction

    def getNightReduction(self):
        return self.nightReduction

    def getForcedReduction(self):
        return self.forcedReduction

    def setAdjustedChargedBuffer(self, value):
        self.adjusted_charged_buffer = value

    def getAdjustedChargedBuffer(self):
        return self.adjusted_charged_buffer

    def setChargedReserveBuffer(self, value):
        self.charged_reserve_buffer = value

    def getChargedReserveBuffer(self):
        return self.charged_reserve_buffer
