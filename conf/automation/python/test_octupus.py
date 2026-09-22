#import http.client
import json

from openhab.actions import HTTP

from configuration import customConfigs

"""query =
query getAccountTariffs() {
    account(accountNumber: $accountNumber) {
        properties {
            electricitySupplyPoints {
                agreements {
                    tariff {
                        ... on TimeOfUseTariff {
                            # Hier werden die zeitabhängigen Preise abgefragt
                            halfHourPrices(fromDatetime: $fromTime, toDatetime: $toTime) {
                                valueWithTax
                                validFrom
                                validTo
                            }
                        }
                    }
                }
            }
        }
    }
}
"""


"""token = None

if token is None:
    query = "mutation MyMutation { obtainKrakenToken(input: {email: \"" + customConfigs["octupus_api"]["username"] + "\", password: \"" + customConfigs["octupus_api"]["password"] + "\"}) { token } }"
    payload = { "query": query, "operationName": "MyMutation" }
    response = HTTP.sendHttpPostRequest(customConfigs["octupus_api"]["url"], "application/json", json.dumps(payload), {}, 10000)
    data = json.loads(response)
    token = data["data"]["obtainKrakenToken"]["token"]
    print(token)

query = "query MyQuery { epexDayAheadPrices(periodStart: \"2026-09-21 00:00:00+02:00\", periodEnd: \"2026-09-22 00:00:00+02:00\", first: 100) { edges { node { unit value periodEnd periodStart }}}}"
payload = {
    "query": query,
    "operationName": "MyQuery"
}

content = json.dumps(payload)
#print(content)
response = HTTP.sendHttpPostRequest(customConfigs["octupus_api"]["url"], "application/json", content, {"Authorization": token}, 10000)
data = json.loads(response)
for slot in data["data"]["epexDayAheadPrices"]["edges"]:
  print(slot)"""
