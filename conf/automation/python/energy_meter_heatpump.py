from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, SystemStartlevelTrigger

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
       GenericCronTrigger("0 0 0 * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Main_Meter_Consumption"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption")
   ]
)
class MeterConsumption:
    def execute(self, module, input):
        consumption = start_electricity_meter_offset
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Main_Meter_Consumption").doubleValue()
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption").doubleValue()
        consumption += Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption").doubleValue()

        consumption_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption",scope.DecimalType(0.0)).doubleValue()

        if consumption < consumption_saved:
            new_offset = consumption_saved - ( consumption - start_electricity_meter_offset)
            self.logger.error("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption: Calculation is wrong ('{}' < '{}'). Set 'start offset' to '{}'".format(consumption, consumption_saved, new_offset ))
            return

        # *** Gesamtverbrauch ***
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").postUpdate(consumption)

        # *** Tagesverbrauch ***
        consumption_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Daily_Consumption").postUpdateIfDifferent(consumption - consumption_today_morning)

        if input['event'].getType() == "TimerEvent":
            Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Daily_Consumption").postUpdateIfDifferent(0)
            Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Water_Daily_Consumption").postUpdateIfDifferent(0)
        else:
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

#heating_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption").doubleValue()
#heating_consumption_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Daily_Consumption").postUpdateIfDifferent(heating_consumption - heating_consumption_today_morning)

@rule(
    triggers = [
       GenericCronTrigger("*/15 * * * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Main_ActivePower"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower"),
    ]
)
class CompressorMeterActivePower:
    def execute(self, module, input):
        main_power = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Main_ActivePower").doubleValue()
        if main_power < 0:
            main_power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Main_ActivePower").postUpdate(main_power)

        compressor_power = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower").doubleValue()
        if compressor_power < 0:
            compressor_power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").postUpdate(compressor_power)

        electric_power = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower").doubleValue()
        if electric_power < 0:
            electric_power = 0

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").postUpdate(electric_power)

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_ActivePower").postUpdate(main_power + compressor_power + electric_power)
