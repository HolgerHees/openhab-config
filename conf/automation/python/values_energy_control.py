import math
import json
import threading

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper
from custom.charging import ChargingHelper

from configuration import customConfigs

import scope
from scope import cache

#KWKG-Umlage: 0,446 ct/kWh
#Offshore-Netzumlage: 0,941 ct/kWh
#Aufschlag für besondere Netznutzung (AbN): 1,559 ct/kWh
ENERGY_TRAFFIC_COST_PER_KWH = 0.12 + 0.00446 + 0.00941 + 0.01559
VAT_COST = 1.19 # %

STORAGE_MAX_CAPACITY = 50.4
STORAGE_EMERGENCY_ENERGY_SOC = STORAGE_MAX_CAPACITY * 0.2

STORAGE_MAX_CHARGING_POWER = STORAGE_MAX_CAPACITY * 0.2 # 10.000W AC => DC, 14.973W DC => DC, 11.274W DC => AC
STORAGE_MIN_CHARGING_POWER = 1.0
STORAGE_PERCENT_TO_CHARING_POWER_MAP = {
    95: STORAGE_MAX_CHARGING_POWER * 1.0,
    96: STORAGE_MAX_CHARGING_POWER * 0.8,
    97: STORAGE_MAX_CHARGING_POWER * 0.6,
    98: STORAGE_MAX_CHARGING_POWER * 0.4,
    99: STORAGE_MAX_CHARGING_POWER * 0.2,
    100: STORAGE_MAX_CHARGING_POWER * 0.08
}
STORAGE_MAX_CHARGING_UNTIL_PERCENT = list(STORAGE_PERCENT_TO_CHARING_POWER_MAP.keys())[0]

STORAGE_MAX_GRID_FEED = 14.0

MAX_CONSUMPTION_PER_DAY = 25.0
BASE_NIGHT_CONSUMPTION_PER_HOUR = 0.5
BASE_DAY_CONSUMPTION_PER_HOUR = 1.0

CAR_MAX_CAPACITY = 50.0
CAR_MAX_CHARGING_POWER = 10.0
CAR_MIN_CHARGING_POWER = 1.0

# 13.16°C => 2,0m² (26.09.2025)
# -4.54°C => 9,5m² (17.02.2025)

# DIFF: 17.7 => 7.5
# DIFF: 1 => 0.423728813559

#  17.88°C =>  0.00m²   |   0.00 =>  0.00
# -20.00°C => 16.05m²   | -37.88 => 16.05

HEATING_MAX_TEMPERATURE = 17.88
HEATING_MIN_TEMPERATURE = -20.0
HEATING_MAX_TEMPERATURE_DIFF = HEATING_MIN_TEMPERATURE - HEATING_MAX_TEMPERATURE
HEATING_MAX_ENERGY = ( 16.05 * 11.0 ) / 4.0

#HOUSE_HEATING_MAP = {
#    -6.0: 10.0,
#    -4.0:  6.0,
#}

FROST_GUARD_HEATING_MAP = {
   -9.0: 13.0,
   -8.0: 11.5,
   -7.0: 10.0,
   -6.0:  8.5,
   -5.0:  7.3,
   -4.0:  6.0,
   -3.0:  5.0,
   -2.0:  4.0,
   -1.0:  3.0,
    0.0:  2.5,
    1.0:  2.0,
    2.0:  1.5,
    3.0:  1.1,
    4.0:  0.5,
    5.0:  0.0
}

REST_API_NULL_VALUE = 999999999

#value = cache.sharedCache.get('test')
#print(value)
#cache.sharedCache.put('test', 2)

@rule(
    triggers = [
#        GenericCronTrigger("*/5 * * * * ?"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_EnergySoc")
    ]
#    , profile_code=True
)
class StorageInfo:
    def __init__(self):
        state = json.loads(Registry.getItemState("pGF_Utilityroom_Electricity_Cached_Inverter_Energy_State").toString())
        #state = cache.sharedCache.get("Inverter_Energy_State")
        if not state:
            self.demand, self.supply, self.production, self.consumption, self.soc, self.last_change = self.dumpState()
        else:
            self.demand = state["demand"]
            self.supply = state["supply"]
            self.production = state["production"]
            self.consumption = state["consumption"]
            self.soc = state["soc"]
            self.last_change = datetime.fromisoformat(state["last_change"])

    def dumpState(self):
        demand = self.getEnergyValue("pGF_Garage_Solar_Inverter_DemandTotalEnergy")
        supply = self.getEnergyValue("pGF_Garage_Solar_Inverter_SupplyTotalEnergy")
        production = self.getEnergyValue("pGF_Garage_Solar_Inverter_ProductionTotalEnergy")
        consumption = self.getEnergyValue("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy")

        soc = self.getEnergyValue("pGF_Garage_Solar_Storage_EnergySoc")
        last_change = Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").getLastStateChange()

        state = { "demand": demand, "supply": supply, "production": production, "consumption": consumption, "soc": soc, "last_change": last_change.isoformat() }
        #cache.sharedCache.put("Inverter_Energy_State", state)
        Registry.getItem("pGF_Utilityroom_Electricity_Cached_Inverter_Energy_State").postUpdate(json.dumps(state))

        return [demand, supply, production, consumption, soc, last_change]

    def getEnergyDiff(self):
        demand, supply, production, consumption, soc, last_change = self.dumpState()

        demand_diff = demand - self.demand
        supply_diff = supply - self.supply
        production_diff = production - self.production
        consumption_diff = consumption - self.consumption

        storage_diff = soc - self.soc

        self.logger.info("CHANGED demand from {} to {}, diff {}".format(self.demand, demand, demand_diff))
        self.logger.info("CHANGED supply from {} to {}, diff {}".format(self.supply, supply, supply_diff))
        self.logger.info("CHANGED production from {} to {}, diff {}".format(self.production, production, production_diff))
        self.logger.info("CHANGED consumption from {} to {}, diff {}".format(self.consumption, consumption, consumption_diff))
        self.logger.info("LAST_CHANGE: {}".format(self.last_change))

        self.demand = demand
        self.supply = supply
        self.production = production
        self.consumption = consumption
        self.soc = soc

        previous_change = self.last_change
        self.last_change = last_change

        return [demand_diff, supply_diff, production_diff, consumption_diff, storage_diff, previous_change]

    def getEnergyValue(self, item_name):
        return Registry.getItem(item_name).getState().doubleValue()

    def calculate(self, current_battery_energy_soc):
        current_battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        current_solar_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        current_grid_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()

        demand_diff, supply_diff, production_diff, consumption_diff, storage_diff, previous_change  = self.getEnergyDiff()

        # *** STEP 1: calculate solar charge ***
        total_charge = (production_diff + demand_diff) - ( supply_diff + consumption_diff )
        if storage_diff > 0:
            if demand_diff < consumption_diff:
                self.logger.info("SOLAR ONLY CHARGE • DIFF: {} ({})".format(storage_diff, total_charge))
                new_solar_energy_soc = current_battery_energy_soc - current_grid_energy_soc
            elif production_diff < 0.01: # smaller then 10 Watt
                self.logger.info("GRID ONLY CHARGE • DIFF: {} ({})".format(storage_diff, total_charge))
                new_solar_energy_soc = current_solar_energy_soc
            else:
                solar_charge = production_diff if production_diff < storage_diff else storage_diff
                self.logger.info("MIXED SOLAR CHARGE • DIFF: {} ({}) • SOLAR: {}".format(storage_diff, total_charge, solar_charge))
                #new_solar_energy_soc = current_solar_energy_soc + ( solar_charge * 0.97 ) # 3% loss
                new_solar_energy_soc = current_solar_energy_soc + solar_charge
                if new_solar_energy_soc > STORAGE_MAX_CAPACITY:
                    new_solar_energy_soc = STORAGE_MAX_CAPACITY
        else:
            self.logger.info("DISCHARGE • DIFF: {} ({})".format(storage_diff, total_charge))
            new_solar_energy_soc = current_solar_energy_soc + storage_diff

        if new_solar_energy_soc < 0:
            self.logger.info("PATCH_SOC: solar_energy_soc: from {} to 0".format(new_solar_energy_soc))
            new_solar_energy_soc = 0
        elif new_solar_energy_soc > 0 and current_battery_energy_soc - new_solar_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC:
            if current_battery_energy_soc > STORAGE_EMERGENCY_ENERGY_SOC:
                _new_solar_energy_soc = new_solar_energy_soc
                new_solar_energy_soc = current_battery_energy_soc - STORAGE_EMERGENCY_ENERGY_SOC
                self.logger.info("PATCH_SOC: solar_energy_soc: from {} to {}".format(_new_solar_energy_soc, new_solar_energy_soc))
            else:
                self.logger.info("PATCH_SOC: solar_energy_soc: from {} to 0".format(new_solar_energy_soc))
                new_solar_energy_soc = 0

        # *** STEP 2: rest is grid charge ***
        new_grid_energy_soc = current_battery_energy_soc - new_solar_energy_soc
        self.logger.info("NEW_SOC: total_energy_soc: {}, solar_energy_soc: {}, grid_energy_soc: {}".format(current_battery_energy_soc, new_solar_energy_soc, new_grid_energy_soc))

        # *** STEP 3: grid charge is never smaller then emergency energy level ***
        #if new_grid_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC:
        #    new_grid_energy_soc = STORAGE_EMERGENCY_ENERGY_SOC if current_battery_energy_soc >=STORAGE_EMERGENCY_ENERGY_SOC else current_battery_energy_soc
        #    new_solar_energy_soc = current_battery_energy_soc - new_grid_energy_soc
        #    self.logger.info("ADJUSTED: new_solar_energy_soc: {}, new_grid_energy_soc: {}".format(new_solar_energy_soc, new_grid_energy_soc))

        # *** STEP 4: Update values and calculate new grid price
        if current_solar_energy_soc != new_solar_energy_soc:
            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").postUpdate(new_solar_energy_soc)

        if current_grid_energy_soc != new_grid_energy_soc:
            # calculate new grid price
            if new_grid_energy_soc > current_grid_energy_soc:
                grid_charge = new_grid_energy_soc - current_grid_energy_soc
                ratio = grid_charge  / new_grid_energy_soc
                current_stock_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").averageSince(previous_change).doubleValue()
                self.logger.info("STOCK PRICE: JDBC: {} DIRECT: {}".format(current_stock_price, Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getState().doubleValue()))

                new_battery_price = ( current_battery_price * (1 - ratio) ) + ( current_stock_price * ratio )
                if current_battery_price != new_battery_price:
                    Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").postUpdate(new_battery_price)

            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").postUpdate(new_grid_energy_soc)

    def execute(self, module, input):
        self.calculate(input['event'].getItemState().doubleValue())

#Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").postUpdate(STORAGE_EMERGENCY_ENERGY_SOC)
#Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").postUpdate(Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").doubleValue() - Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue())
#Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").postUpdate(0.08)

@rule(
    triggers = [
       GenericCronTrigger("*/30 * * * * ?") # 30 seconds, because of 60 seconds watchdoc for fenecon
#       GenericCronTrigger("*/15 * * * * ?")
    ]
#    , profile_code=True
)
class StoragePower:
    def __init__(self):
        self.next_solar_calculation = datetime.now().astimezone()
        self.today_solar_forceast = None
        self.tomorrow_solar_forceast = None

        self.next_heating_calculation = datetime.now().astimezone()
        self.house_heating_forecast = None
        self.frost_guard_heating_forecast = None

        self.charging_helper = ChargingHelper(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc"))

    def initSolarForecast(self, now, start, end):
        if now < self.next_solar_calculation:
            return

        temperature_past = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").maximumBetween(now - timedelta(hours=24), now).getState().doubleValue()
        temperature_future = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").maximumBetween(now, now+timedelta(hours=24)).getState().doubleValue()

        east = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_East_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()
        south = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_South_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()
        west = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_West_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()

        # TODO camera based snow detection
        if temperature_past < 0 and temperature_future < 0 and east < 2.0 and south < 1.2 and west < 1.6:
            # SNOW active
            self.today_solar_forceast = self.tomorrow_solar_forceast = None
        else:
            self.today_solar_forceast = {}
            self.tomorrow_solar_forceast = {}

            end = end - timedelta(microseconds=1) # needed to exclude ending slot from the upcomming day

            dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").getAllStatesBetween(start, end)
            for dumped_state in dumped_states:
                timestamp = dumped_state.getTimestamp()
                value = dumped_state.getState().doubleValue()
                if value == 0:
                    continue

                active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                if timestamp.timestamp() not in active_solar_forceast_variable:
                    active_solar_forceast_variable[timestamp.timestamp()] = [timestamp, 0]
                active_solar_forceast_variable[timestamp.timestamp()][1] += value

            dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_South").getPersistence("jdbc").getAllStatesBetween(start, end)
            for dumped_state in dumped_states:
                timestamp = dumped_state.getTimestamp()
                value = dumped_state.getState().doubleValue()
                if value == 0:
                    continue

                active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                if timestamp.timestamp() not in active_solar_forceast_variable:
                    active_solar_forceast_variable[timestamp.timestamp()] = [timestamp, 0]
                active_solar_forceast_variable[timestamp.timestamp()][1] += value

            dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").getAllStatesBetween(start, end)
            for dumped_state in dumped_states:
                timestamp = dumped_state.getTimestamp()
                value = dumped_state.getState().doubleValue()
                if value == 0:
                    continue

                active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                if timestamp.timestamp() not in active_solar_forceast_variable:
                    active_solar_forceast_variable[timestamp.timestamp()] = [timestamp, 0]
                active_solar_forceast_variable[timestamp.timestamp()][1] += value

        # weather data are fetched every hour at 5 past
        # expected solar is processed every hour at 6 past
        # this is why we recalculate forcecast every hour at 7 past
        self.next_solar_calculation = (now + timedelta(hours=1)).replace(minute=7,second=0, microsecond=0)

    def initHeatingForecast(self, now, start, end):
        if now < self.next_heating_calculation:
            return

        #print("initHeatingForecast")
        avg_value = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").averageBetween(start,end).doubleValue()

        if avg_value > HEATING_MAX_TEMPERATURE:
            house_heating = 0
        elif avg_value < HEATING_MIN_TEMPERATURE:
            house_heating = HEATING_MAX_ENERGY
        else:
            house_heating = ( avg_value - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF

        frost_guard_heating = ChargingHelper.findValueFromMap(avg_value, FROST_GUARD_HEATING_MAP)

        self.house_heating_forecast = house_heating
        self.frost_guard_heating_forecast = frost_guard_heating

        self.next_heating_calculation = (now + timedelta(hours=1)).replace(minute=0,second=0, microsecond=0)

    def isDischargingAllowed(self, now, current_battery_soc, current_price, battery_price):
        is_discharging_allowed = True
        if self.charging_helper.isGridMode():
            if current_battery_soc > STORAGE_EMERGENCY_ENERGY_SOC:
                # nicht entladen, wenn aktueller Strompreis gleich dem max Ladestrompreis ist.
                if Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue() <= 0:
                    if current_price <= battery_price:
                        is_discharging_allowed = False
                        discharging_msg = " • Discharging refused (grid cheaper)"
                    else:
                        discharging_msg = " • Discharging allowed (storage cheaper)"
                else:
                    discharging_msg = " • Discharging allowed (free energy)"
            else:
                # is_discharging_allowed = False => Not needed. Is handled by FEMS emergency limit
                discharging_msg = " • Discharging refused (FEMS) (no energy)"
        else:
            discharging_msg = " • Discharging allowed (FEMS) (emergency mode)"

        return [is_discharging_allowed, discharging_msg]

    def calculateStorageMaxChargePower(self, now, current_battery_soc):
        requested_max_power = None
        if self.today_solar_forceast is None:
            max_power_msg = " • Charging not possible (missing forecast)"
        else:
            _charge_power_missing = STORAGE_MAX_CAPACITY - current_battery_soc
            if current_battery_soc < STORAGE_MAX_CAPACITY / 2:
                max_power_msg = " • Charging not limited (battery low)"
            elif _charge_power_missing < STORAGE_MAX_CAPACITY / 50:
                max_power_msg = " • Charging not limited (battery full)"
            else:
                # *** COLLECT UPCOMMING SLOTS until production limit is reached ***
                _solar_production_total = sum([value for _, value in self.today_solar_forceast.values()])
                _solar_production_limit = _solar_production_total * 0.85 # calculate reduction only during thew first 70% oft the solar time and keep 30% as reserve
                _solar_power_used = 0
                _ref_now = now.replace(minute=math.floor(now.minute / 15) * 15, second=0, microsecond=0)
                solar_slots_used = []
                for timestamp, value in self.today_solar_forceast.values():
                    if timestamp.timestamp() >= _ref_now.timestamp(): # cmp by timestamp for performance reason
                        solar_slots_used.append({"timestamp": timestamp, "value": value, "limit": None})

                    _solar_power_used += value
                    if _solar_power_used >= _solar_production_limit:
                        break

                if len(solar_slots_used) <= 0:
                    max_power_msg = " • Charging not limited (end time reached)"
                else:
                    _remaining_production_total = sum([slot["value"] for slot in solar_slots_used])
                    if _remaining_production_total < _charge_power_missing:  # more then 2% missing
                        max_power_msg = " • Charging not limited (not enough solar)"
                    else:
                        _solar_power_max = max([slot["value"] for slot in solar_slots_used])

                        # *** COLLECT SLOTS with hightes min power, but still enough for a full charge
                        # with each iteration, we increase min power and check if it is still enough
                        # HINT => this loop just excludes early low power productions => It does not limit the power
                        _charging_min_limit = min(_solar_power_max * 0.66, STORAGE_MAX_CHARGING_POWER * 0.66)
                        _charging_min_power = 0
                        _solar_slots_used = []
                        while _charging_min_power < _solar_power_max:
                            _charging_total = 0
                            __solar_slots_used = []
                            for slot in solar_slots_used:
                                if slot["value"] >= _charging_min_power or len(__solar_slots_used) > 0:
                                    __solar_slots_used.append(slot)
                                    _charging_total += slot["value"]

                            # 1. _charging_total not enough means min power is too high, keep the previous one
                            # 2. _charging_min_power is higher then min limit
                            if _charging_total < _charge_power_missing or _charging_min_power > _charging_min_limit:
                                break

                            _solar_slots_used = __solar_slots_used
                            _charging_min_power += 0.1 / 4 # increase 0.1 per hour => 0.025 per 15 min
                        solar_slots_used = _solar_slots_used

                        # *** COLLECT SLOTS
                        # with each iteration, we decrease power factor and check if it is still enough
                        # HINT => this loop simulates active power limitation
                        _solar_min_limit = STORAGE_MIN_CHARGING_POWER / 4
                        _solar_min_power = min([slot["value"] for slot in solar_slots_used])
                        _charging_power_factor = 1
                        _solar_slots_used = []
                        while _charging_power_factor > 0:
                            _charging_total = 0
                            __solar_slots_used = []
                            for slot in solar_slots_used:
                                _value = _solar_min_power * _charging_power_factor + (slot["value"] - _solar_min_power) # * _charging_power_factor ** _charging_power_factor
                                slot["limit"] = max(_value, _solar_min_limit)

                                __solar_slots_used.append(slot)
                                _charging_total += _value

                            # _charging_total not enough means max power is too low, keep the previous one
                            if _charging_total < _charge_power_missing:
                                break

                            _solar_slots_used = __solar_slots_used
                            _charging_power_factor -= 0.05
                        solar_slots_used = _solar_slots_used

                        #for slot in solar_slots_used:
                        #    print("TIME: {}, FROM {:.2f}, CHARGE {:.2f}, GRID {:.2f}".format(slot["timestamp"].strftime('%H:%M'), slot["value"], slot["limit"], slot["value"] - slot["limit"]))

                        if now < solar_slots_used[0]["timestamp"]:
                            requested_max_power = 0
                            max_power_msg = " • Charging delayed until {}".format(solar_slots_used[0]["timestamp"].strftime('%H:%M'))
                        else:
                            requested_max_power = solar_slots_used[0]["limit"] * 4
                            max_power_msg = " • Charging limited to {:.2f}kWh until {}".format(requested_max_power, solar_slots_used[-1]["timestamp"].strftime('%H:%M'))

        return [requested_max_power, max_power_msg]

    def _getStorageChargingPower(self, battery_soc):
        battery_percent = int(round(battery_soc * 100 / STORAGE_MAX_CAPACITY, 0))
        if battery_percent > 100:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[100]

        if battery_percent <= STORAGE_MAX_CHARGING_UNTIL_PERCENT:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[STORAGE_MAX_CHARGING_UNTIL_PERCENT]


        return STORAGE_PERCENT_TO_CHARING_POWER_MAP[battery_percent]

    def calculateStorageChargeLevel(self, now, charging_start, charging_end, consumption_start, consumption_end):
        current_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(now).getState().doubleValue()
        battery_price = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Price").doubleValue()

        solar_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue()
        grid_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue()
        current_battery_soc = Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").doubleValue()
        current_battery_percent = Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").intValue()

        today_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Consumption").doubleValue()
        today_production = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Production").doubleValue()

        # *** CALCULATE AND CACHE SOLAR AND HEATING
        expected_total_demand = MAX_CONSUMPTION_PER_DAY + self.house_heating_forecast + self.frost_guard_heating_forecast
        soc_relevant_demand = expected_total_demand - (today_consumption if now >= consumption_start else 0.0)

        _used_solar_forcecast = self.today_solar_forceast if now >= consumption_start else self.tomorrow_solar_forceast
        if _used_solar_forcecast is not None:
            _used_solar_forcecast = self.today_solar_forceast if now >= consumption_start else self.tomorrow_solar_forceast
            _expected_solar_production = 0
            _used_solar_production = 0
            for timestamp, value in _used_solar_forcecast.values():
                _expected_solar_production += value
                _used_solar_production += BASE_DAY_CONSUMPTION_PER_HOUR / 4 if value > BASE_DAY_CONSUMPTION_PER_HOUR / 4 else value

            _today_remaining_solar_production = sum(value for timestamp, value in self.today_solar_forceast.values() if timestamp >= now)
            _today_total_forecasted_solar_production = sum(value for timestamp, value in self.today_solar_forceast.values())

            soc_relevant_demand -= _used_solar_production
            soc_relevant_solar_production = _expected_solar_production - _used_solar_production if _expected_solar_production > _used_solar_production else 0.0

            solar_forecast_msg = "{:.2f}kWh (consumption {:.2f}kWh, soc {:.2f}kWh)".format(_expected_solar_production, _used_solar_production, soc_relevant_solar_production)
            solar_current_msg = "{:.2f}kWh • Expected {:.2f}kWh • Forecast {:.2f}kWh".format(today_production, _today_remaining_solar_production + today_production, _today_total_forecasted_solar_production)
        else:
            soc_relevant_solar_production = 0.0

            solar_forecast_msg = "not working"
            solar_current_msg = "{:.2f}kWh".format(today_production)

        # too much
        if STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_demand + soc_relevant_solar_production > STORAGE_MAX_CAPACITY:
            target_battery_soc = STORAGE_MAX_CAPACITY - soc_relevant_solar_production
            battery_target_msg = "max capacity - soc relevant solar"

        else:
            target_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_demand
            battery_target_msg = "emergency + total demand - solar consumption" if _used_solar_forcecast is not None else "emergency + total demand"

        _night_in_hours = math.floor((charging_end - consumption_start).total_seconds() / 60.0 / 60.0)
        expected_consumption_during_night = _night_in_hours * BASE_NIGHT_CONSUMPTION_PER_HOUR
        if target_battery_soc < STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night:
            target_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night
            battery_target_msg = "emergency + night consumption"

        target_battery_percent = target_battery_soc * 100 / STORAGE_MAX_CAPACITY

        self.logger.info("Forecast: 🏠 Base {:.2f}kWh 🔥 Heating {:.2f}kWh 🌳 Plants {:.2f}kWh 🌞 Solar {}".format(MAX_CONSUMPTION_PER_DAY, self.house_heating_forecast, self.frost_guard_heating_forecast, solar_forecast_msg))
        self.logger.info("        : 🏠 Total demand {:.2f}kWh 🔋 Battery target {:.2f}kWh ({:.0f}%) ({})".format(expected_total_demand, target_battery_soc, target_battery_percent, battery_target_msg))
        self.logger.info("        : --")

        self.logger.info("Current : 🔋 Battery {:.2f}kWh ({:.0f}%) • {:.2f}kWh ({:.2f}€/kWh) • {:.2f}kWh (0.00€/kWh)".format(current_battery_soc, current_battery_percent, grid_battery_soc, battery_price, solar_battery_soc))
        self.logger.info("        : 💰 Spot price {:.2f}€/kWh 🏠 Consumption {:.2f}kWh 🌞 Solar {}".format(current_price, today_consumption, solar_current_msg))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_charge_power, state_msg, charge_msg = self.charging_helper.calculateRequestedPower(
            start_time = charging_start,
            end_time = charging_end,
            current_time = now,
            current_energy_soc = current_battery_soc,
            target_energy_soc = target_battery_soc,
            min_charging_power = STORAGE_MIN_CHARGING_POWER,
            max_charging_power = STORAGE_MAX_CHARGING_POWER,
            charging_callback = self._getStorageChargingPower
        )

        requested_max_charge_power, max_charge_msg = self.calculateStorageMaxChargePower(now, current_battery_soc)

        # *** CALCULATE DISCHARING ALLOWED
        is_discharging_allowed, max_discharge_msg = self.isDischargingAllowed(now, current_battery_soc, current_price, battery_price)
        state_msg = "{}{}".format(state_msg, max_discharge_msg)

        # *** CALCULATE MAX CHARGING (limit solar charging during the day)
        requested_max_charge_power, max_charge_msg = self.calculateStorageMaxChargePower(now, current_battery_soc)
        state_msg = "{}{}".format(state_msg, max_charge_msg)

        if charge_msg is not None:
            self.logger.info("Charging: {}".format(charge_msg))
            self.logger.info("        : --")

        self.logger.info("{:<8}: ✨ {}".format("Active" if requested_charge_power is not None else "Inactive", state_msg))

        return [requested_charge_power, requested_max_charge_power, is_discharging_allowed]

    def calculateCarChargeLevel(self, now, charging_start, charging_end):
        current_battery_soc = Registry.getItemState("pGF_Outdoor_Car_EnergySoc").doubleValue()
        current_battery_percent = Registry.getItemState("pGF_Outdoor_Car_EssSoc").intValue()

        target_battery_soc = CAR_MAX_CAPACITY
        target_battery_percent = target_battery_soc * 100 / CAR_MAX_CAPACITY

        self.logger.info("Car     : 🔋 Current {:.2f}kWh ({:.0f}%) • Target {:.2f}kWh ({:.0f}%)".format(current_battery_soc, current_battery_percent, target_battery_soc, target_battery_percent))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_charge_power, state_msg, charge_msg = self.charging_helper.calculateRequestedPower(
            start_time = charging_start,
            end_time = charging_end,
            current_time = now,
            current_energy_soc = current_battery_soc,
            target_energy_soc = target_battery_soc,
            min_charging_power = CAR_MIN_CHARGING_POWER,
            max_charging_power = CAR_MAX_CHARGING_POWER,
            charging_callback = lambda battery_soc: CAR_MAX_CHARGING_POWER
        )

        if charge_msg is not None:
            self.logger.info("Charging: {}".format(charge_msg))
            self.logger.info("        : --")
        self.logger.info("{:<8}: ✨ {}".format("Active" if requested_charge_power > 0 else "Inactive", state_msg))

        return requested_charge_power

    def execute(self, module, input):
        self.logger.info("--------: >>>")

        # *** INIT DATES
        #now = datetime.now().astimezone().replace(hour=12, minute=15) #  - timedelta(days=1)
        #self.next_solar_calculation = now
        #self.next_heating_calculation = now
        now = datetime.now().astimezone()

        _sunrise = Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime().replace(day=now.day, month=now.month, year=now.year)
        _sunset = Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime().replace(day=now.day, month=now.month, year=now.year)

        # calculate for tomorrow
        if now > _sunrise:
            charging_start = _sunset                                                                                         # charging starts today sunset
            charging_end = _sunrise + timedelta(days=1)                                                                      # charging ends tomorrow sunrise
        # calculate for today
        else:
            charging_start = _sunset - timedelta(days=1)                                                                     # charging starts yesterday sunset
            charging_end = _sunrise                                                                                          # charging ends today sunrise

        # *** INIT
        self.charging_helper.refresh(now, Registry.getItemState("pGF_Garage_Solar_Inverter_GridEnabled").intValue() == 1)

        # *** BATTERY CHARGING
        if Registry.getItemState("pGF_Garage_Solar_Inverter_Charge_Control") == scope.ON:
            today_morning = now.replace(hour=0, minute=0, second=0, microsecond=0)

            consumption_start = charging_end.replace(hour=0, minute=0, second=0, microsecond=0)                             # consumptions starts on the day where charging ends
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions ends

            self.initSolarForecast(now, today_morning, today_morning + timedelta(days=2)) #consumption_end
            self.initHeatingForecast(now, consumption_start, consumption_end)

            # https://community.openems.io/t/wirkleistungsvorgabe-setactivepowerlessorequals/2811
            # SetActivePowerLessOrEquals => Write command for a minimum charge power (-) or maximum discharge power (+). Range e.g. [-5000 to 5000]
            # SetActivePowerGreaterOrEquals	=> Write command for a maximum charge power (-) or minimum discharge power (+)

            requested_charge_power, requested_max_charge_power, is_discharging_allowed = self.calculateStorageChargeLevel(now, charging_start, charging_end, consumption_start, consumption_end)
            Registry.getItem("pGF_Garage_Solar_Storage_Requested_Power").postUpdate(int(requested_charge_power * 1000) if requested_charge_power is not None else REST_API_NULL_VALUE)
            Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Power").postUpdate(int(requested_max_charge_power * 1000) if requested_max_charge_power is not None else REST_API_NULL_VALUE)
            Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Allowed").postUpdate(scope.ON if is_discharging_allowed else scope.OFF)

        # *** CAR CHARGING
        if Registry.getItemState("pGF_Outdoor_Car_Charge_Control") == scope.ON and Registry.getItemState("pGF_Outdoor_Car_IsConnected") == scope.ON:
            self.logger.info("--------: <<<")
            self.logger.info("--------: >>>")

            requested_power = self.calculateCarChargeLevel(now, charging_start, charging_end)

            if requested_power is not None:
                Registry.getItem("pGF_Outdoor_Car_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))

        self.logger.info("--------: <<<")

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ProductionActivePower"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ConsumptionActivePower"),
        GenericCronTrigger("*/30 * * * * ?")
    ]
#    , profile_code=True
)
class StorageControl:
    def __init__(self):
        self.last_active_power = Registry.getItemState("pGF_Garage_Solar_Storage_ActivePowerEqual").intValue()
        self.last_trigger = 0

        self.lock = threading.Lock()

    def execute(self, module, input):
        with self.lock:
            #active_power = Registry.getItemState("pGF_Garage_Solar_Storage_ActivePowerEqual").intValue()
            requested_power = Registry.getItemState("pGF_Garage_Solar_Storage_Requested_Power").intValue()
            requested_max_power = Registry.getItemState("pGF_Garage_Solar_Storage_Requested_Max_Power").intValue()
            is_discharging_allowed = Registry.getItemState("pGF_Garage_Solar_Storage_Discharged_Allowed") == scope.ON

            trigger_msg = None

            if requested_power == REST_API_NULL_VALUE and requested_max_power == REST_API_NULL_VALUE and is_discharging_allowed:
                if self.last_active_power != REST_API_NULL_VALUE:
                    last_active_power_msg = self.last_active_power if self.last_active_power != REST_API_NULL_VALUE else "off"

                    trigger_msg = "{} => off • Nothing requested".format(last_active_power_msg)
                    Registry.getItem("pGF_Garage_Solar_Storage_ActivePowerEqual").sendCommand(REST_API_NULL_VALUE)

                    self.last_active_power = REST_API_NULL_VALUE
            else:
                production_power = Registry.getItemState("pGF_Garage_Solar_Inverter_ProductionActivePower").intValue()
                consumption_power = Registry.getItemState("pGF_Garage_Solar_Inverter_ConsumptionActivePower").intValue()

                _active_power = REST_API_NULL_VALUE

                # Request Fixed Charging
                if requested_power != REST_API_NULL_VALUE:
                    _active_power = production_power - requested_power
                # Prevent discharging
                elif not is_discharging_allowed and consumption_power > production_power:
                    _active_power = production_power
                # Limit Charging
                elif requested_max_power != REST_API_NULL_VALUE and production_power - consumption_power > requested_max_power:
                    _active_power = production_power - requested_max_power

                now = datetime.now().astimezone().timestamp()

                # trigger on changes or latest after 20 seconds of inactivity. This can result in an interval of 49 seconds. (30 seconds + 19 seconds)
                if self.last_active_power != _active_power or (_active_power != REST_API_NULL_VALUE and now - self.last_trigger > 20):
                    last_active_power_msg = self.last_active_power if self.last_active_power != REST_API_NULL_VALUE else "off"
                    active_power_msg = _active_power if _active_power != REST_API_NULL_VALUE else "off"
                    requested_power_msg = requested_power if requested_power != REST_API_NULL_VALUE else "off"
                    requested_max_power_msg = requested_max_power if requested_max_power != REST_API_NULL_VALUE else "off"

                    trigger_msg = "{} => {} • Requested power: {} (max {}), Discharging allowed: {}, Production: {}, Consumption: {}".format(last_active_power_msg, active_power_msg, requested_power_msg, requested_max_power_msg, is_discharging_allowed, production_power, consumption_power)
                    Registry.getItem("pGF_Garage_Solar_Storage_ActivePowerEqual").sendCommand(_active_power)

                    self.last_active_power = _active_power
                    self.last_trigger = now

            if trigger_msg is not None:
                self.logger.info("--------: >>>")
                self.logger.info("Control : 🔋 Active Power: {}".format(trigger_msg))
                self.logger.info("--------: <<<")
