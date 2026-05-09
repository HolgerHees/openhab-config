import json
import urllib.parse
import threading
import subprocess

from datetime import datetime, timedelta

from org.openhab.core.types import TimeSeries

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger

from custom.suncalculation import SunRadiation

from configuration import customConfigs

from scope import actions

astroAction = actions.get("astro","astro:sun:local")

solar_map = {
    SunRadiation.DIRECTION_EAST: { "power": 8.90, "azimut": 90.0, "elevation": 45.0, "coefficient": 0.29 },
    SunRadiation.DIRECTION_SOUTH: { "power": 5.44, "azimut": 180.0, "elevation": 25.0, "coefficient": 0.38 }, # 12 x 0.41 & 4 x 0.29
    SunRadiation.DIRECTION_WEST: { "power": 4.45, "azimut": 270.0, "elevation": 45.0, "coefficient": 0.29 }
}

# https://www-solisinverters-com.translate.goog/global/documentation/Influence_of_Azimuth_and_Tilt_on_Yield_of_PV_System_11281117.html?_x_tr_sl=en&_x_tr_tl=de&_x_tr_hl=de&_x_tr_pto=rq
azimut_diff_reduction_map = {
     0: 0.0,
    15: 0.7,
    30: 2.8,
    45: 6.2,
    60: 10.4,
    75: 15.6,
    90: 21.3
}

elevation_reduction_map = {
    0: 15.2,
    10: 8.2,
    20: 3.4,
    30: 0.6,
    40: 0.1,
    50: 1.9,
    60: 5.8,
    70: 11.9,
    80: 19.8,
    90: 29.4
}

"""okta_reduction_map = {
    0:  0.0,
    1:  5.0,  # 10.0,
    2: 17.0,  # 20.0,
    3: 20.0,  # 30.0,
    4: 29.0,  # 40.0,
    5: 39.0,  # 50.0,
    6: 50.0,  # 60.0,
    7: 62.0,  # 70.0,
    8: 75.0,  # 80.0,
    9: 90.0   # 90.0,
}"""

@rule(
    triggers = [
      GenericCronTrigger("0 6 * * * ?") # weather data are fetched every hour at 5 past
#      GenericCronTrigger("*/15 * * * * ?")
    ]
)
class ExpectedSolar:
    def __init__(self):
        self.check(logger)
        #self.fetch(logger)
        pass

    def check(self, logger):
        now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        rebuild = False
        if rebuild:
            start = now.replace(day=1, month=1)
            end = now + timedelta(days=2)
        else:
            #now = now - timedelta(days=1)
            start = now
            end = now + timedelta(days=1)

        self.calculateDumpedValues(rebuild, logger, start, end)

        #total = 0
        #dumped_states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").getAllStatesBetween(start, end)
        #for dumped_state in dumped_states:
        #    total += dumped_state.getState().doubleValue()
        #    print(dumped_state.getTimestamp(), dumped_state.getState().doubleValue())
        #print(total)

    def getIntersectionValue(self, value_map, current_value):
        range_start = None
        range_end = None
        for item in value_map.items():
            if item[0] <= current_value:
                range_start = item
            else:
                range_end = item
                break
        if range_end is None:
            range_end = range_start

        current_value_ratio = (current_value - range_start[0]) * 100 / (range_end[0] - range_start[0]) if range_end[0] != range_start[0] else 0
        current_factor = range_start[1] + ((range_end[1] - range_start[1]) * current_value_ratio / 100)

        return (100 - current_factor) / 100

    def calculateExpectedValue(self, direction, start_time, end_time, direct_radiation, diffuse_radiation, temperature):
        duration = (end_time - start_time).total_seconds()
        mid_time = start_time + timedelta(seconds=int(duration/2))

        # *** EFFICIENCE BASED ON TEMPERATURE ***
        efficienceInPercent = (25.0 - temperature) * solar_map[direction]["coefficient"]
        efficienceFactor = 1 + efficienceInPercent / 100

        # *** DIRECT RADIATION ***
        direct_max_power = solar_map[direction]["power"] * direct_radiation / 984       # is the ration between max radiation (984W/m²) and today direct radiation => https://www.sonnenverlauf.de/#/52.3547,13.6254,14/2026.06.21/12:59/1/3
        direct_max_power = direct_max_power * duration / 3600                           # convert direct_max_power (hour based) to direct_max_power (duration based)

        elevation_factor, azimut = SunRadiation.getElevationFactor(mid_time, direction)

        elevation_reduction_factor = self.getIntersectionValue(elevation_reduction_map, solar_map[direction]["elevation"])
        azimut_reduction_factor = self.getIntersectionValue(azimut_diff_reduction_map, abs(solar_map[direction]["azimut"] - azimut))

        active_direct_radiation = direct_max_power * elevation_reduction_factor * azimut_reduction_factor * elevation_factor * efficienceFactor

        # *** DIFFUSE RADIATION ***
        diffuse_max_power = solar_map[direction]["power"] * diffuse_radiation / 984     # max solar power * max radiation factor
        diffuse_max_power = diffuse_max_power * duration / 3600                         # convert diffuse_max_power (hour based) to diffuse_max_power (duration based)

        active_diffuse_radiation = diffuse_max_power * efficienceFactor

        return active_direct_radiation + active_diffuse_radiation

        """current_max_radiation = astroAction.getTotalRadiation(mid_time).doubleValue()
        current_max_radiation_factor = ( current_max_radiation * 100 / max_radiation ) / 100    # is the ration between max radiation (1000W/m²) and today max radiation

        # *** SUN CALCULATION
        current_max_power = solar_map[direction]["power"] * current_max_radiation_factor   # max solar power * max radiation factor
        current_max_power = current_max_power * duration / 3600                       # convert current_max_power (hour based) to current_max_power (duration based)

        elevation_reduction_factor = self.getIntersectionValue(elevation_reduction_map, solar_map[direction]["elevation"])
        current_max_power = current_max_power * elevation_reduction_factor            # reduction based on non optimal panel elevation

        azimut_reduction_factor = self.getIntersectionValue(azimut_diff_reduction_map, abs(solar_map[direction]["azimut"] - azimut))
        current_max_power = current_max_power * azimut_reduction_factor               # reduction based on diff between sun azimut and panel azimut

        current_max_power = current_max_power * elevation_factor                      # reduction based on horizon

        sunshine_ratio = sunshine_duration / 60
        current_solar_power = current_max_power * sunshine_ratio                      # current_power only during sunshine

        # *** CLOUD CALCULATION
        current_max_power = solar_map[direction]["power"] * current_max_radiation_factor  # max solar power * max radiation factor
        current_max_power = current_max_power * duration / 3600                       # convert current_max_power (hour based) to current_max_power (duration based)

        cloud_reduction_factor = self.getIntersectionValue(okta_reduction_map, cloud_okta)
        current_cloud_power = current_max_power * cloud_reduction_factor     # current_power only during sunshine
        #if ( weather_code not in [91,92,93,94,95,96,97,98,99]            # Gewitter
        #     or weather_code not in [90,81,82,83,84,85,86,87,88,89,90]   # Schauer
        #     or weather_code not in [70,71,72,73,74,75,76,77,78,79]      # Schnee
        #     or weather_code not in [61,62,63,64,65,66,67,68,69]         # Regen (excl. 60)
        #     or weather_code not in [51,52,53,54,55,56,57,58,59]         # Sprühregen (excl. 50)
        #     or weather_code not in [40,41,42,43,44,45,46,47,48,49]      # Nebel
        #     or weather_code not in [30,31,32,33,34,35,36,37,38,39]      # Staubsturm, Sandsturm, Schneefegen
        #     or weather_code not in [20,21,22,23,24,25,26,27,28,29]      # nach Sprühregen, Rege, Schnee etc.
        #     or weather_code not in [10,11,12]                           # Trockenereignisse (excl. 13,14,15,16,17,18,19
        #     or weather_code not in [4,5,6,7,8,9]                        # Dunst, Rauch, Staub oder Sand (excl. 0,1,2,3,4)
        #   ):

        return current_solar_power + current_cloud_power"""

    def calculateDumpedValues(self, persist, logger, start, end):
        total_expected = 0

        #max_radiation = astroAction.getTotalRadiation(start.replace(day=21, month=6, hour=13, minute=0, second=0)).doubleValue()

        #sunshine_states = Registry.getItem("pOutdoor_WeatherService_Sunshine_Duration").getPersistence("jdbc").getAllStatesBetween(start,end)
        #cloud_states = Registry.getItem("pOutdoor_WeatherService_Cloud_Cover").getPersistence("jdbc").getAllStatesBetween(start,end)

        end = end - timedelta(microseconds=1) # needed to exclude ending slot from the upcomming day

        direct_radiation_states = Registry.getItem("pOutdoor_WeatherService_Direct_Radiation").getPersistence("jdbc").getAllStatesBetween(start,end)
        diffuse_radiation_states = Registry.getItem("pOutdoor_WeatherService_Diffuse_Radiation").getPersistence("jdbc").getAllStatesBetween(start,end)
        temperature_states = Registry.getItem("pOutdoor_WeatherService_Temperature").getPersistence("jdbc").getAllStatesBetween(start,end)

        states = {"east": TimeSeries(TimeSeries.Policy.ADD), "south": TimeSeries(TimeSeries.Policy.ADD), "west": TimeSeries(TimeSeries.Policy.ADD)}
        for i in range(0, len(direct_radiation_states)):
            #sunshine_state = sunshine_states[i]
            #sunshine_duration = sunshine_state.getState().doubleValue()
            #cloud_okta = cloud_states[i].getState().doubleValue()
            timeslot = direct_radiation_states[i].getTimestamp()
            direct_radiation = direct_radiation_states[i].getState().intValue()
            diffuse_radiation = diffuse_radiation_states[i].getState().intValue()
            temperature = temperature_states[i].getState().doubleValue()

            for i in [0, 15, 30, 45]:
                start_time = timeslot + timedelta(minutes=i)
                if start_time > end:
                    continue
                end_time = start_time + timedelta(minutes=15)

                east_expected = self.calculateExpectedValue( SunRadiation.DIRECTION_EAST, start_time, end_time, direct_radiation, diffuse_radiation, temperature)
                states["east"].add(start_time, east_expected)
                south_expected = self.calculateExpectedValue(SunRadiation.DIRECTION_SOUTH, start_time, end_time, direct_radiation, diffuse_radiation, temperature)
                states["south"].add(start_time, south_expected)
                west_expected = self.calculateExpectedValue(SunRadiation.DIRECTION_WEST, start_time, end_time, direct_radiation, diffuse_radiation, temperature)
                states["west"].add(start_time, west_expected)

                total_expected += east_expected + south_expected + west_expected

        if persist:
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").persist(states["east"])
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_South").getPersistence("jdbc").persist(states["south"])
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").persist(states["west"])

        logger.info("TOTAL EXPECTED: {} - START: {}, END: {}".format(total_expected, start, end))

    def execute(self, module, input):
        start = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(days=2)

        self.calculateDumpedValues(True, logger, start, end)

@rule(
    triggers = [
      GenericCronTrigger("0 0 * * * ?")
#      GenericCronTrigger("*/15 * * * * ?")
    ]
)
class StockPrices:
    def __init__(self):
        """CLIENT_ID = ""
        CLIENT_SECRET = ""

        ACCESS_TOKEN_URL = "https://identity.netztransparenz.de/users/connect/token"

        cmd = "curl --request POST --url '{}' --header 'accept: application/json' --header 'content-type: application/x-www-form-urlencoded' --data grant_type='client_credentials' --data 'client_id={}' --data 'client_secret={}'".format(ACCESS_TOKEN_URL, CLIENT_ID, CLIENT_SECRET)
        print(cmd)
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        data = json.loads(result)
        print(data)

        token = data["access_token"]

        DATA_URL = "https://ds.netztransparenz.de/api/v1/data/Spotmarktpreise/2026-01-22T23:45:00/2026-01-23T23:45:00/"
        cmd = "curl --url '{}' --header 'accept: application/json' --header 'authorization: Bearer {}'".format(DATA_URL, token)
        print(cmd)
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        print(result)"""

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
        #    values = self.fetch(datetime.now().astimezone() - timedelta(days=i) )
        #    print(i)
        #    #for slot, value in values.items():
        #    #    print( str(slot) + " " + str(value))

        last_price = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persistedState(datetime.now().astimezone() + timedelta(days=2))
        if last_price:
            self.last_date = last_price.getTimestamp()

        self.fetch(logger)

    def fetchData(self, now, logger):
        logger.info("Epexspot price fetching started")

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        start_date = ( self.last_date + timedelta(minutes=15) if self.last_date is not None else today_start )
        start_date_str = urllib.parse.quote_plus(start_date.isoformat().split("T")[0])

        end_date = today_start + timedelta(days=2)
        end_date_str = urllib.parse.quote_plus(end_date.isoformat().split("T")[0])

        url = "https://api.energy-charts.info/price?bzn=DE-LU&start={}&end={}".format(start_date_str,end_date_str)
        response = HTTP.sendHttpGetRequest(url, { "Accept": "application/json" }, 10000)
        #print(url)
        #print(response)

        if response is None or response == 'no content available':
            if now.hour > 15:
                logger.error("Epexspot price response is not valid")
                self.last_date = None
            return

        try:
            data = json.loads(response)
        except ValueError:
            data = None

        if data is None:
            logger.error("Epexspot price response is not valid".format(name))
            logger.error(url)
            logger.error(response)
            return

        timeslots = data["unix_seconds"]
        prices = data["price"]

        for i in range(0,len(timeslots)):
            timeslot = datetime.fromtimestamp(timeslots[i]).astimezone().replace(microsecond=0)
            price = prices[i]

            Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persist(timeslot, round(price / 1000, 2))

        logger.info("Epexspot prices updated. COUNT: {}".format(len(timeslots)))

        self.last_date = datetime.fromtimestamp(timeslots[-1]).astimezone().replace(microsecond=0)

    def fetch(self, logger):
        now = datetime.now().astimezone()
        max_date = now + timedelta(days=1)

        # skip if
        # 1. last_date == tomorrow => we already have all data
        # 2. last_date == today and current < 2pm
        if self.last_date is not None and ( self.last_date.day == max_date.day or ( self.last_date.day == now.day and now.hour < 14 ) ):
            logger.info("Epexspot price fetching skipped")
            return

        threading.Thread(target=self.fetchData, args=(now, logger,)).start()

    def execute(self, module, input):
        self.fetch(self.logger)
