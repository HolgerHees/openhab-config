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
    SunRadiation.DIRECTION_EAST: { "power": 8.90, "azimut": 90.0, "elevation": 45.0 },
    SunRadiation.DIRECTION_SOUTH: { "power": 5.44, "azimut": 180.0, "elevation": 25.0 },
    SunRadiation.DIRECTION_WEST: { "power": 4.45, "azimut": 270.0, "elevation": 45.0 }
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

okta_reduction_map = {
    0:  0.0,
    1: 10.0,
    2: 20.0,
    3: 30.0,
    4: 40.0,
    5: 50.0,
    6: 60.0,
    7: 70.0,
    8: 80.0,
    9: 90.0
}


@rule(
    triggers = [
      GenericCronTrigger("0 0 * * * ?")
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
            start = now
            end = now + timedelta(days=1)

        self.calculateDumpedValues(rebuild, logger, start, end)

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

    def calculateExpectedValue(self, direction, start_time, end_time, sunshine_duration, cloud_okta, max_radiation):
        duration = (end_time - start_time).total_seconds()
        mid_time = start_time + timedelta(seconds=int(duration/2))

        elevation_factor, azimut = SunRadiation.getElevationFactor(mid_time, direction)

        current_max_radiation = astroAction.getTotalRadiation(mid_time).doubleValue()
        current_max_radiation_factor = ( current_max_radiation * 100 / max_radiation ) / 100    # is the ration between max radiation (1000W/m²) and today max radiation

        current_possible_power = solar_map[direction]["power"] * current_max_radiation_factor   # max solar power * max radiation factor
        current_possible_power = current_possible_power * duration / 3600                       # convert current_possible_power (hour based) to current_possible_power (duration based)

        elevation_reduction_factor = self.getIntersectionValue(elevation_reduction_map, solar_map[direction]["elevation"])
        current_possible_power = current_possible_power * elevation_reduction_factor            # reduction based on non optimal panel elevation

        azimut_reduction_factor = self.getIntersectionValue(azimut_diff_reduction_map, abs(solar_map[direction]["azimut"] - azimut))
        current_possible_power = current_possible_power * azimut_reduction_factor               # reduction based on diff between sun azimut and panel azimut

        current_power = current_possible_power

        current_power = current_power * elevation_factor                                        # reduction based on horizon

        sunshine_ratio = (( sunshine_duration * 100 / 60 ) / 100)
        current_solar_power = current_power * sunshine_ratio                                    # current_power only during sunshine

        cloud_reduction_factor = self.getIntersectionValue(okta_reduction_map, cloud_okta)
        possible_cloud_power = (current_power - current_solar_power) * cloud_reduction_factor   # rest is calulated on cloud factor

        # TODO
        # schauen ob man radiation vom wetterbericht bekommt

        # DONE
        # remove solcast
        # ausserhalb der sonnenscheindauer den wolkenstand berücksichtigen
        # 15 min slots benutzen
        # reduction_factor anteilsmäßig berechnen

        return current_solar_power + possible_cloud_power

    def calculateDumpedValues(self, persist, logger, start, end):
        total_expected = 0

        max_radiation = astroAction.getTotalRadiation(start.replace(day=21, month=6, hour=13, minute=0, second=0)).doubleValue()

        sunshine_states = Registry.getItem("pOutdoor_WeatherService_Sunshine_Duration").getPersistence("jdbc").getAllStatesBetween(start,end)
        cloud_states = Registry.getItem("pOutdoor_WeatherService_Cloud_Cover").getPersistence("jdbc").getAllStatesBetween(start,end)

        states = {"east": TimeSeries(TimeSeries.Policy.ADD), "south": TimeSeries(TimeSeries.Policy.ADD), "west": TimeSeries(TimeSeries.Policy.ADD)}
        for i in range(0, len(sunshine_states)):
            sunshine_state = sunshine_states[i]
            cloud_state = cloud_states[i]

            timeslot = sunshine_state.getTimestamp()
            sunshine_duration = sunshine_state.getState().doubleValue()
            cloud_okta = cloud_state.getState().doubleValue()
            #print(cloud_state.getTimestamp(), cloud_okta)

            for i in [0, 15, 30, 45]:
                start_time = timeslot + timedelta(minutes=i)
                if start_time > end:
                    continue
                end_time = start_time + timedelta(minutes=15)

                east_expected = self.calculateExpectedValue( SunRadiation.DIRECTION_EAST, start_time, end_time, sunshine_duration, cloud_okta, max_radiation)
                states["east"].add(start_time, east_expected)
                south_expected = self.calculateExpectedValue(SunRadiation.DIRECTION_SOUTH, start_time, end_time, sunshine_duration, cloud_okta, max_radiation)
                states["south"].add(start_time, south_expected)
                west_expected = self.calculateExpectedValue(SunRadiation.DIRECTION_WEST, start_time, end_time, sunshine_duration, cloud_okta, max_radiation)
                states["west"].add(start_time, west_expected)

                total_expected += east_expected + south_expected + west_expected

        if persist:
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_East").getPersistence("jdbc").persist(states["east"])
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_South").getPersistence("jdbc").persist(states["south"])
            Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").persist(states["west"])

        logger.info("TOTAL EXPECTED: {} - START: {}, END: {}".format(total_expected, start, end))

    def execute(self, module, input):
        start = datetime.now().astimezone()
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
