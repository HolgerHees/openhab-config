from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from custom.energy import EnergyHelper


@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Total_Consumption"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption")
    ]
)
class Consumption:
    def execute(self, module, input):
        total = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Consumption").doubleValue()
        comfoair = Registry.getItemState("pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption").doubleValue()
        heatpump = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").doubleValue()

        EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = total - comfoair - heatpump,
          meter_offset          = -1,
          total_item            = "pGF_Utilityroom_Electricity_State_House_Total_Consumption",
          daily_item            = "pGF_Utilityroom_Electricity_State_House_Daily_Consumption",
          annual_current_item   = "pGF_Utilityroom_Electricity_State_House_Annual_Consumption",
          annual_forecast_item  = "pGF_Utilityroom_Electricity_State_House_Annual_Consumption_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Electricity_State_House_Annual_Consumption_Last",
          annual_message_item   = "pGF_Utilityroom_Electricity_State_House_Annual_Consumption_Msg"
        )

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
