#from dataclasses import dataclass#, asdict
import json

from datetime import datetime

class HouseEnergySlotData:
    pass

class RoomEnergySlotData:
    pass

#@dataclass
class RoomState:
    def __init__(self, current_temperature = None, current_temperature_changed = None):
        self.current_temperature = current_temperature
        self.current_temperature_changed = current_temperature_changed

        self.last_temperature = None
        self.last_temperature_changed = None

        self.buffer_ground = None
        self.buffer_volume = None
        self.buffer_outer_wall = None
        self.buffer_inner_wall = None

        self.target_temperature = None
        self.heating_target_temperature = None
        self.heating_circuit_state = None
        self.heating_demand_last_changed = None

        self.active_heating_volume = None
        self.active_heating_radiation = None

        self.passive_energy_slots = {}

    def refresh(self, now, current_temperature, target_temperature, heating_target_temperature, heating_circuit_state, heating_demand_last_changed):
        if current_temperature != self.current_temperature:
            self.last_temperature = self.current_temperature
            self.last_temperature_changed = self.current_temperature_changed
            self.current_temperature = current_temperature
            self.current_temperature_changed = now
            return True

        self.target_temperature = current_temperature
        self.heating_target_temperature = heating_target_temperature
        self.heating_circuit_state = heating_circuit_state
        self.heating_demand_last_changed = heating_demand_last_changed
        return False

    def setActiveEnergyData(self, active_heating_volume, active_heating_radiation):
        self.active_heating_volume = active_heating_volume
        self.active_heating_radiation = active_heating_radiation

    def setEnergySlotData(self, slot,
                                  possible_heating_volume, possible_heating_radiation,
                                  indoor_wall_energy, ground_energy, outdoor_wall_energy, outdoor_wall_radiation,
                                  window_energy, window_radiation,
                                  ventilation_energy,
                                  leak_energy):
        data = RoomEnergySlotData()
        data.possible_heating_volume = possible_heating_volume
        data.possible_heating_radiation = possible_heating_radiation
        data.indoor_wall_energy = indoor_wall_energy
        data.ground_energy = ground_energy
        data.outdoor_wall_energy = outdoor_wall_energy
        data.outdoor_wall_radiation = outdoor_wall_radiation
        data.window_energy = window_energy
        data.window_radiation = window_radiation
        data.ventilation_energy = ventilation_energy
        data.leak_energy = leak_energy
        self.passive_energy_slots[slot] = data

#@dataclass
class HouseState:
    def __init__(self, room_states):
        self.last_runtime = None
        self.room_states = room_states

        self.active_heating_volume = None
        self.active_heating_radiation = None
        self.active_heating_circulation_debug_info = None

        self.passive_energy_slots = {}

    def getRoomStates(self):
        return self.room_states

    def getRoomState(self, room_id):
        return self.room_states[room_id]

    def getPassiveEnergySlot(self, slot):
        return self.passive_energy_slots[slot]

    def setActiveEnergyData(self, active_heating_volume, active_heating_radiation, active_heating_circulation_debug_info ):
        self.active_heating_volume = active_heating_volume
        self.active_heating_radiation = active_heating_radiation
        self.active_heating_circulation_debug_info = active_heating_circulation_debug_info

    def setEnergySlotData(self, slot, possible_heating_volume, possible_heating_radiation, outdoor_temperature, cloud_cover, sun_east_radiation, sun_south_radiation, sun_west_radiation, sun_radiation, sun_debug_info):
        data = HouseEnergySlotData()
        data.possible_heating_volume = possible_heating_volume
        data.possible_heating_radiation = possible_heating_radiation
        data.outdoor_temperature = outdoor_temperature
        data.cloud_cover = cloud_cover
        data.sun_east_radiation = sun_east_radiation
        data.sun_south_radiation = sun_south_radiation
        data.sun_west_radiation = sun_west_radiation
        data.sun_radiation = sun_radiation,
        data.sun_debug_info = sun_debug_info
        self.passive_energy_slots[slot] = data

    @staticmethod
    def custom_encoder(o):
        if isinstance(o, datetime):
          return o.isoformat()
        #d = o.__dict__.copy()
        d = {'__type__': o.__class__.__name__}
        if o.__class__.__name__ == "HouseState":
            d['last_runtime'] = o.last_runtime
            d['room_states'] = o.room_states
        elif o.__class__.__name__ == "RoomState":
            d['current_temperature'] = o.current_temperature
            d['current_temperature_changed'] = o.current_temperature_changed
            d['last_temperature'] = o.current_temperature
            d['last_temperature_changed'] = o.current_temperature_changed
            d['buffer_ground'] = o.buffer_ground
            d['buffer_volume'] = o.buffer_volume
            d['buffer_outer_wall'] = o.buffer_outer_wall
            d['buffer_inner_wall'] = o.buffer_inner_wall
        return d

    @staticmethod
    def dump(house_state):
        data = json.dumps(house_state, default=HouseState.custom_encoder, indent=4)
        #print(data)
        return data

    @staticmethod
    def custom_decoder(dct):
        if '__type__' in dct:
            class_name = dct.pop('__type__')
            if class_name == "HouseState":
                obj = HouseState({})
            elif class_name == "RoomState":
                obj = RoomState()
            for key, value in dct.items():
              if key in ["last_runtime", "current_temperature_changed", "last_temperature_changed", "heating_demand_last_changed"]:
                dct[key] = datetime.fromisoformat(value)
            obj.__dict__.update(dct)
            return obj
        return dct

    @staticmethod
    def load(json_data):
        return json.loads(json_data, object_hook=HouseState.custom_decoder)
