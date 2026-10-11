#import http.client
import json

from openhab.actions import HTTP

from configuration import customConfigs

token = "eyJhbGciOiJSUzI1NiIsImlzcyI6Imh0dHBzOi8vYXBpLm9lZy1rcmFrZW4uZW5lcmd5L3YxL2dyYXBocWwvIiwiamt1IjoiaHR0cHM6Ly9hdXRoLm9lZy1rcmFrZW4uZW5lcmd5Ly53ZWxsLWtub3duL2p3a3MuanNvbiIsImtpZCI6InVVRG5Iak9nczBPOFZvMjhtYmMxWnlFYmZoWVlUdGNmS3Y3OHQ1U2xCNnciLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJrcmFrZW58YWNjb3VudC11c2VyOjE4OTMxMTUiLCJndHkiOiJFTUFJTC1BTkQtUEFTU1dPUkQiLCJ0b2tlblVzZSI6ImFjY2VzcyIsImVtYWlsIjoiaG9sZ2VyLmhlZXNAZ21haWwuY29tIiwiaXNzIjoiaHR0cHM6Ly9hcGkub2VnLWtyYWtlbi5lbmVyZ3kvdjEvZ3JhcGhxbC8iLCJpYXQiOjE3OTExODMyMjksImV4cCI6MTc5MTE4NjgyOSwib3JpZ0lhdCI6MTc5MTE4MzIyOSwiYXV0aF90aW1lIjoxNzkxMTgzMjI5fQ.Gxu_WJs-dUI4WnA0yyw3evsDLdto2ek9IIqebZqanBUJ0ZbZCyKX6hcL3itOJNYuDYcEaRBV2S6TsEPWiqaOrqia8zWN4blnSze9VkgpxOe3B-toiYdJnXWlF8uhtxZkT8_xq6VCvDEJfxMU30HeBVRU4BXbP_cQKClAbJr9BFubLXtfnqF67XyAB_UzVHeAowQR05zbYRw-qxah5HIrwt4c-nL7qAFvL3MKoGUcZw7hbK6-ISowc34spoQOBsGpUCGxW0BavoqKE1-7-Ethat7JuX2YWS_0RnELQvXCUPt_HAF2Re2bQ1lm50dbZh2lRLSF8LNXD-RgmI2SpNEeDQ"

if token is None:
    query = "mutation MyMutation { obtainKrakenToken(input: {email: \"" + customConfigs["octupus_api"]["username"] + "\", password: \"" + customConfigs["octupus_api"]["password"] + "\"}) { token } }"
    payload = { "query": query, "operationName": "MyMutation" }
    response = HTTP.sendHttpPostRequest(customConfigs["octupus_api"]["url"], "application/json", json.dumps(payload), {}, 10000)
    data = json.loads(response)
    token = data["data"]["obtainKrakenToken"]["token"]
    print(token)

query = """
query getDayAheadPrices($accountNumber: String!) {
    account(accountNumber: $accountNumber) {
        properties {
            electricityMalos {
                agreements {
                    unitRateForecast {
                        validFrom
                        validTo
                        unitRateInformation {
                            ... on TimeOfUseProductUnitRateInformation {
                                rates {
                                    netUnitRateCentsPerKwh
                                    latestGrossUnitRateCentsPerKwh
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""

#query = "query MyQuery { epexDayAheadPrices(periodStart: \"2026-09-21 00:00:00+02:00\", periodEnd: \"2026-09-22 00:00:00+02:00\", first: 100) { edges { node { unit value periodEnd periodStart }}}}"
payload = {
    "query": query,
    "operationName": "getDayAheadPrices",
    "variables": {
        "accountNumber": customConfigs["octupus_api"]["account_number"]
    }
}

content = json.dumps(payload)
print(content)
response = HTTP.sendHttpPostRequest(customConfigs["octupus_api"]["url"], "application/json", content, {"Authorization": token}, 10000)
data = json.loads(response)
print(data)
#for slot in data["data"]["epexDayAheadPrices"]["edges"]:
#  print(slot)
