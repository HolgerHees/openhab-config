from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from datetime import datetime

from shared.toolbox import ToolboxHelper

import scope


start_electricity_meter_offset = 0

#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").getPersistence("jdbc").persist(start_of_the_day, 0)

#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").postUpdate(0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").postUpdate(0)

#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption").getPersistence("jdbc").persist(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), 0)

@rule(
   triggers = [
       GenericCronTrigger("1 0 0 * * ?"),
#       GenericCronTrigger("*/15 * * * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption"),
   ]
)
class MeterConsumption:
    def execute(self, module, input):
        consumption = start_electricity_meter_offset
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption").doubleValue()
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption").doubleValue()

        consumption_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption",scope.DecimalType(0.0)).doubleValue()
        if consumption < consumption_saved:
            new_offset = consumption_saved - ( consumption - start_electricity_meter_offset)
            self.logger.error("{}: Calculation is wrong ('{}' < '{}'). Set 'start offset' to '{}'".format(mapping[0], consumption, consumption_saved, new_offset ))
            return

        # *** Gesamtverbrauch ***
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").postUpdate(consumption)

        # *** Tagesverbrauch ***
        consumption_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Daily_Consumption").postUpdateIfDifferent(consumption - consumption_today_morning)

        if Registry.getItemState("pGF_Utilityroom_Heatpump_HW_State") == scope.ON:
            total_item = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption"
            daily_item = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Daily_Consumption"
        elif Registry.getItemState("pGF_Utilityroom_Heatpump_WW_State") == scope.ON:
            total_item = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption"
            daily_item = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Daily_Consumption"
        else:
            return

        heating_consumption = Registry.getItemState(total_item).doubleValue()
        heating_consumption += consumption - consumption_saved
        Registry.getItem(total_item).postUpdateIfDifferent(heating_consumption)

        heating_consumption_today_morning = ToolboxHelper.getPersistedState(total_item, datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem(daily_item).postUpdateIfDifferent(heating_consumption - heating_consumption_today_morning)

@rule(
    triggers = [
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_1"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_2"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_3"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_1"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_2"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_3")
    ]
)
class CompressorMeterActivePower:
    def execute(self, module, input):
        l1 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_1").doubleValue()
        l2 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_2").doubleValue()
        l3 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower_3").doubleValue()
        compressor_power = l1 + l2 + l3
        if compressor_power < 0:
            compressor_power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").postUpdate(compressor_power)

        l1 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_1").doubleValue()
        l2 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_2").doubleValue()
        l3 = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower_3").doubleValue()
        electric_power = l1 + l2 + l3
        if electric_power < 0:
            electric_power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").postUpdate(electric_power)

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_ActivePower").postUpdate(compressor_power + electric_power)
