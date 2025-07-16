from datetime import datetime, timedelta

from openhab import Registry


result = Registry.getItem("pGF_Utilityroom_Heating_Circuit_Pump_Speed").getLastStateChange()
print(result)

location = Registry.getItem("pGF_Kitchen_Light_Ceiling_Brightness").getSemantic().getLocation()
print(str(location))

endDate = datetime.now()
startDate = endDate - timedelta(days=2)

print(startDate)

data = Registry.getItem("pGF_Livingroom_Air_Sensor_Temperature_Value").getPersistence().getAllStatesBetween(startDate, endDate)
print(str(data[0].getTimestamp()))

data = Registry.getItem("pGF_Livingroom_Air_Sensor_Temperature_Value").getPersistence().getAllStatesBetween(startDate.astimezone(), endDate.astimezone())
print(str(data[0].getTimestamp()))
#members = Registry.getItem("gIndoor_Lights").getAllMembers()
#for member in members:
#    print(str(member))





