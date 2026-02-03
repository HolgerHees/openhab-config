import json
import urllib.parse
import threading
import subprocess

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger

from custom.suncalculation import SunRadiation

from configuration import customConfigs


@rule(
    triggers = [
      GenericCronTrigger("0 0 */3 * * ?")
#      GenericCronTrigger("*/15 * * * * ?")
    ]
)
class ExpectedSolar:
    def __init__(self):
        #self.check(logger)
        #self.fetch(logger)
        pass

    def check(self, logger):
        now = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        rebuild = False
        if rebuild:
            states = Registry.getItem("pGF_Utilityroom_Electricity_Expected_Solar_West").getPersistence("jdbc").getAllStatesBetween(now.replace(year=2026,month=1,day=1),now + timedelta(days=4))
            start = states[0].getTimestamp()
            end = states[-1].getTimestamp()
        else:
            start = now # - timedelta(days=1)
            end = start + timedelta(days=1)
        #start = now
        #end = now + timedelta(days=2) #timedelta(days=3)

        self.checkSide(rebuild, logger, start, end, SunRadiation.DIRECTION_EAST, "pGF_Utilityroom_Electricity_Expected_Solar_East", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_East")
        self.checkSide(rebuild, logger, start, end, SunRadiation.DIRECTION_SOUTH, "pGF_Utilityroom_Electricity_Expected_Solar_South", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_South")
        self.checkSide(rebuild, logger, start, end, SunRadiation.DIRECTION_WEST, "pGF_Utilityroom_Electricity_Expected_Solar_West", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_West")

    def checkSide(self, rebuild, logger, start, end, direction, item_name, dumped_item_name):
        total_org = 0
        total_damped = 0

        expectedSolarStates = Registry.getItem(item_name).getPersistence("jdbc").getAllStatesBetween(start,end)
        for expectedSolarState in expectedSolarStates:
            timeslot = expectedSolarState.getTimestamp()
            energy = expectedSolarState.getState().doubleValue()
            factor = SunRadiation.getElevationFactor(timeslot, direction)

            if rebuild:
                Registry.getItem(dumped_item_name).getPersistence("jdbc").persist(timeslot.astimezone(), energy * factor)

            total_org += energy
            total_damped += energy * factor
            #print(timeslot, energy, factor)

        logger.info("{}{}: {} {}".format(direction[0].upper(), direction[1:], total_org, total_damped))

    def fetchSide(self, logger, direction, item_name, dumped_item_name, ressource_id, token):
        url = "https://api.solcast.com.au/rooftop_sites/{}/forecasts?format=json&api_key={}".format(ressource_id, token)
        response = HTTP.sendHttpGetRequest(url, {}, 30000)

        if response is None:
            logger.error("Expected '{}{}' solar response is not available".format(direction[0].upper(), direction[1:]))
            return

        try:
            data = json.loads(response)
        except ValueError:
            data = None

        if data is None or "forecasts" not in data:
            logger.error("Expected '{}{}' solar response is not valid".format(direction[0].upper(), direction[1:]))
            logger.error(url)
            logger.error(response)
            return

        # {"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-01-04T21:00:00.0000000Z","period":"PT30M"}
        for forecast in data["forecasts"]:
            timeslot = datetime.fromisoformat(forecast["period_end"]).astimezone().replace(second=0, microsecond=0) - timedelta(minutes=30)
            energy = forecast["pv_estimate"]
            Registry.getItem(item_name).getPersistence("jdbc").persist(timeslot, energy)

            factor = SunRadiation.getElevationFactor(timeslot, direction)
            Registry.getItem(dumped_item_name).getPersistence("jdbc").persist(timeslot, energy * factor)

        logger.info("Expected '{}{}' solar updated. COUNT: {}".format(direction[0].upper(), direction[1:], len(data["forecasts"])))

    def fetch(self, logger):
        logger.info("Expected solar fetching started")
        self.fetchSide(logger, SunRadiation.DIRECTION_EAST, "pGF_Utilityroom_Electricity_Expected_Solar_East", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_East", customConfigs["solcast_api"]["east"]["ressource_id"],customConfigs["solcast_api"]["east"]["token"])
        self.fetchSide(logger, SunRadiation.DIRECTION_SOUTH, "pGF_Utilityroom_Electricity_Expected_Solar_South", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_South", customConfigs["solcast_api"]["south"]["ressource_id"],customConfigs["solcast_api"]["south"]["token"])
        self.fetchSide(logger, SunRadiation.DIRECTION_WEST, "pGF_Utilityroom_Electricity_Expected_Solar_West", "pGF_Utilityroom_Electricity_Expected_Dumped_Solar_West", customConfigs["solcast_api"]["west"]["ressource_id"],customConfigs["solcast_api"]["west"]["token"])

    def execute(self, module, input):
        threading.Thread(target=self.fetch, args=(self.logger,)).start()

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
