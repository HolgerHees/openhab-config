from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from datetime import datetime

from shared.toolbox import ToolboxHelper

import scope


#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption").getPersistence("jdbc").persist(start_of_the_day, 0)

start_electricity_meter_offset = 0

@rule(
   triggers = [
       GenericCronTrigger("0 0 0 * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Comfoair_Meter_Consumption"),
   ]
)
class MeterConsumption:
    def execute(self, module, input):
        consumption = start_electricity_meter_offset
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Comfoair_Meter_Consumption").doubleValue()

        consumption_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption",scope.DecimalType(0.0)).doubleValue()
        if consumption < consumption_saved:
            new_offset = consumption_saved - ( consumption - start_electricity_meter_offset)
            self.logger.error("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption: Calculation is wrong ('{}' < '{}'). Set 'start offset' to '{}'".format(consumption, consumption_saved, new_offset ))
            return

        # *** Gesamtverbrauch ***
        Registry.getItem("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption").postUpdate(consumption)

        # *** Tagesverbrauch ***
        consumption_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_Comfoair_Daily_Consumption").postUpdateIfDifferent(consumption - consumption_today_morning)

@rule(
    triggers = [
       GenericCronTrigger("*/15 * * * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Comfoair_ActivePower")
    ]
)
class CompressorMeterActivePower:
    def execute(self, module, input):
        power = Registry.getItemState("pGF_Utilityroom_Electricity_Comfoair_ActivePower").doubleValue()
        if power < 0:
            power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Comfoair_ActivePower").postUpdate(power)
