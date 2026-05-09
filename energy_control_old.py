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

SOLAR_SAFETY_TRESHOLD = 1.5 # special logic applies only if 150% of needed energy is available as solar

MAX_CONSUMPTION_PER_DAY = 25.0
BASE_DAY_CONSUMPTION_PER_HOUR = 1.0
BASE_NIGHT_CONSUMPTION_PER_HOUR = 0.5

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

ATTIC_LIGHT_ENERGY_PER_HOUR = 0.2

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

                new_battery_price = ( current_battery_price * (1.0 - ratio) ) + ( current_stock_price * ratio )
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
       GenericCronTrigger("0 * * * * ?")
#       GenericCronTrigger("*/15 * * * * ?")
    ]
#    , profile_code=True
)
class StoragePower:
    def __init__(self):
        self.next_cache_calculation = datetime.now().astimezone()
        self.last_consumtion_start = None

        self.today_solar_forceast = None
        self.tomorrow_solar_forceast = None

        self.avg_expected_temperature = None

        self.charging_helper = ChargingHelper(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc"))

    def initStorageCache(self, now, consumption_start, consumption_end):
        if self.last_consumtion_start != consumption_start:
            self.avg_expected_temperature = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").averageBetween(consumption_start, consumption_end).doubleValue()
            self.last_consumtion_start = consumption_start

        if now.day != self.next_cache_calculation.day or now >= self.next_cache_calculation:
            forecast_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            forecast_end = forecast_start + timedelta(days=2)

            temperature_past = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").maximumBetween(now - timedelta(hours=24), now).getState().doubleValue()
            temperature_future = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").maximumBetween(now, now+timedelta(hours=24)).getState().doubleValue()

            east = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_East_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()
            south = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_South_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()
            west = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_West_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()

            # TODO camera based snow detection
            if temperature_past < 0 and temperature_future < 0 and east < 2.0 and south < 1.2 and west < 1.6:
                # SNOW active
                self.today_solar_forceast = self.tomorrow_solar_forceast = None
            else:
                self.today_solar_forceast = {}
                self.tomorrow_solar_forceast = {}

                forecast_end = forecast_end - timedelta(microseconds=1) # needed to exclude ending slot from the upcomming day

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                    if timestamp.timestamp() not in active_solar_forceast_variable:
                        active_solar_forceast_variable[timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}
                    active_solar_forceast_variable[timestamp.timestamp()]["total"] += value

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_South").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                    if timestamp.timestamp() not in active_solar_forceast_variable:
                        active_solar_forceast_variable[timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}
                    active_solar_forceast_variable[timestamp.timestamp()]["total"] += value

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    active_solar_forceast_variable = self.today_solar_forceast if timestamp.day == now.day else self.tomorrow_solar_forceast
                    if timestamp.timestamp() not in active_solar_forceast_variable:
                        active_solar_forceast_variable[timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}
                    active_solar_forceast_variable[timestamp.timestamp()]["total"] += value

            for slot in self.today_solar_forceast.values():
                slot["chargeable"] = max(slot["total"] - BASE_DAY_CONSUMPTION_PER_HOUR / 4, 0)
                slot["consumed"] = min(BASE_DAY_CONSUMPTION_PER_HOUR / 4, slot["total"])

            for slot in self.tomorrow_solar_forceast.values():
                slot["chargeable"] = max(slot["total"] - BASE_DAY_CONSUMPTION_PER_HOUR / 4, 0)
                slot["consumed"] = min(BASE_DAY_CONSUMPTION_PER_HOUR / 4, slot["total"])

            # weather data are fetched every hour at 5 past
            # expected solar is processed every hour at 6 past
            # this is why we recalculate forcecast every hour at 7 past
            self.next_cache_calculation = (now + timedelta(hours=1)).replace(minute=7,second=0, microsecond=0)

    def getExpectedTotalDemand(self):
        # House and water heating
        if self.avg_expected_temperature > HEATING_MAX_TEMPERATURE:
            house_heating = 0
        elif self.avg_expected_temperature < HEATING_MIN_TEMPERATURE:
            house_heating = HEATING_MAX_ENERGY
        else:
            house_heating = ( self.avg_expected_temperature - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF

        # Garage plants heating
        plant_energy = ChargingHelper.findValueFromMap(self.avg_expected_temperature, FROST_GUARD_HEATING_MAP)

        # Attic plants light
        state = Registry.getItemState("pOther_Manual_State_Auto_Attic_Light").intValue()
        if state > 0:
            plant_energy += (18 if state == 1 else 12) * ATTIC_LIGHT_ENERGY_PER_HOUR

        msg = "🏠 Base {:.2f}kWh 🔥 Heating {:.2f}kWh 🌳 Plants {:.2f}kWh".format(MAX_CONSUMPTION_PER_DAY, house_heating, plant_energy)

        return MAX_CONSUMPTION_PER_DAY + house_heating + plant_energy, house_heating + plant_energy, msg

    def isDischargingAllowed(self, now, current_battery_soc, stock_price, battery_price, expected_total_demand, sunset):
        if not self.charging_helper.isGridMode():
            return [True, "no grid"]
        elif current_battery_soc <= STORAGE_EMERGENCY_ENERGY_SOC:
            # battery level is less then 50% of emergency limit
            if current_battery_soc < STORAGE_EMERGENCY_ENERGY_SOC / 2.0:
                return [False, "no energy"]
            # sunshine is over in the evening (next day it is before sunset)
            elif now > sunset:
                return [False, "low energy and no sunshine soon"]
            else:
                _solar_total = sum([slot["total"] for slot in self.today_solar_forceast.values()])
                if _solar_total < (expected_total_demand + (STORAGE_EMERGENCY_ENERGY_SOC - current_battery_soc)) * SOLAR_SAFETY_TRESHOLD: # only if not enough expected solar
                    return [False, "low energy and not enough solar expected"] # is_discharging_allowed = False => Not needed. Is handled by FEMS emergency limit

        if Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue() > 0:
            return [True, "free energy"]
        elif stock_price > battery_price:
            return [True, "storage cheaper"]
        else:
            return [False, "grid cheaper"]

    def calculateStorageMaxSolarChargePower(self, now, current_battery_soc, tomorrow_total_demand, sunrise, sunset):
        requested_max_power = None
        if not self.charging_helper.isGridMode():
            max_power_msg = "no grid"
        elif self.today_solar_forceast is None:
            max_power_msg = "missing forecast"
        elif now < sunrise or now > sunset:
            max_power_msg = "wrong time"
        else:
            tomorrow_total_solar_production = sum(slot["total"] for slot in self.tomorrow_solar_forceast.values())

            # charge until full, ones per week
            maximumSinceOneWeek = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getPersistence("jdbc").maximumSince(now - timedelta(days=7)).getState().intValue()
            if maximumSinceOneWeek != 100 or tomorrow_total_solar_production < tomorrow_total_demand * SOLAR_SAFETY_TRESHOLD: # for min battery level, tomorrow must be 50% more then needed (safty net)
                min_level = 1.0
            else:
                tomorrow_used_solar_production = sum(slot["consumed"] for slot in self.tomorrow_solar_forceast.values())
                min_soc = STORAGE_EMERGENCY_ENERGY_SOC + tomorrow_total_demand - tomorrow_used_solar_production # today evening consumtion is included in (tomorrow_total_demand), because tomorrow evening consumption does not matter here
                min_level = 1.0 if min_soc > STORAGE_MAX_CAPACITY else min(round(min_soc / STORAGE_MAX_CAPACITY, 2), 1.0)

            target_soc = round(STORAGE_MAX_CAPACITY * min_level, 1)
            target_percent = int(min_level * 100)

            if current_battery_soc < target_soc * 0.5:
                max_power_msg = "battery low"
            elif current_battery_soc > STORAGE_MAX_CAPACITY * 0.95:
                max_power_msg = "battery full"
            elif current_battery_soc >= target_soc:
                requested_max_power = 0
                max_power_msg = "battery health"
            else:
                _charge_power_missing = target_soc - current_battery_soc

                _solar_production_limit = sum([slot["chargeable"] for slot in self.today_solar_forceast.values()]) * 0.8 # calculate reduction only during thew first 80% of the solar time and keep 20% as reserve
                if _solar_production_limit < _charge_power_missing * SOLAR_SAFETY_TRESHOLD: # for charge limitation, today must be 50% more then needed (safty net)
                    max_power_msg = "not enough solar"
                else:
                    # *** COLLECT UPCOMMING SLOTS until production limit is reached ***
                    _solar_max_power = 0
                    _solar_power_used = 0
                    _ref_now = now.replace(minute=math.floor(now.minute / 15) * 15, second=0, microsecond=0)
                    solar_slots_used = []
                    for slot in self.today_solar_forceast.values():
                        if slot["timestamp"].timestamp() >= _ref_now.timestamp(): # cmp by timestamp for performance reason
                            solar_slots_used.append({"timestamp": slot["timestamp"], "chargeable": slot["chargeable"], "limit": None})

                        if slot["chargeable"] > _solar_max_power:
                            _solar_max_power = slot["chargeable"]

                        _solar_power_used += slot["chargeable"]
                        if _solar_power_used >= _solar_production_limit:
                            break
                    solar_base_power = _solar_max_power * 0.5

                    if len(solar_slots_used) <= 0:
                        max_power_msg = "end time"
                    else:
                        _remaining_production_total = sum([slot["chargeable"] for slot in solar_slots_used])
                        if _remaining_production_total < _charge_power_missing:  # more then 2% missing
                            max_power_msg = "not enough solar"
                        else:
                            _solar_min_limit = STORAGE_MIN_CHARGING_POWER / 4
                            _charge_base_reduction = 0
                            _charge_peak_reduction = 0
                            _solar_slots_used = []
                            while _charge_base_reduction < 1 or _charge_peak_reduction < 1:
                                _charging_total = 0
                                __solar_slots_used = []
                                for slot in solar_slots_used:
                                    _value = round(solar_base_power * (1 - _charge_base_reduction) + (slot["chargeable"] - solar_base_power) * (1 - _charge_peak_reduction), 2) # * _charge_reduction ** 2
                                    if _value <= _solar_min_limit:
                                        _value = 0

                                    __solar_slots_used.append({"timestamp": slot["timestamp"], "chargeable": slot["chargeable"], "limit": _value})
                                    _charging_total += _value

                                # _charging_total not enough means max power is too low, keep the previous one
                                if _charging_total < _charge_power_missing:
                                    break

                                _solar_slots_used = __solar_slots_used
                                if _charge_base_reduction < 1:
                                    _charge_base_reduction += 0.05
                                else:
                                    _charge_peak_reduction += 0.05

                            solar_slots_used = _solar_slots_used

                            if len(solar_slots_used) > 0:
                                if now < solar_slots_used[0]["timestamp"]:
                                    requested_max_power = 0
                                    max_power_msg = "delayed until {}".format(solar_slots_used[0]["timestamp"].strftime('%H:%M'))
                                else:
                                    _end_timestamp = solar_slots_used[0]["timestamp"] + timedelta(minutes=15)
                                    _limit = solar_slots_used[0]["limit"]
                                    for slot in solar_slots_used:
                                        if slot["limit"] != _limit:
                                            break
                                        _end_timestamp = slot["timestamp"] + timedelta(minutes=15)
                                    requested_max_power = _limit * 4
                                    max_power_msg = "unil {}".format(_end_timestamp.strftime('%H:%M'))
                            else:
                                max_power_msg = "no slots found"

            #if target_percent < 100:
            max_power_msg = "{}, max {}%".format(max_power_msg, target_percent)

        return [requested_max_power, max_power_msg]

    def _getStorageChargingPower(self, battery_soc):
        battery_percent = int(round(battery_soc * 100 / STORAGE_MAX_CAPACITY, 0))
        if battery_percent > 100:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[100]

        if battery_percent <= STORAGE_MAX_CHARGING_UNTIL_PERCENT:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[STORAGE_MAX_CHARGING_UNTIL_PERCENT]


        return STORAGE_PERCENT_TO_CHARING_POWER_MAP[battery_percent]

    def calculateStorageChargeLevel(self, now, charging_start, charging_end, consumption_start, consumption_end, sunrise, sunset):
        stock_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(now).getState().doubleValue()
        battery_price = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Price").doubleValue()

        solar_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue()
        grid_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue()
        current_battery_soc = Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").doubleValue()
        current_battery_percent = Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").intValue()

        today_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Consumption").doubleValue()
        today_production = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Production").doubleValue()

        # *** CALCULATE AND CACHE SOLAR AND HEATING
        expected_total_demand, expected_heating_demand, expected_total_demand_msg = self.getExpectedTotalDemand()
        soc_relevant_demand = expected_total_demand - (today_consumption if now >= consumption_start else 0.0)
        soc_relevant_solar_production = 0.0

        _active_solar_forcecast = self.today_solar_forceast if now >= consumption_start else self.tomorrow_solar_forceast
        if _active_solar_forcecast is not None:
            _expected_solar_production = _consumed_solar_production = 0
            for slot in _active_solar_forcecast.values():
                _expected_solar_production += slot["total"]
                _consumed_solar_production += slot["consumed"]
                soc_relevant_solar_production += slot["chargeable"]
            soc_relevant_demand -= _consumed_solar_production

            expected_solar_msg = "{:.2f}kWh (consumption {:.2f}kWh, soc {:.2f}kWh)".format(_expected_solar_production, _consumed_solar_production, soc_relevant_solar_production)

            _today_remaining_solar_production = sum(slot["total"] for slot in self.today_solar_forceast.values() if slot["timestamp"] >= now)
            _today_total_solar_production = sum(slot["total"] for slot in self.today_solar_forceast.values())
            current_solar_msg = "{:.2f}kWh • Expected {:.2f}kWh • Forecast {:.2f}kWh".format(today_production, _today_remaining_solar_production + today_production, _today_total_solar_production)
        else:
            expected_solar_msg = "not working"
            current_solar_msg = "{:.2f}kWh".format(today_production)

        # too much
        if STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_demand + soc_relevant_solar_production > STORAGE_MAX_CAPACITY:
            target_battery_soc = STORAGE_MAX_CAPACITY - soc_relevant_solar_production
            battery_target_msg = "max capacity - soc relevant solar"

        else:
            target_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_demand
            battery_target_msg = "emergency + total demand{}".format(" - consumed solar" if _active_solar_forcecast is not None else "")

        _night_duration = (charging_end - (charging_start if now < charging_start else now)).total_seconds() / 60.0 / 60.0
        _evening_duration = _night_duration - 8.0 if _night_duration > 8.0 else 0
        _sleeping_duration = _night_duration - _evening_duration
        _heating_demand_per_hour = expected_heating_demand / 24
        expected_total_demand_during_night = round(_evening_duration * (BASE_DAY_CONSUMPTION_PER_HOUR + _heating_demand_per_hour) + _sleeping_duration * (BASE_NIGHT_CONSUMPTION_PER_HOUR + _heating_demand_per_hour), 1)

        if target_battery_soc < STORAGE_EMERGENCY_ENERGY_SOC + expected_total_demand_during_night:
            target_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC + expected_total_demand_during_night
            battery_target_msg = "emergency + evening/night demand"

        target_battery_percent = target_battery_soc * 100 / STORAGE_MAX_CAPACITY

        self.logger.info("Forecast: {} 🌞 Solar {}".format(expected_total_demand_msg, expected_solar_msg))
        self.logger.info("        : 🏠 Total demand {:.2f}kWh 🔋 Battery target {:.2f}kWh ({:.0f}%) ({})".format(expected_total_demand, target_battery_soc, target_battery_percent, battery_target_msg))
        self.logger.info("        : --")

        self.logger.info("Current : 🔋 Battery {:.2f}kWh ({:.0f}%) • {:.2f}kWh ({:.2f}€/kWh) • {:.2f}kWh (0.00€/kWh)".format(current_battery_soc, current_battery_percent, grid_battery_soc, battery_price, solar_battery_soc))
        self.logger.info("        : 💰 Spot price {:.2f}€/kWh 🏠 Consumption {:.2f}kWh 🌞 Solar {}".format(stock_price, today_consumption, current_solar_msg))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_grid_charge_power, grid_charge_state_msg, grid_charge_next_state_msg, grid_charge_details_msg = self.charging_helper.calculateRequestedPower(
            start_time = charging_start,
            end_time = charging_end,
            current_time = now,
            current_energy_soc = current_battery_soc,
            target_energy_soc = target_battery_soc,
            min_charging_power = STORAGE_MIN_CHARGING_POWER,
            max_charging_power = STORAGE_MAX_CHARGING_POWER,
            charging_callback = self._getStorageChargingPower
        )

        if grid_charge_details_msg is not None:
            self.logger.info("Charging: {}".format(grid_charge_details_msg))
            self.logger.info("        : --")

        # *** CALCULATE MAX CHARGING (limit solar charging during the day)
        requested_max_solar_charge_power, max_solar_charge_info = self.calculateStorageMaxSolarChargePower(now, current_battery_soc, expected_total_demand, sunrise, sunset)

        if requested_grid_charge_power is not None and requested_max_solar_charge_power is not None:
            # 1. "calculateStorageMaxSolarChargePower" happens only during the day and "calculateRequestedPower" only during the night
            # 2. "calculateStorageMaxSolarChargePower" depends on a high solar production
            # 3, "calculateRequestedPower" (via "target_battery_soc") depends on a low solar production
            self.logger.error("Requested Grid Charge and Limit Solar Charge should never happens at the same time")
            requested_max_solar_charge_power = None

        # *** CALCULATE DISCHARING ALLOWED
        is_discharging_allowed, max_discharge_info = self.isDischargingAllowed(now, current_battery_soc, stock_price, battery_price, expected_total_demand, sunset)

        grid_charge_msg = "{} ({}{})".format("No grid charge" if requested_grid_charge_power is None else "Active with {:.2f}kWh".format(requested_grid_charge_power), grid_charge_state_msg, " • {}".format(grid_charge_next_state_msg) if grid_charge_next_state_msg is not None else "")
        max_discharge_msg = "{} ({})".format("No discharge limit" if is_discharging_allowed else "Discharging refused" , max_discharge_info)
        max_solar_charge_msg = "{} ({})".format("No solar charge limit" if requested_max_solar_charge_power is None else "Solar charge limit is {:.2f}kWh".format(requested_max_solar_charge_power), max_solar_charge_info)
        self.logger.info("State   : ✨ {}{}{}".format(grid_charge_msg, " • " + max_discharge_msg, " • " + max_solar_charge_msg))

        #Registry.getItem("pGF_Garage_Solar_Storage_Requested_Grid_Power").postUpdateIfDifferent(REST_API_NULL_VALUE if requested_grid_charge_power is None else int(requested_grid_charge_power * 1000))
        #Registry.getItem("pGF_Garage_Solar_Storage_Requested_Grid_Message").postUpdateIfDifferent("{} ({})".format("inactive" if requested_grid_charge_power is None else "{:.2f}kW".format(requested_grid_charge_power), grid_charge_state_msg))

        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Solar_Power").postUpdateIfDifferent(REST_API_NULL_VALUE if requested_max_solar_charge_power is None else int(requested_max_solar_charge_power * 1000))
        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Solar_Message").postUpdateIfDifferent("{} ({})".format("inactive" if requested_max_solar_charge_power is None else "{:.2f}kW".format(requested_max_solar_charge_power), max_solar_charge_info))

        Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Allowed").postUpdateIfDifferent(scope.ON if is_discharging_allowed else scope.OFF)
        Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Message").postUpdateIfDifferent("{} ({})".format("yes" if is_discharging_allowed else "no", max_discharge_info))

    def calculateCarChargeLevel(self, now, charging_start, charging_end):
        current_battery_soc = Registry.getItemState("pGF_Outdoor_Car_EnergySoc").doubleValue()
        current_battery_percent = Registry.getItemState("pGF_Outdoor_Car_EssSoc").intValue()

        target_battery_soc = CAR_MAX_CAPACITY
        target_battery_percent = target_battery_soc * 100 / CAR_MAX_CAPACITY

        self.logger.info("Car     : 🔋 Current {:.2f}kWh ({:.0f}%) • Target {:.2f}kWh ({:.0f}%)".format(current_battery_soc, current_battery_percent, target_battery_soc, target_battery_percent))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_charge_power, state_msg, next_state_msg, details_msg = self.charging_helper.calculateRequestedPower(
            start_time = charging_start,
            end_time = charging_end,
            current_time = now,
            current_energy_soc = current_battery_soc,
            target_energy_soc = target_battery_soc,
            min_charging_power = CAR_MIN_CHARGING_POWER,
            max_charging_power = CAR_MAX_CHARGING_POWER,
            charging_callback = lambda battery_soc: CAR_MAX_CHARGING_POWER
        )

        if details_msg is not None:
            self.logger.info("Charging: {}".format(details_msg))
            self.logger.info("        : --")

        self.logger.info("State   : ✨ {} ({}{})".format("No grid charge" if requested_charge_power is None else "Active with {:.2f}kWh".format(requested_charge_power), state_msg, " • {}".format(next_state_msg) if next_state_msg is not None else ""))


        if requested_charge_power is not None:
            Registry.getItem("pGF_Outdoor_Car_RequestedPower").sendCommand(int(round(requested_charge_power * 1000.0)))

    def execute(self, module, input):
        #self.logger.info("--------: >>>")

        # *** INIT DATES
        #now = datetime.now().astimezone().replace(hour=12, minute=15) #  - timedelta(days=1)
        #self.next_solar_calculation = now
        #self.next_heating_calculation = now
        now = datetime.now().astimezone()

        sunrise = Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime()
        sunset = Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime()

        # calculate for tomorrow
        if now > sunrise:
            charging_start = sunset                                                                                         # charging starts today sunset
            charging_end = sunrise + timedelta(days=1)                                                                      # charging ends tomorrow sunrise
        # calculate for today
        else:
            charging_start = sunset - timedelta(days=1)                                                                     # charging starts yesterday sunset
            charging_end = sunrise                                                                                          # charging ends today sunrise

        # *** INIT
        self.charging_helper.refresh(now, Registry.getItemState("pGF_Garage_Solar_Inverter_GridEnabled").intValue() == 1)

        # *** BATTERY CHARGING
        if Registry.getItemState("pGF_Garage_Solar_Inverter_Charge_Control") == scope.ON:
            consumption_start = charging_end.replace(hour=0, minute=0, second=0, microsecond=0)                             # consumptions starts on the day where charging ends
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions ends

            self.initStorageCache(now, consumption_start, consumption_end)

            self.calculateStorageChargeLevel(now, charging_start, charging_end, consumption_start, consumption_end, sunrise, sunset)

        # *** CAR CHARGING
        if Registry.getItemState("pGF_Outdoor_Car_Charge_Control") == scope.ON and Registry.getItemState("pGF_Outdoor_Car_IsConnected") == scope.ON:
            #self.logger.info("--------: <<<")
            #self.logger.info("--------: >>>")

            self.calculateCarChargeLevel(now, charging_start, charging_end)

        #self.logger.info("--------: <<<")

@rule(
    runtime_measurement = False,
    triggers = [
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ProductionActivePower"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ConsumptionActivePower"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_Requested_Grid_Power"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_Requested_Max_Solar_Power"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_Discharged_Allowed"),
    ]
#    , profile_code=True
)
class StorageControl:
    def __init__(self):
        self.delayed_items = ["pGF_Garage_Solar_Inverter_ConsumptionActivePower", "pGF_Garage_Solar_Inverter_ProductionActivePower"]
        self.active_power = Registry.getItemState("pGF_Garage_Solar_Storage_ActivePowerEqual").intValue()
        self.last_refresh = datetime.now().astimezone()
        self.lock = threading.Lock()
        self.timer = None

    def _formatPower(self, power):
        return power if power != REST_API_NULL_VALUE else "off"

    def refreshDelayed(self):
        with self.lock:
            self.timer = None
            self.refresh(self.active_power, "Refresh")

    def refresh(self, active_power = None, info = None):
        now = datetime.now().astimezone()
        if active_power is not None:
            msg = "{}".format(self.active_power) if active_power == self.active_power else "{} => {}".format( self._formatPower(self.active_power), self._formatPower(active_power))
            if info is not None:
                msg = "{} • {}".format(msg, info)
            self.logger.info("Control : 🔋 Active Power: {}".format(msg))

            Registry.getItem("pGF_Garage_Solar_Storage_ActivePowerEqual").sendCommand(active_power)
            self.active_power = active_power
            self.last_refresh = now

        if self.active_power != REST_API_NULL_VALUE:
            self.timer = threading.Timer(30 - (now - self.last_refresh).total_seconds(), self.refreshDelayed) # Watchdog Timer
            self.timer.start()

    def processDelayed(self, requested_power, requested_max_power, is_discharging_allowed):
        with self.lock:
            self.timer = None
            self.process(requested_power, requested_max_power, is_discharging_allowed)

    def process(self, requested_power, requested_max_power, is_discharging_allowed):
        production_power = Registry.getItemState("pGF_Garage_Solar_Inverter_ProductionActivePower").intValue()
        consumption_power = Registry.getItemState("pGF_Garage_Solar_Inverter_ConsumptionActivePower").intValue()

        # https://community.openems.io/t/wirkleistungsvorgabe-setactivepowerlessorequals/2811
        # ActivePowerEqual means on the DC/AC "bridge" (after solar production and battery charge/discharge)
        # Negative "ActivePowerEqual" means, AC is requested and Battery is charged with solar production plus requested AC.
        # Positive "ActivePowerEqual" means, AC is provided and Battery is discharged with provided AC minus solar production.
        if requested_power != REST_API_NULL_VALUE and requested_power > production_power - consumption_power:
            active_power = production_power - requested_power
        elif requested_max_power != REST_API_NULL_VALUE and requested_max_power < production_power - consumption_power:
            active_power = production_power - requested_max_power
        elif not is_discharging_allowed and consumption_power > production_power:
            active_power = production_power
        else:
            active_power = REST_API_NULL_VALUE

        if self.active_power != active_power:
            if active_power != REST_API_NULL_VALUE and active_power > 10000:
                self.logger.warn("Active power should not bigger then 10000W. It is a sign for a wrong solar charge power limitation during the day")
                active_power = 10000

            self.refresh(active_power, "Requested power: {} (max {}) • Discharging allowed: {} • Production: {} • Consumption: {}".format(self._formatPower(requested_power), self._formatPower(requested_max_power), is_discharging_allowed, production_power, consumption_power))
        else:
            self.refresh() # just reactivate refresh thread

    def execute(self, module, input):
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None

            requested_power = Registry.getItemState("pGF_Garage_Solar_Storage_Requested_Grid_Power").intValue()
            requested_max_power = Registry.getItemState("pGF_Garage_Solar_Storage_Requested_Max_Solar_Power").intValue()
            is_discharging_allowed = Registry.getItemState("pGF_Garage_Solar_Storage_Discharged_Allowed") == scope.ON

            if requested_power == REST_API_NULL_VALUE and requested_max_power == REST_API_NULL_VALUE and is_discharging_allowed:
                if self.active_power != REST_API_NULL_VALUE:
                    self.refresh(REST_API_NULL_VALUE, "Nothing requested")
            elif input['event'].getType() == "TimerEvent" or input['event'].getItemName() not in self.delayed_items:
                self.process(requested_power, requested_max_power, is_discharging_allowed)
            else:
                self.timer = threading.Timer(0.1, self.processDelayed, args=[requested_power, requested_max_power, is_discharging_allowed])
                self.timer.start()
