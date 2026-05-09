from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper

from datetime import datetime

import scope

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
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Demand",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Demand").doubleValue() + start_electricity_meter_demand_offset
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_demand_offset)
            self.logger.error("pGF_Utilityroom_Electricity_Meter_Demand: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_demand_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Demand").postUpdateIfDifferent(zaehler_stand_current)

        now = datetime.now().astimezone()

        # *** Tagesbezug ***
        zaehler_stand_heute_morgen = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", now.replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Demand").postUpdateIfDifferent(zaehler_stand_current - zaehler_stand_heute_morgen)

        # *** Jahresbezug ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_jahresanfang = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", start_of_the_year).doubleValue()
        current_demand = zaehler_stand_current - zaehler_stand_jahresanfang

        if Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Current").postUpdateIfDifferent(current_demand):
            # Hochrechnung
            zaehler_stand_one_year_ago = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", now.replace(year=now.year-1) ).doubleValue()
            forecast_demand = zaehler_stand_jahresanfang - zaehler_stand_one_year_ago

            zaehler_stand_jahresanfang_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", start_of_the_year.replace(year=start_of_the_year.year-1) ).doubleValue()

            hochrechnung_demand = int( round( current_demand + forecast_demand ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Forecast").postUpdateIfDifferent(hochrechnung_demand)

            vorjahres_demand = int( round( zaehler_stand_jahresanfang - zaehler_stand_jahresanfang_one_year_before ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Last").postUpdateIfDifferent(vorjahres_demand)
@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Supply")
    ]
)
class Supply:
    def execute(self, module, input):
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Supply",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Supply").doubleValue() + start_electricity_meter_supply_offset
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_supply_offset)
            self.logger.error("pGF_Utilityroom_Electricity_Meter_Supply: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_supply_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").postUpdateIfDifferent(zaehler_stand_current)

        now = datetime.now().astimezone()

        # *** Tageslieferung ***
        zaehler_stand_heute_morgen = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", now.replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Supply").postUpdateIfDifferent(zaehler_stand_current - zaehler_stand_heute_morgen)

        # *** Jahreslieferung ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_jahresanfang = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", start_of_the_year).doubleValue()
        current_supply = zaehler_stand_current - zaehler_stand_jahresanfang

        if Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Current").postUpdateIfDifferent(current_supply):
            # Hochrechnung
            zaehler_stand_one_year_ago = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", now.replace(year=now.year-1) ).doubleValue()
            forecast_supply = zaehler_stand_jahresanfang - zaehler_stand_one_year_ago

            zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", start_of_the_year.replace(year=start_of_the_year.year-1)).doubleValue()

            hochrechnung_supply = int( round( current_supply + forecast_supply ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Forecast").postUpdateIfDifferent(hochrechnung_supply)

            vorjahres_supply = int( round( zaehler_stand_jahresanfang - zaehler_stand_old_one_year_before ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Last").postUpdateIfDifferent(vorjahres_supply)
