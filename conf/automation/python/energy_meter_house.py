from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from datetime import datetime

from shared.toolbox import ToolboxHelper


#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_House_Total_Consumption").getPersistence("jdbc").persist(start_of_the_day, 0)

#Registry.getItem("pGF_Utilityroom_Electricity_State_House_Daily_Consumption").postUpdate(0)

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Total_Consumption"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption"),
    ]
)
class Consumption:
    def execute(self, module, input):
        total = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Consumption").doubleValue()
        comfoair = Registry.getItemState("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption").doubleValue()
        heatpump = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").doubleValue()

        consumption = total - comfoair - heatpump

        Registry.getItem("pGF_Utilityroom_Electricity_State_House_Total_Consumption").postUpdateIfDifferent(consumption)

        # *** Tagesbezug ***
        consumption_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_House_Total_Consumption", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_House_Daily_Consumption").postUpdateIfDifferent(consumption - consumption_old)

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ConsumptionActivePower"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Comfoair_ActivePower"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Heatpump_Main_ActivePower"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower")
    ]
)
class ActivePower:
    def execute(self, module, input):
        total = Registry.getItemState("pGF_Garage_Solar_Inverter_ConsumptionActivePower").doubleValue()
        comfoair = Registry.getItemState("pGF_Utilityroom_Electricity_State_Comfoair_ActivePower").doubleValue()
        headpump_main = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Main_ActivePower").doubleValue()
        headpump_compressor = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").doubleValue()
        headpump_electric = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").doubleValue()

        Registry.getItem("pGF_Utilityroom_Electricity_State_House_ActivePower").postUpdate(total - comfoair - headpump_main - headpump_compressor - headpump_electric)

