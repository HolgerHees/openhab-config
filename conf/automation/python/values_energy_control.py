import json
import urllib.parse
import math

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper

import scope


#print(( Registry.getItem("pGF_Garage_Solar_Storage_Capacity").getState().doubleValue() ) / 1000.0)
STORAGE_MAX_CAPACITY = 25.2
STORAGE_EMERGENCY_ENERGY_SOC = STORAGE_MAX_CAPACITY * 0.2

MAX_STORAGE_CHARGE_POWER = STORAGE_MAX_CAPACITY * 0.2
AVG_STORAGE_CHARGE_POWER = STORAGE_MAX_CAPACITY * 0.1

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

@rule(
    triggers = [
      GenericCronTrigger("0 0 * * * ?")
#      GenericCronTrigger("*/15 * * * * ?")
    ]
)
class StockPrices:
    def __init__(self):
        #client_id = customConfigs["ostrom_api"]["client_id"]
        #client_secret = customConfigs["ostrom_api"]["client_secret"]
        #encoded_credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("ascii"))
        #hashed_credentials = hashlib.sha256(encoded_credentials).hexdigest()

        #result = subprocess.Popen("curl --request POST --url https://auth.production.ostrom-api.io/oauth2/token --header 'accept: application/json' --header 'authorization: Basic {}' --header 'content-type: application/x-www-form-urlencoded' --data #grant_type=client_credentials".format(hashed_credentials), shell=True, stdout=subprocess.PIPE).stdout.read()
        #print(result)
        #return
        #headers = {
        #    'Authorization' : 'Basic {}'.format(hashed_credentials),
        #    'Accept': 'application/json',
        #    'Content-type': 'application/x-www-form-urlencoded',
        #}
        #data = HTTP.sendHttpPostRequest("https://auth.production.ostrom-api.io/oauth2/token", "application/x-www-form-urlencoded", "grant_type=client_credentials", headers, 5000)
        #print(data)

        #for i in range(0,365):
        #    values = self.fetchValues(datetime.now().astimezone() - timedelta(days=i) )
        #    print(i)
        #    #for slot, value in values.items():
        #    #    print( str(slot) + " " + str(value))

        self.fetch_time = None

        states = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesUntil(datetime.now().astimezone() + timedelta(days=2))
        trading_date = datetime.now().astimezone()

        # no values for tomorrow are available
        if len(states) > 0:
            # tomorrow values are available
            if (states[-1].getTimestamp() - timedelta(days=1)).day == trading_date.day:
                self.fetch_time = trading_date

        #self.fetch_time = None
        #trading_date = trading_date - timedelta(days=1)
        if self.fetch_time is None:
            self.fetch_time = self.fetchValues(trading_date, logger)

    def fetchValues(self, trading_date, logger):
        if ( trading_date.day == datetime.now().day and trading_date.hour < 14 ) or (self.fetch_time is not None and self.fetch_time.day == trading_date.day):
            return self.fetch_time

        start_date = ( trading_date + timedelta(days=1) ).replace(hour=0, minute=0, second=0, microsecond=0)
        start_date_str = urllib.parse.quote_plus(start_date.isoformat().split("T")[0])

        end_date = start_date + timedelta(days=1)
        end_date_str = urllib.parse.quote_plus(end_date.isoformat().split("T")[0])

        url = "https://api.energy-charts.info/price?bzn=DE-LU&start={}&end={}".format(start_date_str,end_date_str)
        #print(url)
        #print(end_date.isoformat().split("T")[0])
        response = HTTP.sendHttpGetRequest(url, { "Accept": "application/json" }, 5000)
        #print(response)

        if response is None or response == 'no content available':
            logger.error("Epexspot price result not available yet")
            return None

        data = json.loads(response)

        timeslots = data["unix_seconds"]
        prices = data["price"]

        for i in range(0,len(timeslots)):
            timeslot = timeslots[i]
            price = prices[i]

            Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persist(datetime.fromtimestamp(timeslot), round(price / 1000, 2))

            #print("DATETIME: {}, PRICE: {}".format(datetime.fromtimestamp(timeslot), price))

        logger.info("Epexspot prices updated. COUNT: {}".format(len(timeslots)))

        return trading_date

    def execute(self, module, input):
        self.fetch_time = self.fetchValues(datetime.now().astimezone(), self.logger)

#end = datetime.now().astimezone()
#start = end - timedelta(hours=1)
#price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").averageBetween(start, end).doubleValue()
#print(price)
#prices = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesBetween(start, end + timedelta(seconds=1))
#_price = 0
#for price in prices:
#    _price += price.getState().doubleValue()
#print(str(_price/4))

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
    # def __init__(self):
    #     start = datetime.now() - timedelta(days=365)
    #     min_energy_sco = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getPersistence("jdbc").minimumSince(start)
    #
    #     start = min_energy_sco.getTimestamp()
    #
    #     supply = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").getPersistence("jdbc").deltaSince(start).doubleValue()
    #     demand = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Demand").getPersistence("jdbc").deltaSince(start).doubleValue()
    #     production = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Production").getPersistence("jdbc").deltaSince(start).doubleValue()
    #     consumption = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Consumption").getPersistence("jdbc").deltaSince(start).doubleValue()
    #
    #     total_charge = (production + demand) - ( supply + consumption )
    #     solar_charge = production - ( supply + consumption )
    #     demand_charge = demand - ( supply + consumption )
    #
    #     #print(Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").getPersistence("jdbc").persistedState(start).getState().doubleValue())
    #     #print(Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").getState().doubleValue())
    #
    #     print(supply, demand, production, supply + demand + production * 0.90, consumption)
    #
    #     print(min_energy_sco.getState().doubleValue(), min_energy_sco.getTimestamp(), total_charge, solar_charge, demand_charge)

    def execute(self, module, input):
        if input['event'].getType() == 'TimerEvent':
            start = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getLastStateChange()
            start -= timedelta(microseconds=1)
            history_item = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getPersistence("jdbc").persistedState(start)

            start = history_item.getTimestamp()
            current_battery_energy_soc = Registry.getItem("pGF_Garage_Solar_Storage_EssSoc").getState().doubleValue()

            return
        else:
            start = input['event'].getLastStateChange()
            current_battery_percent_soc = input['event'].getItemState().doubleValue()

        current_battery_energy_soc = current_battery_percent_soc * STORAGE_MAX_CAPACITY / 100.0
        current_battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        supply = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").getPersistence("jdbc").deltaSince(start).doubleValue()
        demand = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Demand").getPersistence("jdbc").deltaSince(start).doubleValue()
        production = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Production").getPersistence("jdbc").deltaSince(start).doubleValue()
        consumption = Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Consumption").getPersistence("jdbc").deltaSince(start).doubleValue()

        current_solar_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        current_grid_energy_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()

        # *** STEP 1: calculate solar charge ***
        total_charge = (production + demand) - ( supply + consumption )
        print("CALCULATION: total_charge: {}, production: {}, demand: {}, supply: {}, consumption: {}".format(total_charge, production, demand, supply, consumption))

        if total_charge > 0:
            solar_charge = production - ( supply + consumption - demand )
            print("SOLAR: solar_charge: {}".format(solar_charge))

            if solar_charge < 0:
                solar_charge = 0
            new_solar_energy_soc = current_solar_energy_soc + ( solar_charge * 0.97 ) # 3% loss
            #new_solar_energy_soc = solar_charge * 0.97 # 3% loss

            if new_solar_energy_soc > STORAGE_MAX_CAPACITY:
                new_solar_energy_soc = STORAGE_MAX_CAPACITY
        else:
            new_solar_energy_soc = current_solar_energy_soc + ( total_charge * 1.03 ) # 3% loss
            if new_solar_energy_soc < 0:
                new_solar_energy_soc = 0

        # *** STEP 2: rest is grid charge ***
        new_grid_energy_soc = current_battery_energy_soc - new_solar_energy_soc
        print("NEW_SOC: new_solar_energy_soc: {}, new_grid_energy_soc: {}".format(new_solar_energy_soc, new_grid_energy_soc))

        # *** STEP 3: grid charge is never be smaller then emergency energy level ***
        # force energy < 'STORAGE_EMERGENCY_ENERGY_SOC' to be grid charged
        if new_grid_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC:
            if new_solar_energy_soc > 0:
                diff = STORAGE_EMERGENCY_ENERGY_SOC - new_grid_energy_soc
                if diff > new_solar_energy_soc:
                    new_grid_energy_soc += new_solar_energy_soc
                    new_solar_energy_soc = 0
                else:
                    new_grid_energy_soc += diff
                    new_solar_energy_soc -= diff
            print("ADJUSTED: new_solar_energy_soc: {}, new_grid_energy_soc: {}".format(new_solar_energy_soc, new_grid_energy_soc))

        #print(new_solar_energy_soc, new_grid_energy_soc, current_solar_energy_soc)

        # *** STEP 4: Update values and calculate new grid price
        if current_solar_energy_soc != new_solar_energy_soc:
            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").postUpdate(new_solar_energy_soc)

        if current_grid_energy_soc != new_grid_energy_soc:
            # calculate new grid price
            if new_grid_energy_soc > current_grid_energy_soc:
                grid_charge = new_grid_energy_soc - current_grid_energy_soc
                ratio = grid_charge  / new_grid_energy_soc
                current_stock_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").averageSince(start).doubleValue()

                new_battery_price = ( current_battery_price * (1 - ratio) ) + ( current_stock_price * ratio )
                if current_battery_price != new_battery_price:
                    Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").postUpdate(new_battery_price)

            Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").postUpdate(new_grid_energy_soc)

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
        self.last_forecast_datetime = None
        self.expected_solar = None
        self.solar_direct_consumption = None
        self.total_consumption = None
        self.target_battery_energy_soc = None

        self.last_price_datetime = None
        self.price_map = None

    def applySolar(self, start, end):

        _start = ( datetime.now() - timedelta(days=1) ).replace(hour=0, minute=0, second=0, microsecond=0)
        _end = _start + timedelta(days=1)
        sunshine_radiations = Registry.getItem("pOutdoor_Astro_Total_Radiation").getPersistence("jdbc").getAllStatesBetween(_start, _end) # must be yesterday
        sunshine_duration_max = int( ( sunshine_radiations[-1].getTimestamp() - sunshine_radiations[0].getTimestamp() ).total_seconds() / 60 )

        sunshine_duration_today = Registry.getItem("pOutdoor_Weather_Forecast_Sunshine_Duration").getPersistence("jdbc").sumBetween(start, end).doubleValue()
        sunshine_ratio = round(sunshine_duration_today * 100 / sunshine_duration_max, 0)

        values = {
            start.replace(day=1, month=9): 60.0,
            start.replace(day=30, month=9): 25.0,
            start.replace(day=31, month=10): 15.0,
            start.replace(day=30, month=11): 10.0,
            start.replace(day=1, month=2): 10.0,
            start.replace(day=1, month=3): 15.0,
            start.replace(day=1, month=4): 25.0,
            start.replace(day=1, month=5): 60.0
        }

        start_slot = None
        start_value = 0
        end_slot = None
        end_value = 0
        for slot, value in values.items():
            if start > slot and (start_slot is None or start_slot < slot):
                start_slot = slot
                start_value = value
            else:
                end_slot = slot
                end_value = value
                break

        start_doty = int(start_slot.strftime('%j'))
        end_doty = int(end_slot.strftime('%j'))

        max_diff_days = end_doty + ( 365 - start_doty ) if end_doty < start_doty else end_doty - start_doty
        max_diff_value = end_value - start_value

        current_doty = int(start.strftime('%j'))
        current_diff_days = current_doty + ( 365 - start_doty ) if current_doty < start_doty else current_doty - start_doty

        current_diff_value = current_diff_days * max_diff_value / max_diff_days

        solar = start_value + current_diff_value

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

    def applyHeating(self, start, end):
        avg_value = Registry.getItem("pOutdoor_Weather_Forecast_Temperature").getPersistence("jdbc").averageBetween(start,end).doubleValue()

        if avg_value > HEATING_MAX_TEMPERATURE:
            heating = 0
        elif avg_value < HEATING_MIN_TEMPERATURE:
            heating = HEATING_MAX_ENERGY
        else:
            heating = ( avg_value - HEATING_MAX_TEMPERATURE ) * HEATING_MAX_ENERGY / HEATING_MAX_TEMPERATURE_DIFF

        return heating

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

    def calculateSlots(self, requested_date, prices, max_battery_charge, avg_battery_charge, missing_charge):
        max_battery_charge_per_slot = max_battery_charge / 4
        avg_battery_charge_per_slot = avg_battery_charge / 4

        charge_level = 0
        available_prices = list(prices.keys())
        used_slots = []
        min_price = max_price = available_prices[0]
        for i in range(0, len(available_prices)):
            price = max_price = available_prices[i]
            for slot in prices[price]:
                used_slots.append([price,slot])
                if slot["end"] <= requested_date:
                    continue

            charge_level = missing_charge / len(used_slots)
            if charge_level < max_battery_charge_per_slot:
                if charge_level > avg_battery_charge_per_slot and len(available_prices) > i + 1 and available_prices[i+1] <= 0.1:
                    continue
                break

        used_slots.sort(key=lambda item: item[1]["start"].timestamp()) # sort by timestamp for performance reason
        return [min_price, max_price, used_slots, charge_level * 4]

    def calculateChargeLevel(self):
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

            today_consumption = 0.0
        # calculate for today
        else:
            charging_start = sunset - timedelta(days=1)                                                                     # charging starts yesterday sunset
            charging_end = sunrise                                                                                          # charging ends today sunrise

            consumption_start = requested_date.replace(hour=0, minute=0, second=0, microsecond=0)                           # consumptions starts today 00:00
            consumption_end = consumption_start + timedelta(days=1)                                                         # consumptions starts today 23:59

            today_consumption = Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Consumption").getState().doubleValue()

        # *** CALCULATE AND CACHE SOLAR AND HEATING
        if self.last_forecast_datetime is None or self.last_forecast_datetime.hour != now.hour:
            self.expected_solar = self.applySolar(consumption_start, consumption_end)

            sunshine_in_hours = math.floor((sunset - sunrise).total_seconds() / 60.0 / 60.0)
            self.solar_direct_consumption = sunshine_in_hours * BASE_CONSUMPTION_PER_HOUR
            self.total_consumption = STORAGE_EMERGENCY_ENERGY_SOC + MAX_CONSUMPTION_PER_DAY + self.applyHeating(consumption_start, consumption_end)

            midnight = sunrise.replace(hour=0, minute=0, second=0)
            night_in_hours = math.floor((sunrise - midnight).total_seconds() / 60.0 / 60.0)
            night_base_consumption = night_in_hours * BASE_CONSUMPTION_PER_HOUR

            effective_solar = self.expected_solar - self.solar_direct_consumption if self.expected_solar > self.solar_direct_consumption else 0.0
            effective_total_consuption = self.total_consumption - self.solar_direct_consumption

            self.target_battery_energy_soc = STORAGE_MAX_CAPACITY - effective_solar if effective_total_consuption + effective_solar > STORAGE_MAX_CAPACITY else effective_total_consuption
            if self.target_battery_energy_soc < STORAGE_EMERGENCY_ENERGY_SOC + night_base_consumption:
                self.target_battery_energy_soc = STORAGE_EMERGENCY_ENERGY_SOC + night_base_consumption

            self.last_forecast_datetime = now

        #Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").postUpdate(0.1)

        price_persistance = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc")
        current_price = price_persistance.persistedState(requested_date).getState().doubleValue()
        battery_price = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Price").getState().doubleValue()

        solar_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Solar_Soc").getState().doubleValue()
        grid_battery_soc = Registry.getItem("pGF_Utilityroom_Electricity_Storage_Grid_Soc").getState().doubleValue()
        current_battery_soc = ( Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").getState().doubleValue() ) / 1000.0

        requested_power = requested_max_discharger_power = None

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

        self.logger.info("Forecast: Consumption {:.2f}kWh • Storage {:.2f}kWh • Solar {:.2f}kWh • Direct {:.2f}kWh".format(self.total_consumption, self.target_battery_energy_soc, self.expected_solar, self.solar_direct_consumption))

        # *** CALCULATE MISSING CHARGING
        state = "Inactive"
        state_msg = ""

        missing_energy = self.target_battery_energy_soc - current_battery_soc - today_consumption
        if missing_energy <= 0:
            state_msg = "No charging needed"
        else:
            # *** CALCULATE PRICES
            last_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(charging_end)
            if charging_end.day != last_price.getTimestamp().day:
                state_msg = "Prices are not available yet"
            else:
                if self.last_price_datetime != last_price.getTimestamp():
                    prices = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesBetween(charging_start, charging_end)
                    self.price_map = self.mapPrices(prices)
                    self.last_price_datetime = last_price.getTimestamp()

                # *** CALCULATE SLOTS
                min_price, max_price, used_slots, requested_power = self.calculateSlots(requested_date, self.price_map, MAX_STORAGE_CHARGE_POWER, AVG_STORAGE_CHARGE_POWER, missing_energy)
                if requested_power > MAX_STORAGE_CHARGE_POWER:
                    requested_power = MAX_STORAGE_CHARGE_POWER
                #for i in range(0, len(used_slots)):
                #    slot = used_slots[i]
                #    print(slot[0], slot[1]["start"].strftime('%d %H:%M'))
                #print(len(used_slots))

                price_msg = "{:.2f}-{:.2f}".format(min_price, max_price) if min_price != max_price else "{:.2f}".format(min_price)
                self.logger.info("          Charging between {} and {} with {:.2f}kWh for {}€ in {} slots".format(used_slots[0][1]["start"].strftime('%H:%M'), used_slots[-1][1]["end"].strftime('%H:%M'), requested_power, price_msg, len(used_slots)))

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
                    state_msg = "{} • Next slot at {}".format(state_msg, next_slot[1]["start"].strftime('%H:%M'))

        self.logger.info("        : --")
        self.logger.info("Prices  : Spot {:.2f}€ • Grid Storage {:.2f}€ • Solar Storage 0.00€".format(current_price, battery_price))
        self.logger.info("Storage : Total {:.2f}kWh • Grid {:.2f}kWh • Solar {:.2f}kWh".format(current_battery_soc,grid_battery_soc,solar_battery_soc))
        self.logger.info("        : --")
        self.logger.info("{}: {}{}".format(state, state_msg, state_suffix))
        return [requested_power, requested_max_discharger_power]

    def execute(self, module, input):
        self.logger.info("--------: >>>")
        requested_power, requested_max_discharger_power = self.calculateChargeLevel()

        if requested_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedPower").sendCommand(int(round(requested_power * 1000.0)))


        if requested_max_discharger_power is not None:
            # START/REFRESH CHARGING => Fenecon Watchdog
            Registry.getItem("pGF_Garage_Solar_Storage_RequestedMaxDischargerPower").sendCommand(requested_max_discharger_power)
        self.logger.info("--------: <<<")
