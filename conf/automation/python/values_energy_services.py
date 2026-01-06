import json
import urllib.parse
import threading

from datetime import datetime, timedelta

from openhab import rule, Registry, logger
from openhab.actions import HTTP
from openhab.triggers import GenericCronTrigger

from configuration import customConfigs


@rule(
    triggers = [
      GenericCronTrigger("0 0 */3 * * ?")
#      GenericCronTrigger("*/15 * * * * ?")
    ]
)
class ExpectedSolar:
    def __init__(self):
        pass #self.fetch()

    def fetchData(self, name, item_name, ressource_id, token):
        url = "https://api.solcast.com.au/rooftop_sites/{}/forecasts?format=json&api_key={}".format(ressource_id, token)
        response = HTTP.sendHttpGetRequest(url, {}, 5000)

        if response is None:
            self.logger.error("Expected '{}' solar not available".format(name))
            return

        data = json.loads(response)
        # {"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-01-04T21:00:00.0000000Z","period":"PT30M"}
        for forecast in data["forecasts"]:
            timeslot = datetime.fromisoformat(forecast["period_end"]) - timedelta(minutes=30)
            energy = forecast["pv_estimate"]
            Registry.getItem(item_name).getPersistence("jdbc").persist(timeslot.astimezone(), energy)

        self.logger.info("Expected '{}' solar updated. COUNT: {}".format(name, len(data["forecasts"])))

    def fetch(self):
        self.logger.info("Expected solar fetching started")
        self.fetchData("East", "pGF_Utilityroom_Electricity_Expected_Solar_East", customConfigs["solcast_api"]["east"]["ressource_id"],customConfigs["solcast_api"]["east"]["token"])
        self.fetchData("South", "pGF_Utilityroom_Electricity_Expected_Solar_South", customConfigs["solcast_api"]["south"]["ressource_id"],customConfigs["solcast_api"]["south"]["token"])
        self.fetchData("West", "pGF_Utilityroom_Electricity_Expected_Solar_West", customConfigs["solcast_api"]["west"]["ressource_id"],customConfigs["solcast_api"]["west"]["token"])

    def execute(self, module, input):
        threading.Thread(target=self.fetch).start()

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
        #    values = self.fetch(datetime.now().astimezone() - timedelta(days=i) )
        #    print(i)
        #    #for slot, value in values.items():
        #    #    print( str(slot) + " " + str(value))

        states = Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").getAllStatesUntil(datetime.now().astimezone() + timedelta(days=2))
        if len(states) > 0:
            self.last_date = states[-1].getTimestamp()

        self.fetch(logger)

    def fetchData(self, logger):
        logger.info("Epexspot price fetching started")

        today_start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        start_date = ( self.last_date + timedelta(minutes=15) if self.last_date is not None else today_start )
        start_date_str = urllib.parse.quote_plus(start_date.isoformat().split("T")[0])

        end_date = today_start + timedelta(days=2)
        end_date_str = urllib.parse.quote_plus(end_date.isoformat().split("T")[0])

        url = "https://api.energy-charts.info/price?bzn=DE-LU&start={}&end={}".format(start_date_str,end_date_str)

        #print(url)
        #print(end_date.isoformat().split("T")[0])
        response = HTTP.sendHttpGetRequest(url, { "Accept": "application/json" }, 5000)
        #print(response)

        if response is None or response == 'no content available':
            logger.error("Epexspot price result not available yet")
            self.last_date = None
            return

        data = json.loads(response)

        timeslots = data["unix_seconds"]
        prices = data["price"]

        for i in range(0,len(timeslots)):
            timeslot = timeslots[i]
            price = prices[i]

            Registry.getItem("pGF_Utilityroom_Electricity_Stock_Price").getPersistence("jdbc").persist(datetime.fromtimestamp(timeslot), round(price / 1000, 2))

        logger.info("Epexspot prices updated. COUNT: {}".format(len(timeslots)))

        self.last_date = datetime.fromtimestamp(timeslots[-1])

    def fetch(self, logger):
        now = datetime.now().astimezone()
        max_date = now + timedelta(days=1)

        # skip if
        # 1. last_date == tomorrow => we already have all data
        # 2. last_date == today and current < 2pm
        if self.last_date is not None and ( self.last_date.day == max_date.day or ( self.last_date.day == now.day and now.hour < 14 ) ):
            logger.info("Epexspot price fetching skipped")
            return

        threading.Thread(target=self.fetchData, args=(logger,)).start()

    def execute(self, module, input):
        self.fetch(self.logger)
