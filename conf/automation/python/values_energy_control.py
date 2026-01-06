import math

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

STORAGE_POWER_MAP = {
    0.10: 2.0, # -0.7
    0.09: 2.7, # -0.7
    0.08: 3.4, # -0.7
    0.07: 4.1, # -0.7
    0.06: 4.8, # -0.7
    0.05: 5.5, # -0.7
    0.04: 6.2, # -0.7
    0.03: 6.9, # -0.7
    0.02: 7.6, # -0.7
    0.01: 8.3, # -0.7
    0.00: 9.0, #
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
BASE_CONSUMPTION_PER_HOUR = 0.5

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

FROST_GUARD_HEATING_MAP = {
   -9.0: 18.0,
   -8.0: 16.5,
   -7.0: 15.0,
   -6.0: 13.5,
   -5.0: 12.0,
   -4.0: 10.5,
   -3.0:  9.0,
   -2.0:  7.5,
   -1.0:  6.0,
    0.0:  4.5,
    1.0:  3.0,
    2.0:  2.0,
    3.0:  1.1,
    4.0:  0.5,
    5.0:  0.0
}

#end = datetime.now().astimezone()
#start = end - timedelta(hours=1)
#price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").averageBetween(start, end).doubleValue()
#print(price)
#prices = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesBetween(start, end + timedelta(seconds=1))
#_price = 0
#for price in prices:
#    _price += price.getState().doubleValue()
#print(str(_price/4))

#print(Registry.getItemState("pGF_Utilityroom_Electricity_Stock_Price"),Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getLastStateChange())
#print(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(datetime.now().astimezone()))
#print(Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").nextState())

@rule(
    triggers = [
#      GenericCronTrigger("0 0 * * * ?")
#      GenericCronTrigger("*/30 * * * * ?") # 30 seconds, because of 60 seconds watchdoc for fenecon
#        GenericCronTrigger("*/5 * * * * ?"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Storage_EssSoc")
    ]
#    , profile_code=True
)
class StorageInfo:
    def __init__(self):
        self.demand = self.getEnergyValue("pGF_Garage_Solar_Inverter_DemandTotalEnergy")
        self.supply = self.getEnergyValue("pGF_Garage_Solar_Inverter_SupplyTotalEnergy")
        self.production = self.getEnergyValue("pGF_Garage_Solar_Inverter_ProductionTotalEnergy")
        self.consumption = self.getEnergyValue("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy")

        self.last_change = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getLastStateChange()

        #self.calculate(Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").doubleValue())

    def getEnergyValue(self, item_name):
        return Registry.getItem(item_name).getState().doubleValue() / 1000.0

    def calculate(self, current_battery_percent_soc = None):
        current_battery_energy_soc = current_battery_percent_soc * STORAGE_MAX_CAPACITY / 100.0
        current_battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        demand = self.getEnergyValue("pGF_Garage_Solar_Inverter_DemandTotalEnergy")
        demand_diff = demand - self.demand
        supply = self.getEnergyValue("pGF_Garage_Solar_Inverter_SupplyTotalEnergy")
        supply_diff = supply - self.supply
        production = self.getEnergyValue("pGF_Garage_Solar_Inverter_ProductionTotalEnergy")
        production_diff = production - self.production
        consumption = self.getEnergyValue("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy")
        consumption_diff = consumption - self.consumption

        current_solar_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        current_grid_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()

        # *** STEP 1: calculate solar charge ***
        total_charge = (production_diff + demand_diff) - ( supply_diff + consumption_diff )
        print("CALCULATION: total_charge: {}, production: {}, demand: {}, supply: {}, consumption: {}".format(total_charge, production_diff, demand_diff, supply_diff, consumption_diff))

        if total_charge > 0:
            solar_charge = production_diff - ( supply_diff + consumption_diff - demand_diff )
            if solar_charge > 0:
                print("SOLAR: solar_charge: {}".format(solar_charge))
                new_solar_energy_soc = current_solar_energy_soc + ( solar_charge * 0.97 ) # 3% loss
                if new_solar_energy_soc > STORAGE_MAX_CAPACITY:
                    new_solar_energy_soc = STORAGE_MAX_CAPACITY
        else:
            new_solar_energy_soc = current_solar_energy_soc + ( total_charge * 1.03 ) # 3% loss
            if new_solar_energy_soc < 0:
                new_solar_energy_soc = 0

        # *** STEP 2: rest is grid charge ***
        new_grid_energy_soc = current_battery_energy_soc - new_solar_energy_soc
        print("NEW_SOC: new_solar_energy_soc: {}, new_grid_energy_soc: {}".format(new_solar_energy_soc, new_grid_energy_soc))

        # *** STEP 3: grid charge is never smaller then emergency energy level ***
        if new_grid_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC:
            new_grid_energy_soc = STORAGE_EMERGENCY_ENERGY_SOC if current_battery_energy_soc >=STORAGE_EMERGENCY_ENERGY_SOC else current_battery_energy_soc
            new_solar_energy_soc = current_battery_energy_soc - new_grid_energy_soc
            print("ADJUSTED: new_solar_energy_soc: {}, new_grid_energy_soc: {}".format(new_solar_energy_soc, new_grid_energy_soc))

        # *** STEP 4: Update values and calculate new grid price
        if current_solar_energy_soc != new_solar_energy_soc:
            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").postUpdate(new_solar_energy_soc)

        if current_grid_energy_soc != new_grid_energy_soc:
            # calculate new grid price
            if new_grid_energy_soc > current_grid_energy_soc:
                grid_charge = new_grid_energy_soc - current_grid_energy_soc
                ratio = grid_charge  / new_grid_energy_soc
                current_stock_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").averageSince(self.last_change).doubleValue()
                print("STOCK PRICE: JDBC: {} DIRECT: {}".format(current_stock_price, Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getState().doubleValue()))

                new_battery_price = ( current_battery_price * (1 - ratio) ) + ( current_stock_price * ratio )
                if current_battery_price != new_battery_price:
                    Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").postUpdate(new_battery_price)

            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").postUpdate(new_grid_energy_soc)

        # *** STEP 5: confirm values
        self.demand = demand
        self.supply = supply
        self.production = production
        self.consumption = consumption
        self.last_change = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getLastStateChange()

    def execute(self, module, input):
        self.calculate(input['event'].getItemState().doubleValue())

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
        self.last_price_datetime = None
        self.price_map = None

        self.last_forecast_datetime = None
        self.expected_solar = None
        self.effective_solar = None

        self.total_consumption = None
        self.house_heating_consumption = None

        self.target_battery_energy_soc = None

    def initPrices(self, charging_start, charging_end):
        # *** CALCULATE PRICES
        last_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(charging_end)
        if charging_end.day != last_price.getTimestamp().day:
            self.price_map = None
            return

        if self.last_price_datetime != last_price.getTimestamp():
            prices = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesBetween(charging_start, charging_end)
            self.price_map = self.mapPrices(prices)
            self.last_price_datetime = last_price.getTimestamp()

    def mapPrices(self, prices):
        price_map = {}
        for price in prices:
            price_date = price.getTimestamp()
            #if price_date > sunrise and price_date < sunset:
            #    continue

            value = price.getState().doubleValue()
            if value not in price_map:
                price_map[value] = []

            price_map[value].append({"start": price_date, "end": price_date + timedelta(minutes=15)})

        for price, slots in price_map.items():
            slots.sort(key=lambda x: x["start"].timestamp(), reverse=True)

        return dict(sorted(price_map.items(), key=lambda item: item[0]))

    def calculateSlots(self, requested_date, missing_energy, price_map, power_map):
        _charging_power_list = list(power_map.values())
        min_battery_charge_per_slot = _charging_power_list[0] / 4
        max_battery_charge_per_slot = _charging_power_list[-1] / 4

        charge_level_per_slot = 0
        available_prices = list(price_map.keys())
        used_slots = []
        min_price = max_price = available_prices[0]
        for i in range(0, len(available_prices)):
            price = max_price = available_prices[i]
            for slot in price_map[price]:
                used_slots.append([price,slot])
                if slot["end"] <= requested_date:
                    continue

            charge_level_per_slot = missing_energy / len(used_slots)
            if charge_level_per_slot < max_battery_charge_per_slot:
                current_min_charging_speed_per_slot = ( power_map[price] if price in power_map else min_battery_charge_per_slot ) / 4
                #print(charge_level_per_slot,price,min_charging_speed_per_slot)
                if charge_level_per_slot > current_min_charging_speed_per_slot and len(available_prices) > i + 1 and available_prices[i+1] in power_map:
                    continue
                break

        total_price = 0
        for slot in used_slots:
            total_price += price * charge_level_per_slot

        requested_power = charge_level_per_slot * 4

        used_slots.sort(key=lambda item: item[1]["start"].timestamp()) # sort by timestamp for performance reason

        price_msg = "{:.2f}-{:.2f}".format(min_price, max_price) if min_price != max_price else "{:.2f}".format(min_price)
        self.logger.info("Charging: Between {} and {} with {:.2f}kWh for {}€ in {} slots".format(used_slots[0][1]["start"].strftime('%H:%M'), used_slots[-1][1]["end"].strftime('%H:%M'), requested_power, price_msg, len(used_slots)))

        real_total_price = ( total_price + ENERGY_TRAFFIC_COST_PER_KWH * missing_energy ) * VAT_COST
        self.logger.info("        : Price for {:.2f}kWh is {:.2f}€ • {:.2f}€/kWh (Taxes included)".format(missing_energy, real_total_price, real_total_price / missing_energy))

        return [min_price, max_price, total_price, used_slots, requested_power]

    def selectActiveSlot(self, used_slots, requested_date, requested_power, current_price, min_price, max_price, total_price, missing_energy, state, state_msg):
        #print(requested_date)
        active_slot = None
        next_slot = None
        for price, slot in used_slots:
            if active_slot is None and requested_date > slot["start"] and requested_date < slot["end"]:
                active_slot = [price, slot]

            if next_slot is None and requested_date < slot["start"]:
                next_slot = [price, slot]

            if active_slot is not None and next_slot is not None:
                break

            #print(price, slot)

        if active_slot is not None:
            is_ending = ( next_slot is None or next_slot[1]["start"] != active_slot[1]["end"] ) and requested_date >= active_slot[1]["end"] - timedelta(minutes=1)
            state = "Ending  " if is_ending else "Active  "
            state_msg = "With {:.2f}kWh for {}€".format(requested_power, current_price)
            if is_ending:
                requested_power = None
        else:
            state_msg = "No slot matches"
            requested_power = None

        if next_slot is not None:
            state_msg = "{} • Next slot at {} with {}€".format(state_msg, next_slot[1]["start"].strftime('%H:%M'), next_slot[0])

        return [state, state_msg, requested_power]

    def calculateRequestedPower(self, current_price, requested_date, missing_energy, state_suffix = ""):
        requested_power = None

        state = "Inactive"
        state_msg = ""

        if missing_energy <= 0:
            state_msg = "No charging needed"
        else:
            # *** CALCULATE PRICES
            if not self.price_map:
                state_msg = "Prices are not available yet"
            else:
                # *** CALCULATE SLOTS
                min_price, max_price, total_price, used_slots, requested_power = self.calculateSlots(requested_date, missing_energy, self.price_map, STORAGE_POWER_MAP)
                self.logger.info("        : --")

                state, state_msg, requested_power = self.selectActiveSlot(used_slots, requested_date, requested_power, current_price, min_price, max_price, total_price, missing_energy, state, state_msg)

        self.logger.info("{}: {}{}".format(state, state_msg, state_suffix))

        return requested_power

    def findValueFromMap(self, key, values):
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

    def getSolarForecast(self, start, end):
        _start = ( datetime.now() - timedelta(days=1) ).replace(hour=0, minute=0, second=0, microsecond=0)
        _end = _start + timedelta(days=1)
        sunshine_radiations = Registry.getItem("pOutdoor_Astro_Total_Radiation").getPersistence("jdbc").getAllStatesBetween(_start, _end) # must be yesterday
        sunshine_duration_max = int( ( sunshine_radiations[-1].getTimestamp() - sunshine_radiations[0].getTimestamp() ).total_seconds() / 60 )

        sunshine_duration_today = Registry.getItem("pOutdoor_Weather_Forecast_Sunshine_Duration").getPersistence("jdbc").sumBetween(start, end).doubleValue()
        sunshine_ratio = round(sunshine_duration_today * 100 / sunshine_duration_max, 0)

        values = {
            start.replace(day=1, month=2).timetuple().tm_yday: 10.0,
            start.replace(day=1, month=3).timetuple().tm_yday: 15.0,
            start.replace(day=1, month=4).timetuple().tm_yday: 25.0,
            start.replace(day=1, month=5).timetuple().tm_yday: 60.0,
            start.replace(day=1, month=9).timetuple().tm_yday: 60.0,
            start.replace(day=30, month=9).timetuple().tm_yday: 25.0,
            start.replace(day=31, month=10).timetuple().tm_yday: 15.0,
            start.replace(day=30, month=11).timetuple().tm_yday: 10.0
        }

        solar = self.findValueFromMap(start.timetuple().tm_yday, values)

        #cloud_cover = Registry.getItem("pOutdoor_Weather_Forecast_Cloud_Cover").getPersistence("jdbc").averageBetween(start, end).doubleValue()
        # more timerealistic
        #if cloud_cover > 8:
        #    solar = solar * 0.3
        #elif cloud_cover > 6:
        #    solar = solar * 0.6
        #elif cloud_cover > 5:
        #    solar = solar * 0.8
        #elif cloud_cover > 4:
        #    solar = solar * 0.9

        return solar * sunshine_ratio / 100

    def getHeatingForecast(self, start, end):
        avg_value = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getPersistence("jdbc").averageBetween(start,end).doubleValue()

        if avg_value > HEATING_MAX_TEMPERATURE:
            house_heating = 0
        elif avg_value < HEATING_MIN_TEMPERATURE:
            house_heating = HEATING_MAX_ENERGY
        else:
            house_heating = ( avg_value - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF

        frost_guard_heating = self.findValueFromMap(avg_value, FROST_GUARD_HEATING_MAP)

        return [house_heating, frost_guard_heating]

    def calculateStorageChargeLevel(self, requested_date, consumption_start, consumption_end, sunrise, sunset):
        # *** CALCULATE AND CACHE SOLAR AND HEATING
        if self.last_forecast_datetime is None or self.last_forecast_datetime.hour != requested_date.hour:
            self.expected_solar = self.getSolarForecast(consumption_start, consumption_end)

            self.house_heating_consumption, self.frost_guard_heating_consumption = self.getHeatingForecast(consumption_start, consumption_end)

            sunshine_in_hours = math.floor((sunset - sunrise).total_seconds() / 60.0 / 60.0)
            solar_direct_consumption = sunshine_in_hours * BASE_CONSUMPTION_PER_HOUR
            self.total_consumption = STORAGE_EMERGENCY_ENERGY_SOC + MAX_CONSUMPTION_PER_DAY + self.house_heating_consumption + self.frost_guard_heating_consumption

            midnight = sunrise.replace(hour=0, minute=0, second=0)
            night_in_hours = math.floor((sunrise - midnight).total_seconds() / 60.0 / 60.0)
            night_base_consumption = night_in_hours * BASE_CONSUMPTION_PER_HOUR

            self.effective_solar = self.expected_solar - solar_direct_consumption if self.expected_solar > solar_direct_consumption else 0.0
            effective_total_consuption = self.total_consumption - solar_direct_consumption

            self.target_battery_energy_soc = STORAGE_MAX_CAPACITY - self.effective_solar if effective_total_consuption + self.effective_solar > STORAGE_MAX_CAPACITY else effective_total_consuption
            if self.target_battery_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC + night_base_consumption:
                self.target_battery_energy_soc = STORAGE_EMERGENCY_ENERGY_SOC + night_base_consumption

            self.last_forecast_datetime = requested_date

        price_persistance = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc")
        current_price = price_persistance.persistedState(requested_date).getState().doubleValue()
        battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        solar_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        grid_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()
        current_battery_soc = ( Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").getState().doubleValue() ) / 1000.0

        requested_max_discharger_power = None

        # *** CALCULATE POSSIBLE DISCHARGING
        state_suffix = ""
        if current_battery_soc > STORAGE_EMERGENCY_ENERGY_SOC:
            # nicht entladen, wenn aktueller Strompreis gleich dem max Ladestrompreis ist.
            if Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue() <= 0:
                reference_price = current_price if Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").getState().intValue() == -1 else price_persistance.persistedState(requested_date + timedelta(minutes=1)).getState().doubleValue()
                if reference_price <= battery_price:
                    requested_max_discharger_power = 0
                    state_suffix = " • {}".format("Limit discharging • Stock price cheaper")
                else:
                    state_suffix = " • {}".format("Discharging allowed • Storage price cheaper")
                #print(reference_price, battery_price)
            else:
                state_suffix = " • {}".format("Discharging allowed • Solar energy available")

        self.logger.info("Forecast: Emergency {:.2f}kWh • Base {:.2f}kWh, Heating {:.2f}kWh • Plants {:.2f}kWh".format(STORAGE_EMERGENCY_ENERGY_SOC, MAX_CONSUMPTION_PER_DAY, self.house_heating_consumption, self.frost_guard_heating_consumption))
        self.logger.info("        : Total {:.2f}kWh • Battery Target {:.2f}kWh, Expected Solar {:.2f}kWh ({:.2f}kWh)".format(self.total_consumption, self.target_battery_energy_soc, self.effective_solar, self.expected_solar))



        self.logger.info("        : --")
        self.logger.info("Storage : Total {:.2f}kWh • Spot price {:.2f}€/kWh".format(current_battery_soc, current_price))
        self.logger.info("        : Grid {:.2f}kWh ({:.2f}€/kWh) • Solar {:.2f}kWh".format(grid_battery_soc, battery_price, solar_battery_soc))
        #self.logger.info("State   : Spot price {:.2f}€ • Grid storage price {:.2f}€ • Solar storage price 0.00€".format(current_price, battery_price))
        #self.logger.info("        : Total storage {:.2f}kWh • Grid storage {:.2f}kWh • Solar storage {:.2f}kWh".format(current_battery_soc, grid_battery_soc, solar_battery_soc))
        self.logger.info("        : --")

        # *** CALCULATE MISSING CHARGING
        today_consumption = 0.0 if requested_date > sunrise else Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Consumption").getState().doubleValue()
        missing_energy = self.target_battery_energy_soc - current_battery_soc - today_consumption

        return [ self.calculateRequestedPower(current_price, requested_date, missing_energy, state_suffix), requested_max_discharger_power]

    def calculateCarChargeLevel(self, requested_date):
        current_battery_soc = 0.0
        max_battery_soc = 50.0

        current_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(requested_date).getState().doubleValue()

        self.logger.info("Storage : Total {:.2f}kWh • Max {:.2f}kWh".format(current_battery_soc,max_battery_soc))
        self.logger.info("        : --")

        # *** CALCULATE MISSING CHARGING
        missing_energy = max_battery_soc - current_battery_soc

        return self.calculateRequestedPower(current_price, requested_date, missing_energy)

    def execute(self, module, input):
        self.logger.info("--------: >>>")

        # *** INIT DATES
        now = datetime.now().astimezone()
        requested_date = now #.replace(day=11)

        sunrise = Registry.getItem("pOutdoor_Astro_Sunrise_Time").getState().getZonedDateTime()
        sunrise = sunrise.replace(day=requested_date.day, month=requested_date.month, year=requested_date.year)

        sunset = Registry.getItem("pOutdoor_Astro_Sunset_Time").getState().getZonedDateTime()
        sunset = sunset.replace(day=requested_date.day, month=requested_date.month, year=requested_date.year)

        # calculate for tomorrow
        if requested_date > sunrise:
            charging_start = sunset                                                                                         # charging starts today sunset
            charging_end = sunrise + timedelta(days=1)                                                                      # charging ends tomorrow sunrise

            consumption_start = (requested_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)     # consumptions starts tomorrow 00:00
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions starts tomorrow 23:59
        # calculate for today
        else:
            charging_start = sunset - timedelta(days=1)                                                                     # charging starts yesterday sunset
            charging_end = sunrise                                                                                          # charging ends today sunrise

            consumption_start = requested_date.replace(hour=0, minute=0, second=0, microsecond=0)                           # consumptions starts today 00:00
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions starts today 23:59

        # *** INIT PRICES
        self.initPrices(charging_start, charging_end)

        #self.logger.info("--- BATTERY CHARGING ---")
        requested_power, requested_max_discharger_power = self.calculateStorageChargeLevel(requested_date, consumption_start, consumption_end, sunrise, sunset)

        if requested_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))


        if requested_max_discharger_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").sendCommand(requested_max_discharger_power)

        #self.logger.info("")
        #self.logger.info("--- CAR CHARGING ---")
        #requested_power = self.calculateCarChargeLevel(requested_date)
        #if requested_power is not None:
        #    pass

        self.logger.info("--------: <<<")

# TODO mindestens 2.52KW (10%) Platz für Solar
