import math
import json

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper

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
STORAGE_MIN_CHARGING_POWER = 1.0

STORAGE_POWER_MAP = {
    0.10: 3.0, #
    0.09: 3.2, # +0.2
    0.08: 3.5, # +0.3
    0.07: 3.9, # +0.4
    0.06: 4.4, # +0.5
    0.05: 5.0, # +0.6
    0.04: 5.7, # +0.7
    0.03: 6.5, # +0.8
    0.02: 7.4, # +0.9
    0.01: 8.4, # +1.0
    0.00: 9.5, # +1.1
}

CAR_POWER_MAP = {
    0.10:  6.00,
    0.09:  7.00,
    0.08:  7.00,
    0.07:  8.00,
    0.06:  8.00,
    0.05:  9.00,
    0.04:  9.00,
    0.03: 10.00,
    0.02: 10.10,
    0.01: 11.00,
    0.00: 11.00,
}

MAX_CONSUMPTION_PER_DAY = 25.0
BASE_NIGHT_CONSUMPTION_PER_HOUR = 0.5
BASE_DAY_CONSUMPTION_PER_HOUR = 1.0

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
#      GenericCronTrigger("0 0 * * * ?")
#      GenericCronTrigger("*/30 * * * * ?") # 30 seconds, because of 60 seconds watchdoc for fenecon
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
            new_solar_energy_soc = 0
        elif new_solar_energy_soc > STORAGE_MAX_CAPACITY - STORAGE_EMERGENCY_ENERGY_SOC:
            new_solar_energy_soc = STORAGE_MAX_CAPACITY - STORAGE_EMERGENCY_ENERGY_SOC

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

#Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").postUpdate(0.0)
#Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").postUpdate(5.04)

@rule(
    triggers = [
#      GenericCronTrigger("0 0 * * * ?")
      GenericCronTrigger("*/30 * * * * ?") # 30 seconds, because of 60 seconds watchdoc for fenecon
#      GenericCronTrigger("*/5 * * * * ?")
    ]
#    , profile_code=True
)
class StoragePower:
    def __init__(self):
        self.last_price_day = -1
        self.price_map = None

        self.last_solar_hour = -1
        self.today_solar_forceast = None
        self.tomorrow_solar_forceast = None

        self.last_heating_hour = -1
        self.house_heating_forecast = None
        self.frost_guard_heating_forecast = None

    def initPrices(self, start, end):
        if self.last_price_day != end.day:
            #print("initPrices")
            # *** CALCULATE PRICES
            last_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(end)
            if end.day != last_price.getTimestamp().day:
                self.price_map = None
                return

            _mapped_prices = list(STORAGE_POWER_MAP.keys())
            _first_mapped_price = _mapped_prices[0]
            _first_mapped_power = STORAGE_POWER_MAP[_first_mapped_price]
            _last_mapped_price = _mapped_prices[-1]
            _last_mapped_power = STORAGE_POWER_MAP[_last_mapped_price]

            prices = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesBetween(start, end)
            price_map = {}
            for price in prices:
                value = price.getState().doubleValue()

                if value not in price_map:
                    price_map[value] = []

                charging_power = STORAGE_POWER_MAP[value] if value in STORAGE_POWER_MAP else (_first_mapped_power if value > _first_mapped_price else _last_mapped_power)
                price_date = price.getTimestamp()
                price_map[value].append({"start": price_date, "end": price_date + timedelta(minutes=15), "charging_power": charging_power})

            for price, slots in price_map.items():
                slots.sort(key=lambda x: x["start"].timestamp(), reverse=True)

            self.price_map = dict(sorted(price_map.items(), key=lambda item: item[0]))
            self.last_price_day = last_price.getTimestamp().day

    def initSolarForecast(self, now, start, end):
        if self.last_solar_hour != now.hour:
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

    def _findValueFromMap(self, key, values):
        slot_key = None
        slot_value = None
        for _slot_key, _slot_value in values.items():
            if slot_value is None or key > _slot_key:
                slot_key = _slot_key
                slot_value = _slot_value
            elif key < _slot_key:
                max_diff_key = _slot_key - slot_key
                max_diff_value = _slot_value - slot_value

                diff_key = key - slot_key

                slot_value += (max_diff_value * (diff_key / max_diff_key))
                break
        return slot_value

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

            frost_guard_heating = self._findValueFromMap(avg_value, FROST_GUARD_HEATING_MAP)

            self.house_heating_forecast = house_heating
            self.frost_guard_heating_forecast = frost_guard_heating
            self.last_heating_hour = now.hour

    def calculateRemainingSlots(self, now, consumption_start, missing_energy, price_map):
        used_slots_start = (now if now < consumption_start else consumption_start).timestamp()
        used_slots_charged_energy = remaining_slots_charged_energy = 0
        remaining_slots = []

        for price in list(price_map.keys()):
            for slot in price_map[price]:
                if slot["end"].timestamp() <= used_slots_start: # used slots are calculated between charging start and charging end and are reduced until consumption start (midnight)
                    continue

                used_slots_charged_energy += slot["charging_power"] / 4

                if slot["end"].timestamp() > now.timestamp(): # remaining slots are calculated across all used slots between now until charging end
                    remaining_slots_charged_energy += slot["charging_power"] / 4
                    remaining_slots.append({ "price": price, "charging_power": slot["charging_power"], "start": slot["start"], "end": slot["end"]})

            if used_slots_charged_energy >= missing_energy:
                break

        active_slot = next_slot = None
        if len(remaining_slots) > 0:
            min_power = remaining_slots[-1]["charging_power"]
            max_power = remaining_slots[0]["charging_power"]
            min_price = remaining_slots[0]["price"]
            max_price = remaining_slots[-1]["price"]

            if remaining_slots_charged_energy >= missing_energy:
                # If price is does not matter, distribute the load across all remaining slots with "fixed" power
                override_power = round(min_power - ( remaining_slots_charged_energy - missing_energy ) / len(price_map[max_price]), 2)
                if override_power < STORAGE_MIN_CHARGING_POWER:
                    override_power = STORAGE_MIN_CHARGING_POWER
                if min_power == max_power:
                    max_power = override_power
                min_power = override_power
                override_price = max_price
                charged_enery = missing_energy
            else:
                override_price = override_power = None
                charged_enery = remaining_slots_charged_energy

            remaining_slots.sort(key=lambda item: item["start"].timestamp()) # sort by timestamp for performance reason

            hours, remainder = divmod(len(remaining_slots) * 900, 3600)
            minutes, _ = divmod(remainder, 60)

            power_msg = "{:.2f}-{:.2f}".format(min_power, max_power) if min_power != max_power else "{:.2f}".format(min_power)
            price_msg = "{:.2f}-{:.2f}".format(min_price, max_price) if min_price != max_price else "{:.2f}".format(min_price)
            self.logger.info("Charging: 🔋 Total {:.2f}kWh ⚡ Power {}kW 💰 Price {}€/kWh 🕐 Between {} and {} • Duration {:02d}:{:02d} ({} slots)".format(charged_enery, power_msg, price_msg, remaining_slots[0]["start"].strftime('%H:%M'), remaining_slots[-1]["end"].strftime('%H:%M'), hours, minutes, len(remaining_slots)))
            self.logger.info("        : --")

            next_slot = remaining_slots[0] if len(remaining_slots) > 0 else None
            active_slot = next_slot if next_slot is not None and now >= next_slot["start"] else None
            if active_slot is not None:
                next_slot = remaining_slots[1] if len(remaining_slots) > 1 else None
                if override_price  is not None and override_price == active_slot["price"]:
                    active_slot["charging_power"] = override_power

            if next_slot is not None and override_price  is not None and override_price == next_slot["price"]:
                next_slot["charging_power"] = override_power

        return [active_slot, next_slot]

    def calculateRequestedPower(self, now, consumption_start, missing_energy, state_suffix = ""):
        requested_power = None
        state = "Inactive"

        if missing_energy <= 0:
            state_msg = "No charging needed"
        elif self.price_map is None:
            state_msg = "Prices are not available yet"
        else:
            active_slot, next_slot = self.calculateRemainingSlots(now, consumption_start, missing_energy, self.price_map)
            if active_slot is not None:
                requested_power = active_slot["charging_power"]
                if ( next_slot is None or next_slot["start"] != active_slot["end"] ) and now >= active_slot["end"] - timedelta(minutes=1):
                    state = "Ending  "
                    requested_power = None # if it ends in one minute, reset the requested power to trigger the inverter's watchdog timer within one minute
                else:
                    state = "Active  "
                state_msg = "With {:.2f}kWh for {:.2f}€/kWh".format(active_slot["charging_power"], active_slot["price"])
            else:
                state_msg = "No slot matches"

            if next_slot is not None:
                state_msg = "{} • Next slot at {} with {:.2f}kWh for {:.2f}€/kWh".format(state_msg, next_slot["start"].strftime('%H:%M'), next_slot["charging_power"], next_slot["price"])
        self.logger.info("{}: {}{}".format(state, state_msg, state_suffix))

        return requested_power

    def calculateStorageChargeLevel(self, now, consumption_start, consumption_end, sunrise, sunset):
        price_persistance = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc")
        current_price = price_persistance.persistedState(now).getState().doubleValue()
        battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        solar_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        grid_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()
        current_battery_soc = ( Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").getState().doubleValue() ) / 1000.0
        current_battery_percent = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getState().intValue()

        today_consumption = Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Consumption").getState().doubleValue()
        today_production = Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Production").getState().doubleValue()

        # *** CALCULATE AND CACHE SOLAR AND HEATING
        already_consumed = today_consumption if now >= consumption_start else 0.0

        expected_total_consumption = MAX_CONSUMPTION_PER_DAY + self.house_heating_forecast + self.frost_guard_heating_forecast
        expected_solar_production = self.today_solar_forceast if now >= consumption_start else self.tomorrow_solar_forceast

        _sunshine_in_hours = math.floor((sunset - sunrise).total_seconds() / 60.0 / 60.0)
        expected_consumption_during_sunshine = _sunshine_in_hours * BASE_DAY_CONSUMPTION_PER_HOUR

        _midnight = sunrise.replace(hour=0, minute=0, second=0)
        _night_in_hours = math.floor((sunrise - _midnight).total_seconds() / 60.0 / 60.0)
        expected_consumption_during_night = _night_in_hours * BASE_NIGHT_CONSUMPTION_PER_HOUR

        soc_relevant_solar = expected_solar_production - expected_consumption_during_sunshine if expected_solar_production > expected_consumption_during_sunshine else 0.0
        soc_relevant_consumption = expected_total_consumption - expected_consumption_during_sunshine - already_consumed

        is_too_much = STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_consumption + soc_relevant_solar > STORAGE_MAX_CAPACITY
        target_battery_energy_soc = STORAGE_MAX_CAPACITY - soc_relevant_solar if is_too_much else STORAGE_EMERGENCY_ENERGY_SOC + soc_relevant_consumption
        if target_battery_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night:
            target_battery_energy_soc = STORAGE_EMERGENCY_ENERGY_SOC + expected_consumption_during_night
        target_percent = target_battery_energy_soc * 100 / STORAGE_MAX_CAPACITY

        self.logger.info("Forecast: 🏠 Base {:.2f}kWh 🔥 Heating {:.2f}kWh 🌳 Plants {:.2f}kWh 🌞 Solar {:.2f}kWh (soc relevant {:.2f}kWh)".format(MAX_CONSUMPTION_PER_DAY, self.house_heating_forecast, self.frost_guard_heating_forecast, expected_solar_production, soc_relevant_solar))
        self.logger.info("        : 🏠 Total demand {:.2f}kWh 🔋 Battery target {:.2f}kWh ({:.0f}%) ({})".format(expected_total_consumption, target_battery_energy_soc, target_percent, "max capacity - soc relevant solar" if is_too_much else "emergency + consumption"))
        self.logger.info("        : --")

        self.logger.info("Current : 🔋 Battery {:.2f}kWh ({:.0f}%) • {:.2f}kWh ({:.2f}€/kWh) • {:.2f}kWh (0.00€/kWh)".format(current_battery_soc, current_battery_percent, grid_battery_soc, battery_price, solar_battery_soc))
        self.logger.info("        : 💰 Spot price {:.2f}€/kWh 🏠 Consumption {:.2f}kWh 🌞 Solar {:.2f}kWh (expected {:.2f}kWh)".format(current_price, today_consumption, today_production, self.today_solar_forceast))
        self.logger.info("        : --")

        # *** CALCULATE MISSING CHARGING
        missing_energy = target_battery_energy_soc - current_battery_soc

        # *** CALCULATE POSSIBLE DISCHARGING
        requested_max_discharger_power = None
        if current_battery_soc > STORAGE_EMERGENCY_ENERGY_SOC:
            # nicht entladen, wenn aktueller Strompreis gleich dem max Ladestrompreis ist.
            if Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue() <= 0:
                reference_price = current_price if Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").getState().intValue() == -1 else price_persistance.persistedState(now + timedelta(minutes=1)).getState().doubleValue()
                if reference_price <= battery_price:
                    requested_max_discharger_power = 0
                    state_suffix = " • {}".format("Limit discharging • Stock price cheaper")
                else:
                    state_suffix = " • {}".format("Discharging allowed • Storage price cheaper")
            else:
                state_suffix = " • {}".format("Discharging allowed • Solar energy available")
        else:
            state_suffix = " • {}".format("Limit discharging • No energy available")

        return [ self.calculateRequestedPower(now, consumption_start, missing_energy, state_suffix), requested_max_discharger_power]

    def calculateCarChargeLevel(self, now, consumption_start):
        current_battery_soc = 0.0
        max_battery_soc = 50.0

        current_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(now).getState().doubleValue()


        self.logger.info("Storage : Total {:.2f}kWh • Max {:.2f}kWh".format(current_battery_soc,max_battery_soc))
        self.logger.info("        : --")

        # *** CALCULATE MISSING CHARGING
        missing_energy = max_battery_soc - current_battery_soc

        return self.calculateRequestedPower(now, consumption_start, missing_energy)

    def execute(self, module, input):
        self.logger.info("--------: >>>")

        # *** INIT DATES
        now = datetime.now().astimezone() #.replace(hour=2, minute=30) # - timedelta(days=1)

        today_morning = now.replace(hour=0, minute=0, second=0, microsecond=0)

        sunrise = Registry.getItem("pOutdoor_Astro_Sunrise_Time").getState().getZonedDateTime()
        sunrise = sunrise.replace(day=now.day, month=now.month, year=now.year)

        sunset = Registry.getItem("pOutdoor_Astro_Sunset_Time").getState().getZonedDateTime()
        sunset = sunset.replace(day=now.day, month=now.month, year=now.year)

        # calculate for tomorrow
        if now > sunrise:
            charging_start = sunset                                                                                         # charging starts today sunset
            charging_end = sunrise + timedelta(days=1)                                                                      # charging ends tomorrow sunrise

            consumption_start = today_morning + timedelta(days=1)                                                           # consumptions starts tomorrow 00:00
        # calculate for today
        else:
            charging_start = sunset - timedelta(days=1)                                                                     # charging starts yesterday sunset
            charging_end = sunrise                                                                                          # charging ends today sunrise

            consumption_start = today_morning                                                                               # consumptions starts today 00:00

        consumption_end = consumption_start + timedelta(days=1)                                                             # consumptions ends

        #print(now, charging_start, charging_end)

        # *** INIT
        self.initPrices(charging_start, charging_end)
        self.initSolarForecast(now, today_morning, today_morning + timedelta(days=2))
        self.initHeatingForecast(now, consumption_start, consumption_end)

        #self.logger.info("--- BATTERY CHARGING ---")
        requested_power, requested_max_discharger_power = self.calculateStorageChargeLevel(now, consumption_start, consumption_end, sunrise, sunset)

        if requested_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))


        if requested_max_discharger_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").sendCommand(requested_max_discharger_power)

        #self.logger.info("")
        #self.logger.info("--- CAR CHARGING ---")
        #requested_power = self.calculateCarChargeLevel(now, consumption_start)
        #if requested_power is not None:
        #    pass

        self.logger.info("--------: <<<")
