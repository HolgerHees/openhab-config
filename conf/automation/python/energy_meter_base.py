from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.energy import EnergyHelper


# offset values for electricity meter demand and supply (total values at the time when new electricity meter was changed)
start_electricity_meter_demand_offset = 22223.717
start_electricity_meter_supply_offset = 0.0


@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Demand")
    ]
)
class Demand:
    def execute(self, module, input):
        EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Demand").doubleValue(),
          meter_offset          = start_electricity_meter_demand_offset,
          total_item            = "pGF_Utilityroom_Electricity_State_Total_Demand",
          daily_item            = "pGF_Utilityroom_Electricity_State_Daily_Demand",
          annual_current_item   = "pGF_Utilityroom_Electricity_State_Annual_Demand_Current",
          annual_forecast_item  = "pGF_Utilityroom_Electricity_State_Annual_Demand_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Electricity_State_Annual_Demand_Last",
          annual_message_item   = "pGF_Utilityroom_Electricity_State_Annual_Demand_Msg"
        )

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Supply")
    ]
)
class Supply:
    def execute(self, module, input):
        EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Supply").doubleValue(),
          meter_offset          = start_electricity_meter_supply_offset,
          total_item            = "pGF_Utilityroom_Electricity_State_Total_Supply",
          daily_item            = "pGF_Utilityroom_Electricity_State_Daily_Supply",
          annual_current_item   = "pGF_Utilityroom_Electricity_State_Annual_Supply_Current",
          annual_forecast_item  = "pGF_Utilityroom_Electricity_State_Annual_Supply_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Electricity_State_Annual_Supply_Last",
          annual_message_item   = "pGF_Utilityroom_Electricity_State_Annual_Supply_Msg"
        )
