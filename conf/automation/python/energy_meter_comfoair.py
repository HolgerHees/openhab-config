from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.energy import EnergyHelper


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
        EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = Registry.getItemState("pGF_Utilityroom_Electricity_Comfoair_Meter_Consumption").doubleValue(),
          meter_offset          = start_electricity_meter_offset,
          total_item            = "pGF_Utilityroom_Electricity_State_Comfoair_Total_Consumption",
          daily_item            = "pGF_Utilityroom_Electricity_State_Comfoair_Daily_Consumption",
          annual_current_item   = "pGF_Utilityroom_Electricity_State_Comfoair_Annual_Consumption",
          annual_forecast_item  = "pGF_Utilityroom_Electricity_State_Comfoair_Annual_Consumption_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Electricity_State_Comfoair_Annual_Consumption_Last",
          annual_message_item   = "pGF_Utilityroom_Electricity_State_Comfoair_Annual_Consumption_Msg"
        )

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
