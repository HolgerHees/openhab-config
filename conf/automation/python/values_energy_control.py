import math
import json

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper
from custom.charging import ChargingHelper

from configuration import customConfigs

import scope


#KWKG-Umlage: 0,446 ct/kWh
#Offshore-Netzumlage: 0,941 ct/kWh
#Aufschlag für besondere Netznutzung (AbN): 1,559 ct/kWh
ENERGY_TRAFFIC_COST_PER_KWH = 0.12 + 0.00446 + 0.00941 + 0.01559
VAT_COST = 1.19 # %

#print(( Registry.getItem("pGF_Garage_Solar_Storage_Capacity").getState().doubleValue() ) / 1000.0)
STORAGE_MAX_CAPACITY = 25.2
STORAGE_EMERGENCY_ENERGY_SOC = STORAGE_MAX_CAPACITY * 0.2

STORAGE_MAX_CHARGING_POWER = STORAGE_MAX_CAPACITY * 0.2
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


@rule(
    triggers = [
#        GenericCronTrigger("*/5 * * * * ?"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_EnergySoc")
    ]
#    , profile_code=True
)
class StorageInfo:
    def __init__(self):
        state = Registry.getItemState("pGF_Utilityroom_Electricity_Cached_Inverter_Energy_State").toString()
        state = json.loads(state)
        self.demand = state["demand"]
        self.supply = state["supply"]
        self.production = state["production"]
        self.consumption = state["consumption"]
        self.last_change = datetime.fromisoformat(state["last_change"])

    def getEnergyDiff(self):
        demand = self.getEnergyValue("pGF_Garage_Solar_Inverter_DemandTotalEnergy")
        demand_diff = demand - self.demand

        supply = self.getEnergyValue("pGF_Garage_Solar_Inverter_SupplyTotalEnergy")
        supply_diff = supply - self.supply

        production = self.getEnergyValue("pGF_Garage_Solar_Inverter_ProductionTotalEnergy")
        production_diff = production - self.production

        consumption = self.getEnergyValue("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy")
        consumption_diff = consumption - self.consumption

        last_change = Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").getLastStateChange()

        state = { "demand": demand, "supply": supply, "production": production, "consumption": consumption, "last_change": last_change.isoformat() }
        Registry.getItem("pGF_Utilityroom_Electricity_Cached_Inverter_Energy_State").postUpdate(json.dumps(state))

        self.logger.info("CHANGED demand from {} to {}, diff {}".format(self.demand, demand, demand_diff))
        self.logger.info("CHANGED supply from {} to {}, diff {}".format(self.supply, supply, supply_diff))
        self.logger.info("CHANGED production from {} to {}, diff {}".format(self.production, production, production_diff))
        self.logger.info("CHANGED consumption from {} to {}, diff {}".format(self.consumption, consumption, consumption_diff))
        self.logger.info("LAST_CHANGE: {}".format(self.last_change))

        self.demand = demand
        self.supply = supply
        self.production = production
        self.consumption = consumption

        previous_change = self.last_change
        self.last_change = last_change

        return [demand_diff, supply_diff, production_diff, consumption_diff, previous_change]

    def getEnergyValue(self, item_name):
        return Registry.getItem(item_name).getState().doubleValue() / 1000.0

    def calculate(self, current_battery_energy_soc):
        current_battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        current_solar_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        current_grid_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()

        demand_diff, supply_diff, production_diff, consumption_diff, previous_change  = self.getEnergyDiff()

        # *** STEP 1: calculate solar charge ***
        total_charge = (production_diff + demand_diff) - ( supply_diff + consumption_diff )
        if total_charge > 0:
            if demand_diff < consumption_diff:
                self.logger.info("SOLAR ONLY CHARGE • TOTAL: {}".format(total_charge))
                new_solar_energy_soc = current_battery_energy_soc - current_grid_energy_soc
            elif production_diff < 0.01: # smaller then 10 Watt
                self.logger.info("GRID ONLY CHARGE • TOTAL: {}".format(total_charge))
                new_solar_energy_soc = current_solar_energy_soc
            else:
                solar_charge = production_diff if production_diff < total_charge else total_charge
                self.logger.info("MIXED SOLAR CHARGE • TOTAL: {} • SOLAR: {}".format(total_charge, solar_charge))
                new_solar_energy_soc = current_solar_energy_soc + ( solar_charge * 0.97 ) # 3% loss
                if new_solar_energy_soc > STORAGE_MAX_CAPACITY:
                    new_solar_energy_soc = STORAGE_MAX_CAPACITY
        else:
            self.logger.info("DISCHARGE • TOTAL: {}".format(total_charge))
            new_solar_energy_soc = current_solar_energy_soc + ( total_charge * 1.03 ) # 3% loss

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
        self.calculate(input['event'].getItemState().doubleValue() / 1000.0)


@rule(
    triggers = [
      GenericCronTrigger("*/30 * * * * ?") # 30 seconds, because of 60 seconds watchdoc for fenecon
#      GenericCronTrigger("*/5 * * * * ?")
    ]
#    , profile_code=True
)
class StoragePower:
    def __init__(self):
        self.last_solar_hour = -1
        self.today_solar_forceast = None
        self.tomorrow_solar_forceast = None

        self.last_heating_hour = -1
        self.house_heating_forecast = None
        self.frost_guard_heating_forecast = None

        self.charging_helper = ChargingHelper(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc"))

    def initSolarForecast(self, now, start, end):
        if self.last_solar_hour != now.hour:
            end = datetime.now().astimezone()
            start = end - timedelta(hours=24)
            temperature_past = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc").maximumBetween(start, end).getState().doubleValue()
            temperature_future = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getPersistence("jdbc").maximumBetween(end, end+timedelta(hours=24)).getState().doubleValue()

            east = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_East_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()
            south = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_South_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()
            west = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_West_Production").getPersistence("jdbc").deltaBetween(start, end).doubleValue()

            #solarpower = Registry.getItem("pOutdoor_WeatherStation_Solar_Power").getPersistence("jdbc").maximumBetween(start, end).getState().doubleValue()

            if temperature_past < 0 and temperature_future < 0 and east < 2.0 and south < 1.2 and west < 1.6:
                # SNOW active
                self.today_solar_forceast = self.tomorrow_solar_forceast = None
            else:
                #print("initSolarForecast")
                self.today_solar_forceast = self.tomorrow_solar_forceast = 0

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Dumped_Solar_East").getPersistence("jdbc").getAllStatesBetween(start, end)
                for dumped_state in dumped_states:
                    if dumped_state.getTimestamp().day == now.day:
                        self.today_solar_forceast += dumped_state.getState().doubleValue()
                    else:
                        self.tomorrow_solar_forceast += dumped_state.getState().doubleValue()

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Dumped_Solar_South").getPersistence("jdbc").getAllStatesBetween(start, end)
                for dumped_state in dumped_states:
                    if dumped_state.getTimestamp().day == now.day:
                        self.today_solar_forceast += dumped_state.getState().doubleValue()
                    else:
                        self.tomorrow_solar_forceast += dumped_state.getState().doubleValue()

                dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Dumped_Solar_West").getPersistence("jdbc").getAllStatesBetween(start, end)
                for dumped_state in dumped_states:
                    if dumped_state.getTimestamp().day == now.day:
                        self.today_solar_forceast += dumped_state.getState().doubleValue()
                    else:
                        self.tomorrow_solar_forceast += dumped_state.getState().doubleValue()

            self.last_solar_hour = now.hour

    def initHeatingForecast(self, now, start, end):
        if self.last_heating_hour != now.hour:
            #print("initHeatingForecast")
            avg_value = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getPersistence("jdbc").averageBetween(start,end).doubleValue()

            if avg_value > HEATING_MAX_TEMPERATURE:
                house_heating = 0
            elif avg_value < HEATING_MIN_TEMPERATURE:
                house_heating = HEATING_MAX_ENERGY
            else:
                house_heating = ( avg_value - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF

            frost_guard_heating = ChargingHelper.findValueFromMap(avg_value, FROST_GUARD_HEATING_MAP)

            self.house_heating_forecast = house_heating
            self.frost_guard_heating_forecast = frost_guard_heating
            self.last_heating_hour = now.hour

    def calculateStorageDischargePower(self, now, current_battery_soc, current_price, battery_price):
        requested_max_discharger_power = None
        if self.charging_helper.isGridMode():
            if current_battery_soc > STORAGE_EMERGENCY_ENERGY_SOC:
                # nicht entladen, wenn aktueller Strompreis gleich dem max Ladestrompreis ist.
                if Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue() <= 0:
                    reference_price = current_price if Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").getState().intValue() == -1 else price_persistance.persistedState(now + timedelta(minutes=1)).getState().doubleValue()
                    if reference_price <= battery_price:
                        requested_max_discharger_power = 0
                        discharge_msg = " • {}".format("Discharging refused • Stock price cheaper")
                    else:
                        discharge_msg = " • {}".format("Discharging allowed • Storage price cheaper")
                else:
                    discharge_msg = " • {}".format("Discharging allowed • Solar energy available")
            else:
                # requested_max_discharger_power = 0 => Not needed. Is handled by FEMS emergency limit
                discharge_msg = " • {}".format("Discharging refused (FEMS) • No energy available")
        else:
            discharge_msg = " • {}".format("Discharging allowed (FEMS) • Emergency mode")

        return [requested_max_discharger_power, discharge_msg]

    def _getStorageChargingPower(self, battery_soc):
        battery_percent = int(round(battery_soc * 100 / STORAGE_MAX_CAPACITY, 0))
        if battery_percent > 100:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[100]

        if battery_percent <= STORAGE_MAX_CHARGING_UNTIL_PERCENT:
            return STORAGE_PERCENT_TO_CHARING_POWER_MAP[STORAGE_MAX_CHARGING_UNTIL_PERCENT]


        return STORAGE_PERCENT_TO_CHARING_POWER_MAP[battery_percent]

    def calculateStorageChargeLevel(self, now, charging_start, charging_end, consumption_start, consumption_end, sunrise, sunset):
        current_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(now).getState().doubleValue()
        battery_price = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Price").doubleValue()

        solar_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Solar_Soc").doubleValue()
        grid_battery_soc = Registry.getItemState("pGF_Utilityroom_Electricity_Storage_Grid_Soc").doubleValue()
        current_battery_soc = Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").doubleValue() / 1000.0
        current_battery_percent = Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").intValue()

        today_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Consumption").doubleValue()
        today_production = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Production").doubleValue()

        # *** CALCULATE AND CACHE SOLAR AND HEATING
        expected_total_consumption = MAX_CONSUMPTION_PER_DAY + self.house_heating_forecast + self.frost_guard_heating_forecast
        soc_relevant_consumption = expected_total_consumption - (today_consumption if now >= consumption_start else 0.0)
        solar_is_working = self.today_solar_forceast is not None and self.tomorrow_solar_forceast is not None

        if solar_is_working:
            _expected_solar_production = self.today_solar_forceast if now >= consumption_start else self.tomorrow_solar_forceast

            _sunshine_in_hours = math.floor((sunset - sunrise).total_seconds() / 60.0 / 60.0)
            _expected_consumption_during_sunshine = _sunshine_in_hours * BASE_DAY_CONSUMPTION_PER_HOUR

            soc_relevant_consumption -= _expected_consumption_during_sunshine
            soc_relevant_solar_production = _expected_solar_production - _expected_consumption_during_sunshine if _expected_solar_production > _expected_consumption_during_sunshine else 0.0

            solar_forecast_msg = "{:.2f}kWh (soc relevant {:.2f}kWh)".format(_expected_solar_production, soc_relevant_solar_production)
            solar_current_msg = "{:.2f}kWh (expected {:.2f}kWh)".format(today_production, self.today_solar_forceast)
        else:
            soc_relevant_solar_production = 0.0

            solar_forecast_msg = "not working"
            solar_current_msg = "{:.2f}kWh".format(today_production)

        is_too_much = STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_consumption + soc_relevant_solar_production > STORAGE_MAX_CAPACITY
        target_battery_soc = STORAGE_MAX_CAPACITY - soc_relevant_solar_production if is_too_much else STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_consumption
        battery_target_msg = ("max capacity - soc relevant solar" if is_too_much else "emergency + consumption") if solar_is_working else "max capacity"

        _midnight = sunrise.replace(hour=0, minute=0, second=0)
        _night_in_hours = math.floor((sunrise - _midnight).total_seconds() / 60.0 / 60.0)
        expected_consumption_during_night = _night_in_hours * BASE_NIGHT_CONSUMPTION_PER_HOUR

        if target_battery_soc < STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night:
            target_battery_soc = STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night
        target_battery_percent = target_battery_soc * 100 / STORAGE_MAX_CAPACITY

        self.logger.info("Forecast: 🏠 Base {:.2f}kWh 🔥 Heating {:.2f}kWh 🌳 Plants {:.2f}kWh 🌞 Solar {}".format(MAX_CONSUMPTION_PER_DAY, self.house_heating_forecast, self.frost_guard_heating_forecast, solar_forecast_msg))
        self.logger.info("        : 🏠 Total demand {:.2f}kWh 🔋 Battery target {:.2f}kWh ({:.0f}%) ({})".format(expected_total_consumption, target_battery_soc, target_battery_percent, battery_target_msg))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE DISCHARGING
        requested_max_discharger_power, discharge_msg = self.calculateStorageDischargePower(now, current_battery_soc, current_price, battery_price)

        self.logger.info("Current : 🔋 Battery {:.2f}kWh ({:.0f}%) • {:.2f}kWh ({:.2f}€/kWh) • {:.2f}kWh (0.00€/kWh)".format(current_battery_soc, current_battery_percent, grid_battery_soc, battery_price, solar_battery_soc))
        self.logger.info("        : 💰 Spot price {:.2f}€/kWh 🏠 Consumption {:.2f}kWh 🌞 Solar {}".format(current_price, today_consumption, solar_current_msg))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_power, state, state_msg, charge_msg = self.charging_helper.calculateRequestedPower(
            start_time = charging_start,
            end_time = charging_end,
            current_time = now,
            current_energy_soc = current_battery_soc,
            target_energy_soc = target_battery_soc,
            min_charging_power = STORAGE_MIN_CHARGING_POWER,
            max_charging_power = STORAGE_MAX_CHARGING_POWER,
            charging_callback = self._getStorageChargingPower
        )

        if charge_msg is not None:
            self.logger.info("Charging: {}".format(charge_msg))
            self.logger.info("        : --")
        self.logger.info("{:<8}: ✨ {}{}".format(state, state_msg, discharge_msg))

        return [requested_power , requested_max_discharger_power]

    def calculateCarChargeLevel(self, now, charging_start, charging_end):
        current_battery_soc = Registry.getItemState("pGF_Outdoor_Car_EnergySoc").doubleValue() / 1000.0
        current_battery_percent = Registry.getItemState("pGF_Outdoor_Car_EssSoc").intValue()

        target_battery_soc = CAR_MAX_CAPACITY
        target_battery_percent = target_battery_soc * 100 / CAR_MAX_CAPACITY

        self.logger.info("Car     : 🔋 Current {:.2f}kWh ({:.0f}%) • Target {:.2f}kWh ({:.0f}%)".format(current_battery_soc, current_battery_percent, target_battery_soc, target_battery_percent))
        self.logger.info("        : --")

        # *** CALCULATE POSSIBLE CHARGING
        requested_power, state, state_msg, charge_msg = self.charging_helper.calculateRequestedPower(
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
        self.logger.info("{:<8}: ✨ {}".format(state, state_msg))

        return requested_power

    def execute(self, module, input):
        self.logger.info("--------: >>>")

        # *** INIT DATES
        now = datetime.now().astimezone() #.replace(hour=23, minute=15) - timedelta(days=1)

        sunrise = Registry.getItemState("pOutdoor_Astro_Sunrise_Time").getZonedDateTime().replace(day=now.day, month=now.month, year=now.year)
        sunset = Registry.getItemState("pOutdoor_Astro_Sunset_Time").getZonedDateTime().replace(day=now.day, month=now.month, year=now.year)

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
            today_morning = now.replace(hour=0, minute=0, second=0, microsecond=0)

            consumption_start = charging_end.replace(hour=0, minute=0, second=0, microsecond=0)                             # consumptions starts on the day where charging ends
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions ends

            self.initSolarForecast(now, today_morning, today_morning + timedelta(days=2))
            self.initHeatingForecast(now, consumption_start, consumption_end)

            requested_power, requested_max_discharger_power = self.calculateStorageChargeLevel(now, charging_start, charging_end, consumption_start, consumption_end, sunrise, sunset)

            if requested_power is not None:
                # START/REFRESH CHARGING => Fenecon Watchdog
                Registry.getItem("pGF_Garage_Solar_Storage_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))

            if requested_max_discharger_power is not None:
                # START/REFRESH CHARGING => Fenecon Watchdog
                Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").sendCommand(int(round(requested_max_discharger_power * 1000.0)))

        # *** CAR CHARGING
        if Registry.getItemState("pGF_Outdoor_Car_Charge_Control") == scope.ON and Registry.getItemState("pGF_Outdoor_Car_IsConnected") == scope.ON:
            self.logger.info("--------: <<<")
            self.logger.info("--------: >>>")

            requested_power = self.calculateCarChargeLevel(now, charging_start, charging_end)

            if requested_power is not None:
                Registry.getItem("pGF_Outdoor_Car_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))

        self.logger.info("--------: <<<")

#Registry.getItem("pGF_Garage_Solar_Inverter_Charge_Control").postUpdate(scope.ON)

#Registry.getItem("pGF_Outdoor_Car_EnergySoc").postUpdate(0)
#Registry.getItem("pGF_Outdoor_Car_EssSoc").postUpdate(0)
#Registry.getItem("pGF_Outdoor_Car_IsConnected").postUpdate(scope.OFF)
