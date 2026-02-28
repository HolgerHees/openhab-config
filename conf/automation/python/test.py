import sys
import scope
from openhab.actions import Transformation


rawjson = '{"Time":"2020-10-10T20:33:27","DS18B20_1":{"Id":"3C01B6078704","Temperature":19.4},"DS18B20_2":{"Id":"3C01B607DE10","Temperature":19.9},"DS18B20_3":{"Id":"3C01B607FA45","Temperature":19.9},"TempUnit":"C"}'



results = Transformation.transform("JSONPATH", "$.DS18B20_2", rawjson)
print(results)

results = Transformation.transform("JSONPATH", "$.DS18B20_2.Temperature", rawjson)
print(results)

results =  Transformation.transform("JSONPATH", "$..[?(@.Id==\"3C01B607DE10\")]", rawjson)
print(results)

results =  Transformation.transform("JSONPATH", "$..[?(@.Id==\"3C01B607DE10\")].Temperature", rawjson)
print(results)
