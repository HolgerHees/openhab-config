import math
import json
import threading
import time

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper
from custom.charging import ChargingHelper
from custom.watering import WateringHelper
from custom.heating import HeatingHelper

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

SOLAR_MIN_SAFETY_TRESHOLD = 1.5 #1.5 # special logic applies only if 160% of needed energy is expected as solar
SOLAR_MAX_SAFETY_TRESHOLD = 2.0 #1.5 # special logic applies only if 160% of needed energy is expected as solar
SOLAR_SAFETY_DAYS_LOOKUP = 2
#SOLAR_SAFETY_TRESHOLD = 2.0 #1.5 # special logic applies only if 160% of needed energy is expected as solar
SOLAR_CHARGE_ENDING_TRESHOLD = 0.66 # solar charging should be done, after 66% of total expected charge

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
HEATING_WW_ENERGY = 1.0 #0.7

#COOLING_MAX_AVG_TEMPERATURE = 28.00
#COOLING_MIN_AVG_TEMPERATURE = 20.00
#COOLING_MAX_AVG_TEMPERATURE_DIFF = COOLING_MAX_AVG_TEMPERATURE - COOLING_MIN_AVG_TEMPERATURE
VENTILATION_BASE_ENERGY = 0.5 # KW per day
COOLING_MIN_ENERGY = 4.0 # KW per day
COOLING_MAX_ENERGY = 10.0 # KW per day
COOLING_DIFF = 5.00

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

ATTIC_LIGHT_ENERGY_PER_HOUR = 0.4 # 0.2
WATER_PUMP_ENERGY_PER_HOUR = 1.6

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
        return Registry.getItemState(item_name).doubleValue()

    def calculate(self, current_battery_energy_soc):
        current_battery_price = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Price").doubleValue()

        current_solar_energy_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue()
        current_grid_energy_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue()

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
                self.logger.info("STOCK PRICE: JDBC: {} DIRECT: {}".format(current_stock_price, Registry.getItemState("pGF_Utilityroom_Electricity_Stock_Price").doubleValue()))

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
    TIMESPAN = 4

    def __init__(self):
        self.next_cache_calculation = datetime.now().astimezone()
        self.last_consumtion_start = None

        self.max_temperature_past = None
        self.avg_day_temperature_past = None

        self.avg_day_temperature_future = None
        self.max_temperature_future = None

        self.expected_solar_productions = None

        self.avg_expected_temperature = None

        self.charging_helper = ChargingHelper(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc"))

    def initStorageCache(self, now, consumption_start, consumption_end):
        if self.last_consumtion_start != consumption_start:
            self.avg_expected_temperature = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").averageBetween(consumption_start, consumption_end).doubleValue()
            self.last_consumtion_start = consumption_start

        if now.day != self.next_cache_calculation.day or now >= self.next_cache_calculation:
            forecast_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            forecast_end = forecast_start + timedelta(days=self.TIMESPAN)

            _start = (now - timedelta(hours=24))
            self.max_temperature_past = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").maximumBetween(_start, now).getState().doubleValue()
            self.avg_day_temperature_past = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").averageBetween(_start.replace(hour=8), _start.replace(hour=20)).doubleValue()

            self.max_temperature_future = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").maximumBetween(now, now+timedelta(hours=24)).getState().doubleValue()
            self.avg_day_temperature_future = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").averageBetween(now.replace(hour=8), now.replace(hour=20)).doubleValue()

            east = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_East_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()
            south = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_South_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()
            west = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_West_Production").getPersistence("jdbc").deltaBetween(forecast_start, forecast_end).doubleValue()

            # TODO camera based snow detection
            if self.max_temperature_past < 0 and self.max_temperature_future < 0 and east < 2.0 and south < 1.2 and west < 1.6:
                # SNOW active
                self.expected_solar_productions = None
            else:
                expected_solar_productions = {}

                forecast_end = forecast_end - timedelta(microseconds=1) # needed to exclude ending slot from the upcomming day

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    diff = (timestamp - forecast_start).days
                    if diff not in expected_solar_productions:
                        expected_solar_productions[diff] = {}

                    if timestamp.timestamp() not in expected_solar_productions[diff]:
                      expected_solar_productions[diff][timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}

                    expected_solar_productions[diff][timestamp.timestamp()]["total"] += value

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_South").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    diff = (timestamp - forecast_start).days
                    if diff not in expected_solar_productions:
                        expected_solar_productions[diff] = {}

                    if timestamp.timestamp() not in expected_solar_productions[diff]:
                      expected_solar_productions[diff][timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}

                    expected_solar_productions[diff][timestamp.timestamp()]["total"] += value

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").getAllStatesBetween(forecast_start, forecast_end)
                for dumped_state in dumped_states:
                    timestamp = dumped_state.getTimestamp()
                    value = dumped_state.getState().doubleValue()
                    if value == 0:
                        continue

                    diff = (timestamp - forecast_start).days
                    if diff not in expected_solar_productions:
                        expected_solar_productions[diff] = {}

                    if timestamp.timestamp() not in expected_solar_productions[diff]:
                      expected_solar_productions[diff][timestamp.timestamp()] = {"timestamp": timestamp, "total": 0, "chargeable": 0, "consumed": 0}

                    expected_solar_productions[diff][timestamp.timestamp()]["total"] += value

                totals = {}
                for i in range(0, self.TIMESPAN):
                  #print(i, expected_solar_productions[i])
                  for slot in expected_solar_productions[i].values():
                      if i not in totals:
                          totals[i] = 0
                      totals[i] += slot["total"]
                      slot["chargeable"] = max(slot["total"] - BASE_DAY_CONSUMPTION_PER_HOUR / 4, 0)
                      slot["consumed"] = min(BASE_DAY_CONSUMPTION_PER_HOUR / 4, slot["total"])

                self.expected_solar_productions = expected_solar_productions

                self.logger.info("Calculate solar between {} and {}. Today expected solar: {}, Tomorrow expected solar: {}".format(forecast_start, forecast_end, round(totals[0], 2), round(totals[1], 2)))

            # weather data are fetched every hour at 5 past
            # expected solar is processed every hour at 6 past
            # this is why we recalculate forcecast every hour at 7 past
            self.next_cache_calculation = (now + timedelta(hours=1)).replace(minute=7,second=0, microsecond=0)

    def getExpectedTotalDemand(self, now, charging_start, charging_end, dawn_duration):
        # House heating
        if Registry.getItemState("pGF_Utilityroom_Heatpump_Auto_Mode").intValue() == HeatingHelper.STATE_MODE_AUTO:
          if self.avg_expected_temperature > HEATING_MAX_TEMPERATURE:
              house_heating = 0
          elif self.avg_expected_temperature < HEATING_MIN_TEMPERATURE:
              house_heating = HEATING_MAX_ENERGY
          else:
              house_heating = ( self.avg_expected_temperature - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF
        else:
              house_heating = 0

        # Water heating if current ww temperature not more then 5° above target ww temperature
        current_ww_temperature = Registry.getItemState("pGF_Utilityroom_Heatpump_WW_Warmwassertemperatur").doubleValue()
        target_ww_temperature = Registry.getItemState("pGF_Utilityroom_Heatpump_WW_Warmwassersolltemperatur").doubleValue()
        if current_ww_temperature - target_ww_temperature < 5:
            house_heating += HEATING_WW_ENERGY

        # Cooling / Ventilation
        house_cooling = VENTILATION_BASE_ENERGY
        if Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Power") == scope.ON and Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Season").intValue() == HeatingHelper.STATE_CLIME_SEASON_COOLING and Registry.getItemState("pGF_Utilityroom_Heatpump_Auto_Mode").intValue() == HeatingHelper.STATE_MODE_COOLING:
            reference_temperature = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").doubleValue()
            target_temperature = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Target_Temperature").doubleValue()
            if reference_temperature > target_temperature:
                temp_diff = reference_temperature - target_temperature
                if temp_diff > COOLING_DIFF:
                  temp_diff = COOLING_DIFF
                energy_diff = COOLING_MAX_ENERGY - COOLING_MIN_ENERGY
                house_cooling = ( temp_diff * COOLING_DIFF / energy_diff ) + COOLING_MIN_ENERGY

        # Attic plants light
        state = Registry.getItemState("pOther_Manual_State_Auto_Attic_Light").intValue()
        indoor_plant_energy = (18 if state == 1 else 12) * ATTIC_LIGHT_ENERGY_PER_HOUR if state > 0 else 0

        # Garage plants heating
        outdoor_plant_energy = ChargingHelper.findValueFromMap(self.avg_expected_temperature, FROST_GUARD_HEATING_MAP)

        # Garden plants irrigation
        #print(self.avg_day_temperature_past)
        #print(self.avg_day_temperature_future)
        ref_temp = max(self.avg_day_temperature_past, self.avg_day_temperature_future)
        if ref_temp > 25:
            outdoor_plant_energy += 4 * WATER_PUMP_ENERGY_PER_HOUR
        elif ref_temp > 24:
            outdoor_plant_energy += 3 * WATER_PUMP_ENERGY_PER_HOUR
        elif ref_temp > 23:
            outdoor_plant_energy += 2 * WATER_PUMP_ENERGY_PER_HOUR
        elif ref_temp > 22:
            outdoor_plant_energy += 1 * WATER_PUMP_ENERGY_PER_HOUR
        #if Registry.getItemState("pOutdoor_Plant_Sensor_Lawn_Back_Left_Switch") == scope.ON:
        #    state = Registry.getItemState("pOutdoor_Plant_Sensor_Lawn_Back_Left_State").intValue()
        #    if state == WateringHelper.STATE_WATERING_MAYBE:
        #        outdoor_plant_energy += 0.5 * WATER_PUMP_ENERGY_PER_HOUR
        #    elif state == WateringHelper.STATE_WATERING_NOW:
        #        outdoor_plant_energy += 1.0 * WATER_PUMP_ENERGY_PER_HOUR
        #if Registry.getItemState("pOutdoor_Plant_Sensor_Lawn_Streedside_Switch") == scope.ON:
        #    state = Registry.getItemState("pOutdoor_Plant_Sensor_Lawn_Streedside_State").intValue()
        #    if state == WateringHelper.STATE_WATERING_MAYBE:
        #        outdoor_plant_energy += 0.5 * WATER_PUMP_ENERGY_PER_HOUR
        #    elif state == WateringHelper.STATE_WATERING_NOW:
        #        outdoor_plant_energy += 1.0 * WATER_PUMP_ENERGY_PER_HOUR

        # DEBUG
        msg = "🏠 Base {:.2f}kWh 🔥 Heating {:.2f}kWh 💨 Cooling {:.2f}kWh 🪴 Indoor {:.2f}kWh 🌳 Outdoor {:.2f}kWh".format(MAX_CONSUMPTION_PER_DAY, house_heating, house_cooling, indoor_plant_energy, outdoor_plant_energy)

        _consumption_start = charging_start - timedelta(seconds=dawn_duration * 3)
        _sleeping_time = _consumption_start.replace(hour=23,minute=0,second=0,microsecond=0)
        evening_duration = ( _sleeping_time - (_consumption_start if now < _consumption_start else now) ).total_seconds() / 60.0 / 60.0 if now < _sleeping_time else 0

        _consumption_end = charging_end + timedelta(seconds=dawn_duration * 3)
        sleeping_duration = (_consumption_end - (_sleeping_time if now < _sleeping_time else now) ).total_seconds() / 60.0 / 60.0 if now < _consumption_end else 0

        total_consumption = MAX_CONSUMPTION_PER_DAY + house_heating + house_cooling + indoor_plant_energy + outdoor_plant_energy

        evening_consumption_per_hour = house_heating / 20 + house_cooling / 24 + ( indoor_plant_energy + outdoor_plant_energy ) / 18 # heating only during 20 hours, cooling during 24 hours, and the rest only during 18 hours
        evening_consumption = round(evening_duration * (BASE_DAY_CONSUMPTION_PER_HOUR * 2 + evening_consumption_per_hour), 1)

        sleep_consumption_per_hour = house_heating / 20 + house_cooling / 24
        sleeping_consumption = round(sleeping_duration * (BASE_NIGHT_CONSUMPTION_PER_HOUR + sleep_consumption_per_hour), 1)

        #print(evening_duration, evening_consumption, _consumption_start)
        #print(sleeping_duration, sleeping_consumption, _consumption_end)

        return total_consumption, evening_consumption + sleeping_consumption, msg

    def getStorageChargingPower(self, battery_soc):
        battery_percent = int(round(battery_soc * 100 / STORAGE_MAX_CAPACITY, 0))
        if battery_percent > 100:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[100]

        if battery_percent <= STORAGE_MAX_CHARGING_UNTIL_PERCENT:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[STORAGE_MAX_CHARGING_UNTIL_PERCENT]


        return STORAGE_PERCENT_TO_CHARING_POWER_MAP[battery_percent]

    def isDischargingAllowed(self, current_battery_soc, emergency_battery_soc, stock_price, battery_price):
        if emergency_battery_soc < 0:
            return [True, "no grid"]

        if current_battery_soc <= emergency_battery_soc:
            is_allowed, msg = [False, "no energy"]
        elif Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue() > 0:
            is_allowed, msg = [True, "solar energy"]
        elif stock_price > battery_price:
            is_allowed, msg = [True, "storage cheaper"]
        else:
            is_allowed, msg = [False, "grid cheaper"]

        if emergency_battery_soc < STORAGE_EMERGENCY_ENERGY_SOC:
            msg = "{} • reduced emergency".format(msg)
        return [is_allowed, msg]

    def calculateStorageMaxSolarChargePower(self, now, current_battery_soc, max_battery_soc):
        requested_max_power = None

        if max_battery_soc < STORAGE_MAX_CAPACITY * 0.6: # not less then 60%
            target_battery_soc = STORAGE_MAX_CAPACITY * 0.6
        elif max_battery_soc > STORAGE_MAX_CAPACITY * 0.95: # upper 95% => 100%
            target_battery_soc = STORAGE_MAX_CAPACITY
        else:
            target_battery_soc = max_battery_soc

        if current_battery_soc < target_battery_soc * 0.5:
            max_power_msg = "battery low"
        elif current_battery_soc > STORAGE_MAX_CAPACITY * 0.95:
            max_power_msg = "battery full"
        elif current_battery_soc >= target_battery_soc:
            requested_max_power = 0
            max_power_msg = "battery health"
        else:
            TEST = 0 # 0 disabled, 1 log, 2 testdata
            if TEST == 2:
              _charge_power_missing = 9.5
              hour = 13
            else:
              _charge_power_missing = target_battery_soc - current_battery_soc
              hour = now.hour

            solar_total_chargeable = 0
            for slot in self.expected_solar_productions[0].values():
                solar_total_chargeable += slot["chargeable"]

            # dynamic "evening buffer" value,
            # should always be anough to fully charge '_charge_power_missing'.
            # is getting smaller during the day when battery is charged
            # minimum buffer is 30% of daily charge or 30% of battery buffer (what is smaller)
            lower_buffer_limit = min(solar_total_chargeable * 0.3, STORAGE_MAX_CAPACITY * 0.3)
            solar_reduceable_chargeable = solar_total_chargeable - (lower_buffer_limit if _charge_power_missing < lower_buffer_limit else _charge_power_missing)

            _start_timestamp = now.replace(hour=hour, minute=math.floor(now.minute / 15) * 15, second=0, microsecond=0).timestamp()
            solar_slots_remaining = []
            solar_used_chargeable = solar_max_chargeable = 0
            for slot in self.expected_solar_productions[0].values():
                if slot["timestamp"].timestamp() >= _start_timestamp: # cmp by timestamp for performance reason
                    solar_slots_remaining.append({"timestamp": slot["timestamp"], "chargeable": slot["chargeable"], "limit": None})
                if slot["chargeable"] > solar_max_chargeable:
                    solar_max_chargeable = slot["chargeable"]
                solar_used_chargeable += slot["chargeable"]

                # stop to keep enough for the "evening buffer"
                if solar_used_chargeable >= solar_reduceable_chargeable:
                    break

            charge_limits = []
            solar_treshold_limit = solar_max_chargeable
            solar_min_limit = STORAGE_MIN_CHARGING_POWER / 4
            while solar_treshold_limit > 0:
                _charge_total = 0
                _charge_limits = []
                for slot in solar_slots_remaining:
                    _value = slot["chargeable"] - solar_treshold_limit
                    if _value < solar_min_limit:
                        _value = 0
                    else:
                      _value = round(_value, 2)
                      _charge_total += _value
                    _charge_limits.append({"timestamp": slot["timestamp"], "chargeable": slot["chargeable"], "limit": _value})

                if _charge_total < _charge_power_missing:
                    solar_treshold_limit -= 0.01
                    continue

                charge_limits = _charge_limits
                break

            for i in reversed(range(0, len(charge_limits))):
                if charge_limits[i]["limit"] != 0:
                    break
                del charge_limits[i]

            if TEST > 0:
              total = 0
              for limit in charge_limits:
                  print("TIME: ", limit["timestamp"].strftime('%H:%M'), "LIMIT", limit["limit"], "SUPPLY", limit["chargeable"] - limit["limit"], "CHARGEABLE",  round(limit["chargeable"], 2))
                  total += limit["limit"]
              print("TOTAL: ", total, "MISSING: ", _charge_power_missing, "solar_treshold_limit", solar_treshold_limit)

            if TEST == 2:
              charge_limits = []

            if len(charge_limits) == 0:
                max_power_msg = "not enough solar"
            else:
                if now < charge_limits[0]["timestamp"]:
                    requested_max_power = 0
                    max_power_msg = "delayed until {}".format(charge_limits[0]["timestamp"].strftime('%H:%M'))
                else:
                    _until_timestamp = charge_limits[0]["timestamp"] + timedelta(minutes=15)
                    _active_limit = charge_limits[0]["limit"]
                    for slot in charge_limits:
                        if slot["limit"] != _active_limit:
                            _until_timestamp = slot["timestamp"]
                            break

                    _end_timestamp = charge_limits[-1]["timestamp"] + timedelta(minutes=15)
                    _end_limit = charge_limits[-1]["limit"]

                    requested_max_power = _active_limit * 4
                    max_power_msg = "unil {}, end {}".format(_until_timestamp.strftime('%H:%M'), _end_timestamp.strftime('%H:%M'))

        return [requested_max_power, max_battery_soc, max_power_msg]

    def calcReduction(self, ratio):
        if ratio > 4.0:
            ratio = 4.0
        ratio = (ratio * -1) + 4.0
        return ratio**3

    def calculateStorageChargeLevel(self, now):
        # ***************************************
        # *** INIT Timeranges, Vars and Cache ***
        dawn = Registry.getItemState("pOutdoor_Astro_Dawn_Time").getZonedDateTime()
        sunrise = Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime()
        sunset = Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime()

        if now > sunrise: # calculate for tomorrow
            charging_start = sunset
            charging_end = sunrise + timedelta(days=1)

            consumption_start = charging_end.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            consumption_end = consumption_start + timedelta(days=1)
        else: # calculate for today
            charging_start = sunset - timedelta(days=1)
            charging_end = sunrise

            consumption_start = charging_end.replace(hour=0, minute=0, second=0, microsecond=0)
            consumption_end = consumption_start + timedelta(days=1)

        self.initStorageCache(now, consumption_start, consumption_end)

        stock_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(now).getState().doubleValue()
        battery_price = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Price").doubleValue()

        solar_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue()
        grid_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue()
        current_battery_soc = Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").doubleValue()
        current_battery_percent = Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").intValue()

        today_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Consumption").doubleValue()
        today_production = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Production").doubleValue()

        #total_consumption, evening_consumption_per_hour, sleep_consumption_per_hour
        expected_total_demand, expected_night_demand, expected_total_demand_msg = self.getExpectedTotalDemand(now, charging_start, charging_end, (sunrise - dawn).total_seconds())

        requested_grid_charge_power = requested_max_solar_charge_power = None
        grid_charge_state_msg = max_solar_charge_info = "wrong time"
        grid_charge_next_state_msg = grid_charge_details_msg = None

        debug_log_infos = []

        emergency_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC

        # ***************************************

        # NO GRID available
        if Registry.getItemState("pGF_Garage_Solar_Inverter_GridEnabled").intValue() != 1:
            emergency_battery_soc = -1
            grid_charge_state_msg = max_solar_charge_info = "no grid"
        # NO Forecast available
        elif self.expected_solar_productions[0] is None:
            grid_charge_state_msg = max_solar_charge_info = "missing forecast"
        # Default
        else:
            calculation_slot_is_today = now < sunrise
            _expected_solar_productions_offset = 0 if calculation_slot_is_today else 1

            expected_total_solar_production = expected_consumed_solar_production = expected_chargeable_solar_production = 0
            for slot in self.expected_solar_productions[_expected_solar_productions_offset].values():
                expected_total_solar_production += slot["total"]
                expected_consumed_solar_production += slot["consumed"]
                expected_chargeable_solar_production += slot["chargeable"]

            # Safety solar is the expected solar production, reduced by a safety factor
            # This factor depends on the "fluctuation" of the upcomming days
            _safety_values = None
            _safety_min_factor = 1
            _safety_factors = []
            for i in range(1,SOLAR_SAFETY_DAYS_LOOKUP+1):
                _total = _consumed = _chargeable = 0
                for slot in self.expected_solar_productions[_expected_solar_productions_offset + i].values():
                    _total += slot["total"]
                    _consumed += slot["consumed"]
                    _chargeable += slot["chargeable"]

                _factor = _total / expected_total_solar_production
                _safety_factors.append(_factor)
                if _factor < _safety_min_factor:
                    _safety_min_factor = _factor
                    _safety_values = {"total": _total, "consumed": _consumed, "chargeable": _chargeable}

            if _safety_values is not None:
              #print(self.solar_radiation_totals)
              debug_log_infos.append("Solar production {:.2f} => {:.2f} {}".format(expected_total_solar_production, _safety_values["total"], list(map(lambda x: round(x,2), _safety_factors))))
              expected_total_solar_production = _safety_values["total"]
              expected_consumed_solar_production = _safety_values["consumed"]
              expected_chargeable_solar_production = _safety_values["chargeable"]

            # ratio of 1 => 0.73, 2 => 0.92, 3 => 0.99, 4 => 1.00
            # factor of 1.0 is only used if 4 times more solar is available
            # factor of 0.73 is only used if 1 times more solar is available
            ratio = min( expected_total_solar_production / expected_consumed_solar_production, 4)
            ratio = (ratio * -1) + 4.0 # invert ration
            _expected_consumed_solar_factor = (100 - ratio**3) / 100.0
            if _expected_consumed_solar_factor < 1:
                _expected_consumed_solar_production = expected_consumed_solar_production * expected_consumed_solar_factor
                debug_log_infos.append("Direct consumption {} => {}".format(expected_consumed_solar_production, _expected_consumed_solar_production))
                expected_consumed_solar_production = _expected_consumed_solar_production

            expected_solar_msg = "Solar production {:.2f}kWh • Direct consumption {:.2f}kWh • Chargeable {:.2f}kWh".format(expected_total_solar_production, expected_consumed_solar_production, expected_chargeable_solar_production)

            today_remaining_solar_production = sum(slot["total"] for slot in self.expected_solar_productions[0].values() if slot["timestamp"] >= now)
            _today_total_solar_production = sum(slot["total"] for slot in self.expected_solar_productions[0].values())
            current_solar_msg = "Solar production {:.2f}kWh of {:.2f}kWh • Original expected {:.2f}kWh".format(today_production, today_remaining_solar_production + today_production, _today_total_solar_production)

            # *** REDUCE LOWER BATTERY LIMIT ***
            # It is allowed to fall below the emergency energy level in the morning of a sunny day. This can occur after several days of poor sunshine.
            # 1. only if we have enough expected solar soon
            # 2. only if the battery is already very empty
            if calculation_slot_is_today and current_battery_soc <= emergency_battery_soc and expected_total_solar_production > expected_total_demand * SOLAR_MAX_SAFETY_TRESHOLD:
                debug_log_infos.append("reduced emergency allowed")
                emergency_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC / 2

            # *********************************************************
            # *** CALCULATE GENERAL BATTERY TARGET ********************
            # >>> INFO: goal is to charge enough energy, taking into account direct consumption
            min_battery_soc = emergency_battery_soc + expected_total_demand - (today_consumption if calculation_slot_is_today else 0.0)
            min_battery_soc -= expected_consumed_solar_production
            battery_target_msg = "emergency + expected demand - consumed solar"

            # *** FORCED CHARGING ****
            charge_offset = Registry.getItemState("pGF_Utilityroom_Electricity_Charge_Offset").intValue()
            if charge_offset > 0:
              expected_total_demand += charge_offset
              expected_night_demand += charge_offset

              if emergency_battery_soc + expected_total_demand > STORAGE_MAX_CAPACITY:
                expected_total_demand = STORAGE_MAX_CAPACITY - emergency_battery_soc

              if emergency_battery_soc + expected_night_demand > STORAGE_MAX_CAPACITY:
                expected_night_demand = STORAGE_MAX_CAPACITY - emergency_battery_soc

              min_battery_soc = emergency_battery_soc + expected_total_demand

              expected_total_demand_msg = "{} ✨ Offset {:.0f}".format(expected_total_demand_msg, charge_offset)

            # >>> INFO: if there is expected chargeable solar, it is priorized to give enough battery space (this prevents grid charge and "MAX SOLAR CHARGE" logic will take over)
            if min_battery_soc + expected_chargeable_solar_production > STORAGE_MAX_CAPACITY:
                min_battery_soc = STORAGE_MAX_CAPACITY - expected_chargeable_solar_production
                battery_target_msg = "max capacity - chargeable solar"
                debug_log_infos.append("expected solar > max capacity")

            # >>> INFO: with a fallback to have enough at last for the evening and night (only happens if there is expected solar)
            if min_battery_soc < emergency_battery_soc + expected_night_demand:
                min_battery_soc = emergency_battery_soc + expected_night_demand
                battery_target_msg = "emergency + evening/night demand"

            debug_log_infos.append("min battery soc = {}".format(battery_target_msg))

            _min_battery_percent = min_battery_soc * 100 / STORAGE_MAX_CAPACITY
            self.logger.info("{}: {}".format("Today   " if calculation_slot_is_today else "Tomorrow", expected_total_demand_msg))
            self.logger.info("        : 🌞 {}".format(expected_solar_msg))
            self.logger.info("        : 🏠 Total demand {:.2f}kWh 🔋 Min Battery {:.2f}kWh ({:.0f}%)".format(expected_total_demand, min_battery_soc, _min_battery_percent))
            self.logger.info("        : --")

            self.logger.info("Today   : 🔋 Battery {:.2f}kWh ({:.0f}%) • {:.2f}kWh ({:.2f}€/kWh) • {:.2f}kWh (0.00€/kWh) 💰 Spot price {:.2f}€/kWh".format(current_battery_soc, current_battery_percent, grid_battery_soc, battery_price, solar_battery_soc, stock_price))
            self.logger.info("        : 🌞 {}".format(current_solar_msg))
            self.logger.info("        : 🏠 Consumption {:.2f}kWh".format(today_consumption))
            self.logger.info("        : --")
            # ********************************************************

            # ********************************************************
            # *** DURING THE DAY, CALCULATE MAX SOLAR CHARGE LEVEL ***
            # >>> INFO: goal is to limit solar charge energy
            if now > sunrise and now < sunset:
                _maximumSinceOneWeekState = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getPersistence("jdbc").maximumSince(sunrise - timedelta(days=6))
                _forceFullStorageCharge = _maximumSinceOneWeekState.getState().intValue() != 100 or now.date() == _maximumSinceOneWeekState.getTimestamp().date()

                min_safety_expected_total_demand = expected_total_demand * SOLAR_MIN_SAFETY_TRESHOLD
                max_safety_expected_total_demand = expected_total_demand * SOLAR_MAX_SAFETY_TRESHOLD

                if _forceFullStorageCharge or expected_total_solar_production < min_safety_expected_total_demand: # charge once a week to 100% or for min battery level, tomorrow must be 50% more then needed (safety net)
                    max_level = 1.0
                    debug_log_infos.append("weekly full charge" if _forceFullStorageCharge else "full charge • low solar expected tomorrow")
                else:
                    # >>> INFO: just charge enough for the next day, taking into account direct consumption
                    # today evening consumtion is included in (expected_total_demand), because tomorrow evening consumption does not matter here
                    _max_battey_soc = emergency_battery_soc + expected_total_demand - expected_consumed_solar_production

                    if min_battery_soc > _max_battey_soc: # can happen if min_battery_soc was pushed by 'min_battery_soc < emergency_battery_soc + expected_night_deman'
                        # DEBUG min_battery_soc 22.78, _max_battey_soc 22.324548442384092, expected_total_demand 26.3, expected_night_demand 12.700000000000001, expected_consumed_solar_production 14.055451557615909
                        #self.logger.info("        : DEBUG min_battery_soc {}, _max_battey_soc {}, expected_total_demand {}, expected_night_demand {}, expected_consumed_solar_production {}".format(min_battery_soc, _max_battey_soc, expected_total_demand, expected_night_demand, expected_consumed_solar_production))
                        _max_battey_soc = min_battery_soc

                    #_max_battey_soc += STORAGE_MAX_CAPACITY * 0.2 # 10kWh safety if weather is not stable

                    max_level = 1.0 if _max_battey_soc > STORAGE_MAX_CAPACITY else min(round(_max_battey_soc / STORAGE_MAX_CAPACITY, 2), 1.0)

                    # *** BOOSTER CALCULATION ***
                    # based on where the expected solar is located between min and max safety level, we increase (boost) the max level
                    # if expected_total_solar_production == min_safety_expected_total_demand => we increase max_level to 1.0
                    # if expected_total_solar_production == max_safety_expected_total_demand => we keep max_level as it is
                    level_booster = 0
                    if expected_total_solar_production < max_safety_expected_total_demand:
                        safety_total_diff = max_safety_expected_total_demand - min_safety_expected_total_demand
                        expected_diff = max_safety_expected_total_demand - expected_total_solar_production
                        level_diff = 1.0 - max_level
                        level_booster = expected_diff * level_diff / safety_total_diff
                        max_level += level_booster

                        #print(expected_total_solar_production)
                        #print(min_safety_expected_total_demand)
                        #print(max_safety_expected_total_demand)
                        #print(max_level, level_booster, expected_diff, level_diff, safety_total_diff)

                        debug_log_infos.append("{:.0f}% boosted • low solar expected tomorrow".format(level_booster * 100))

                _target_battery_soc = round(STORAGE_MAX_CAPACITY * max_level, 1)
                requested_max_solar_charge_power, _max_battery_soc, _max_battery_msg = self.calculateStorageMaxSolarChargePower(now, current_battery_soc, _target_battery_soc)

                _battery_prefix = " ↑{:.0f}%".format(_target_battery_soc * 100 / STORAGE_MAX_CAPACITY) if _target_battery_soc != _max_battery_soc else ""
                max_solar_charge_info = "{}, max {:.0f}%{}".format(_max_battery_msg, _max_battery_soc * 100 / STORAGE_MAX_CAPACITY, _battery_prefix)

                min_battery_soc = None
            # ********************************************************

            # *******************************************************
            # *** CALCULATE POSSIBLE CHARGING *****
            if min_battery_soc is not None:
                # TODO add forced daily charge, if price is 50% of cheapest nightly price

                requested_grid_charge_power, grid_charge_state_msg, grid_charge_next_state_msg, grid_charge_details_msg = self.charging_helper.calculateRequestedPower(
                    start_time = charging_start,
                    end_time = charging_end,
                    current_time = now,
                    current_energy_soc = current_battery_soc,
                    target_energy_soc = min_battery_soc,
                    min_charging_power = STORAGE_MIN_CHARGING_POWER,
                    max_charging_power = STORAGE_MAX_CHARGING_POWER,
                    charging_callback = self.getStorageChargingPower
                )

            if grid_charge_details_msg is not None:
                self.logger.info("Charging: {}".format(grid_charge_details_msg))
                self.logger.info("        : --")
            # ********************************************************

        # ************************************
        # *** CALCULATE DISCHARING ALLOWED ***
        is_discharging_allowed, max_discharge_info = self.isDischargingAllowed(current_battery_soc, emergency_battery_soc, stock_price, battery_price)
        # ****************************************

        grid_charge_msg = "{} ({}{})".format("No grid charge" if requested_grid_charge_power is None else "Active with {:.2f}kW".format(requested_grid_charge_power), grid_charge_state_msg, " • {}".format(grid_charge_next_state_msg) if grid_charge_next_state_msg is not None else "")
        max_discharge_msg = "{} ({})".format("No discharge limit" if is_discharging_allowed else "Discharging refused" , max_discharge_info)
        max_solar_charge_msg = "{} ({})".format("No solar charge limit" if requested_max_solar_charge_power is None else "Solar charge limit is {:.2f}kW".format(requested_max_solar_charge_power), max_solar_charge_info)
        self.logger.info("State   : ✨ {} 🔋 {} 🌞 {}".format(grid_charge_msg, max_discharge_msg, max_solar_charge_msg))
        self.logger.info("        : ✨ {}".format(" • ".join(debug_log_infos)))


        #Registry.getItem("pGF_Garage_Solar_Storage_Requested_Grid_Power").postUpdateIfDifferent(REST_API_NULL_VALUE if requested_grid_charge_power is None else int(requested_grid_charge_power * 1000))
        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Grid_Status").postUpdateIfDifferent("inactive" if requested_grid_charge_power is None else "{:.2f}kW".format(requested_grid_charge_power))
        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Grid_Details").postUpdateIfDifferent(grid_charge_state_msg)

        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Solar_Power").postUpdateIfDifferent(REST_API_NULL_VALUE if requested_max_solar_charge_power is None else int(requested_max_solar_charge_power * 1000))
        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Solar_Status").postUpdateIfDifferent("no limit" if requested_max_solar_charge_power is None else "{:.2f}kW".format(requested_max_solar_charge_power))
        Registry.getItem("pGF_Garage_Solar_Storage_Requested_Max_Solar_Details").postUpdateIfDifferent(max_solar_charge_info)

        #is_discharging_allowed = True
        Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Allowed").postUpdateIfDifferent(scope.ON if is_discharging_allowed else scope.OFF)
        Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Status").postUpdateIfDifferent("allowed" if is_discharging_allowed else "forbidden")
        Registry.getItem("pGF_Garage_Solar_Storage_Discharged_Details").postUpdateIfDifferent(max_discharge_info)

        msg = "GRID: {}, SOLAR: {}, DISCHARGE: {}".format("inactive" if requested_grid_charge_power is None else "active", "no limit" if requested_max_solar_charge_power is None else "limited", "allowed" if is_discharging_allowed else "forbidden")
        Registry.getItem("pGF_Garage_Solar_Storage_Summary_Details").postUpdateIfDifferent(msg)

    # def calculateCarChargeLevel(self, now, charging_start, charging_end):
    #     current_battery_soc = Registry.getItemState("pGF_Outdoor_Car_EnergySoc").doubleValue()
    #     current_battery_percent = Registry.getItemState("pGF_Outdoor_Car_EssSoc").intValue()
    #
    #     target_battery_soc = CAR_MAX_CAPACITY
    #     target_battery_percent = target_battery_soc * 100 / CAR_MAX_CAPACITY
    #
    #     self.logger.info("Car     : 🔋 Current {:.2f}kWh ({:.0f}%) • Target {:.2f}kWh ({:.0f}%)".format(current_battery_soc, current_battery_percent, target_battery_soc, target_battery_percent))
    #     self.logger.info("        : --")
    #
    #     # *** CALCULATE POSSIBLE CHARGING
    #     requested_charge_power, state_msg, next_state_msg, details_msg = self.charging_helper.calculateRequestedPower(
    #         start_time = charging_start,
    #         end_time = charging_end,
    #         current_time = now,
    #         current_energy_soc = current_battery_soc,
    #         target_energy_soc = target_battery_soc,
    #         min_charging_power = CAR_MIN_CHARGING_POWER,
    #         max_charging_power = CAR_MAX_CHARGING_POWER,
    #         charging_callback = lambda battery_soc: CAR_MAX_CHARGING_POWER
    #     )
    #
    #     if details_msg is not None:
    #         self.logger.info("Charging: {}".format(details_msg))
    #         self.logger.info("        : --")
    #
    #     self.logger.info("State   : ✨ {} ({}{})".format("No grid charge" if requested_charge_power is None else "Active with {:.2f}kWh".format(requested_charge_power), state_msg, " • {}".format(next_state_msg) if next_state_msg is not None else ""))
    #
    #
    #     if requested_charge_power is not None:
    #         Registry.getItem("pGF_Outdoor_Car_RequestedPower").sendCommand(int(round(requested_charge_power * 1000.0)))

    def execute(self, module, input):
        self.logger.info("--------: >>>")

        # *** INIT DATES
        now = datetime.now().astimezone()

        # *** INIT
        self.charging_helper.refresh(self.logger, now)

        # *** BATTERY CHARGING
        if Registry.getItemState("pGF_Garage_Solar_Inverter_Charge_Control") == scope.ON:
            self.calculateStorageChargeLevel(now)

        # *** CAR CHARGING
        #if Registry.getItemState("pGF_Outdoor_Car_Charge_Control") == scope.ON and Registry.getItemState("pGF_Outdoor_Car_IsConnected") == scope.ON:
        #    #self.logger.info("--------: <<<")
        #    #self.logger.info("--------: >>>")

        #    self.calculateCarChargeLevel(now, charging_start, charging_end)

        self.logger.info("--------: <<<")

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
                #self.logger.warn("Active power should not bigger then 10000W. It is a sign for a wrong solar charge power limitation during the day")
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
