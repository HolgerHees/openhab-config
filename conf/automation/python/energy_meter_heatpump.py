from openhab import rule, Registry, logger
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, SystemStartlevelTrigger

from datetime import datetime

from shared.toolbox import ToolboxHelper
from custom.energy import EnergyHelper
from custom.format import FormatHelper

import scope


start_electricity_meter_offset = 0

#compressor = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption").doubleValue()
#electric = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption").doubleValue()
#print(compressor, electric)

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
        diff = input['event'].getOldItemState().doubleValue() - input["event"].getItemState().doubleValue()

        # pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption sometimes flapping
        if diff > 0 and diff < 0.002:
            self.logger.error("DEBUG: SKIP MINOR METER DIFF")
            return

        main = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Main_Meter_Consumption").doubleValue()
        compressor = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_Meter_Consumption").doubleValue()
        electric = Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_Meter_Consumption").doubleValue()

        consumption_new = main + compressor + electric
        consumption_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").doubleValue()

        EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = consumption_new,
          meter_offset          = start_electricity_meter_offset,
          total_item            = "pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption",
          daily_item            = "pGF_Utilityroom_Electricity_State_Heatpump_Daily_Consumption",
          annual_current_item   = "pGF_Utilityroom_Electricity_State_Heatpump_Annual_Consumption",
          annual_forecast_item  = "pGF_Utilityroom_Electricity_State_Heatpump_Annual_Consumption_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Electricity_State_Heatpump_Annual_Consumption_Last",
          annual_message_item   = "pGF_Utilityroom_Electricity_State_Heatpump_Annual_Consumption_Msg"
        )

        if input['event'].getType() == "TimerEvent":
            Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Daily_Consumption").postUpdateIfDifferent(0)
            Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Water_Daily_Consumption").postUpdateIfDifferent(0)
        else:
            if Registry.getItemState("pGF_Utilityroom_Heatpump_HW_State") == scope.ON:
                total_item = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption"
                daily_item = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Daily_Consumption"
                annual_item = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Annual_Consumption"
            elif Registry.getItemState("pGF_Utilityroom_Heatpump_WW_State") == scope.ON:
                total_item = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption"
                daily_item = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Daily_Consumption"
                annual_item = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Annual_Consumption"
            else:
                return

            EnergyHelper.calculateStats(
              logger                = self.logger,
              meter_value           = Registry.getItemState(total_item).doubleValue() + (consumption_new - consumption_saved),
              meter_offset          = 0,
              total_item            = total_item,
              daily_item            = daily_item,
              annual_current_item   = annual_item,
              annual_forecast_item  = "{}_Forecast".format(annual_item),
              annual_last_year_item = "{}_Last".format(annual_item),
              annual_message_item   = "{}_Msg".format(annual_item)
            )

#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption").postUpdateIfDifferent(35.684)

#EnergyHelper.calculateStats(
#  logger                = logger,
#  meter_value           = Registry.getItemState("pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption").doubleValue(),
#  meter_offset          = 0,
#  total_item            = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption",
#  daily_item            = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Daily_Consumption",
#  annual_current_item   = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Annual_Consumption",
#  annual_forecast_item  = "{}_Forecast".format("pGF_Utilityroom_Electricity_State_Heatpump_Water_Annual_Consumption"),
#  annual_last_year_item = "{}_Last".format("pGF_Utilityroom_Electricity_State_Heatpump_Water_Annual_Consumption"),
#  annual_message_item   = "{}_Msg".format("pGF_Utilityroom_Electricity_State_Heatpump_Water_Annual_Consumption")
#)

@rule(
    triggers = [
       #GenericCronTrigger("*/15 * * * * ?"),
       GenericCronTrigger("0 */5 * * * ?"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Main_ActivePower"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower"),
       ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower"),
    ]
)
class CompressorMeterActivePower:
    def execute(self, module, input):
        main_power = max(Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Main_ActivePower").doubleValue(), 0)
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Main_ActivePower").postUpdate(main_power)

        compressor_power = max(Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Compressor_ActivePower").doubleValue(), 0)
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").postUpdate(compressor_power)

        electric_power = max(Registry.getItemState("pGF_Utilityroom_Electricity_Heatpump_Electric_ActivePower").doubleValue(), 0)
        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").postUpdate(electric_power)

        Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_ActivePower").postUpdate(main_power + compressor_power + electric_power)

@rule(
    triggers = [
       #GenericCronTrigger("0 0 0 * * ?"),
       GenericCronTrigger("0 */5 * * * ?")
       #ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Statistik_Gesamt_monat")
    ]
)
class HeatpumpStatsThermalProduction:
    def execute(self, module, input):
        #total_consumption_current_month = Registry.getItemState("pGF_Utilityroom_Heatpump_Statistik_Heizen_monat").doubleValue()
        #total_consumption_current_month = Registry.getItemState("pGF_Utilityroom_Heatpump_Statistik_WW_monat").doubleValue()
        #total_consumption_current_month = Registry.getItemState("pGF_Utilityroom_Heatpump_Statistik_Gesamt_monat").doubleValue()

        now = datetime.now().astimezone()
        today_morning = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heatpump_Statistik_Total_Production", today_morning ).doubleValue()
        total_heating_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heatpump_Statistik_Heizen_Total_Production", today_morning ).doubleValue()
        total_ww_today_morning = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heatpump_Statistik_WW_Total_Production", today_morning ).doubleValue()

        heating_energy_since_today_morning = Registry.getItem("pGF_Utilityroom_Heatpump_HW_Energy").getPersistence("jdbc").riemannSumBetween(today_morning, now).doubleValue() / 60 / 60 # KWs => KWh
        ww_energy_since_today_morning = Registry.getItem("pGF_Utilityroom_Heatpump_WW_Energy").getPersistence("jdbc").riemannSumBetween(today_morning, now).doubleValue() / 60 / 60 # KWs => KWh

        total_production = EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = total_today_morning + heating_energy_since_today_morning + ww_energy_since_today_morning,
          meter_offset          = 0,
          total_item            = "pGF_Utilityroom_Heatpump_Statistik_Total_Production",
          daily_item            = "pGF_Utilityroom_Heatpump_Statistik_Daily_Production",
          annual_current_item   = "pGF_Utilityroom_Heatpump_Statistik_Annual_Production",
          annual_forecast_item  = "pGF_Utilityroom_Heatpump_Statistik_Annual_Production_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Heatpump_Statistik_Annual_Production_Last",
          annual_message_item   = "pGF_Utilityroom_Heatpump_Statistik_Annual_Production_Msg"
        )

        EnergyHelper.calculateJAZ(
            logger              = self.logger,
            thermal_value       = total_production,
            thermal_item        = "pGF_Utilityroom_Heatpump_Statistik_Total_Production",
            electric_item       = "pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption",
            jaz_item            = "pGF_Utilityroom_Heatpump_Statistik_JAZ"
        )

        total_heating_production = EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = total_heating_today_morning + heating_energy_since_today_morning,
          meter_offset          = 0,
          total_item            = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Total_Production",
          daily_item            = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Daily_Production",
          annual_current_item   = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Annual_Production",
          annual_forecast_item  = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Annual_Production_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Annual_Production_Last",
          annual_message_item   = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Annual_Production_Msg"
        )

        EnergyHelper.calculateJAZ(
            logger              = self.logger,
            thermal_value       = total_heating_production,
            thermal_item        = "pGF_Utilityroom_Heatpump_Statistik_Heizen_Total_Production",
            electric_item       = "pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption",
            jaz_item            = "pGF_Utilityroom_Heatpump_Statistik_Heizen_JAZ"
        )

        total_ww_production = EnergyHelper.calculateStats(
          logger                = self.logger,
          meter_value           = total_ww_today_morning + ww_energy_since_today_morning,
          meter_offset          = 0,
          total_item            = "pGF_Utilityroom_Heatpump_Statistik_WW_Total_Production",
          daily_item            = "pGF_Utilityroom_Heatpump_Statistik_WW_Daily_Production",
          annual_current_item   = "pGF_Utilityroom_Heatpump_Statistik_WW_Annual_Production",
          annual_forecast_item  = "pGF_Utilityroom_Heatpump_Statistik_WW_Annual_Production_Forecast",
          annual_last_year_item = "pGF_Utilityroom_Heatpump_Statistik_WW_Annual_Production_Last",
          annual_message_item   = "pGF_Utilityroom_Heatpump_Statistik_WW_Annual_Production_Msg"
        )

        EnergyHelper.calculateJAZ(
            logger              = self.logger,
            thermal_value       = total_ww_production,
            thermal_item        = "pGF_Utilityroom_Heatpump_Statistik_WW_Total_Production",
            electric_item       = "pGF_Utilityroom_Electricity_State_Heatpump_Water_Total_Consumption",
            jaz_item            = "pGF_Utilityroom_Heatpump_Statistik_WW_JAZ"
        )

        hh_production = Registry.getItemState("pGF_Utilityroom_Heatpump_Statistik_Heizen_Daily_Production").doubleValue()
        ww_production = Registry.getItemState("pGF_Utilityroom_Heatpump_Statistik_WW_Daily_Production").doubleValue()

        Registry.getItem("pGF_Utilityroom_Heatpump_Statistik_Msg").postUpdateIfDifferent("HZ {} KWh • WW {} KWh".format(FormatHelper.format(hh_production, 1), FormatHelper.format(ww_production, 1) ))
