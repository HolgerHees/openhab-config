from openhab import Registry
from datetime import datetime, timedelta

#temp_persistence = Registry.getItem("pOutdoor_WeatherStation_Temperature").getPersistence("jdbc")
#gas_persistence = Registry.getItem("pGF_Utilityroom_Gas_Meter_Current_Count").getPersistence("jdbc")

#now = datetime.now()
#end = datetime.now().replace(day=1, month=1, year=now.year-1, hour=0, minute=0, second=0, microsecond=0)
#start = end.replace(year=end.year-1)

#rows = [["Date","Gas","Temperature"]]
#slot = start
#while slot < end:
#    _slot = slot + timedelta(days=1)

#    temp_value = round(temp_persistence.averageBetween(slot, _slot).doubleValue(), 1)
#    gas_value = round(gas_persistence.deltaBetween(slot, _slot).doubleValue(), 2)

#    rows.append([slot.date().isoformat(), gas_value, temp_value])

#    slot = _slot

#print(rows)

#dumped_states = persistance.changedBetween(forecast_start, forecast_end)

