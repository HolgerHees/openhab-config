from openhab import rule, Registry, logger
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, SystemStartlevelTrigger, ThingStatusChangeTrigger

from shared.toolbox import ToolboxHelper
from shared.notification import NotificationHelper

from datetime import datetime

from configuration import customConfigs

import scope


# offset values for electricity meter demand and supply (total values at the time when new electricity meter was changed)
start_electricity_meter_demand_offset = 22223.717
start_electricity_meter_supply_offset = 0.0
start_electricity_meter_consumption_offset = 52933.980 #52933.973 #52933.935 #52933.913 #52933.875 #52933.840 #52933.821 #52933.754 #25559.396
start_electricity_meter_production_offset = 16261.281 #16261.268 #16261.245 #16261.244 #16260.991

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("fenecon:home-device:local")
    ]
)
class ErrorMessage:
    def execute(self, module, input):
        thing = Registry.getThing("fenecon:home-device:local")

        msg = "Thing: {}".format(thing.getStatusInfo().toString()) if thing.getStatus().toString() != "ONLINE" else ""
        Registry.getItem("eOther_Error_Solar_Inverter_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_State"),
        ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_GridEnabled")
    ]
)
class StateMessage:
    def execute(self, module, input):
        active = []
        if Registry.getItemState("pGF_Garage_Solar_Inverter_State").toString() not in ["Ok","Info"]:
            active.append(Registry.getItemState("pGF_Garage_Solar_Inverter_State").toString())

        if Registry.getItemState("pGF_Garage_Solar_Inverter_GridEnabled").intValue() == 2:
            active.append("Stromausfall")

        if len(active) == 0:
            active.append("Alles ok")

        msg = ", ".join(active)
        Registry.getItem("pGF_Utilityroom_Electricity_State_Message").postUpdate(msg)

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Demand")
    ]
)
class EnergyCounterDemand:
    def execute(self, module, input):
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Demand",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Demand").doubleValue() + start_electricity_meter_demand_offset
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_demand_offset)
            self.logger.error("pGF_Utilityroom_Electricity_Meter_Demand: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_demand_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Demand").postUpdateIfDifferent(zaehler_stand_current)

        now = datetime.now().astimezone()

        # *** Tagesbezug ***
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", start_of_the_day ).doubleValue()
        current_demand = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Demand").postUpdateIfDifferent(current_demand)

        # *** Jahresbezug ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", start_of_the_year).doubleValue()
        current_demand = zaehler_stand_current - zaehler_stand_old

        if Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Current").postUpdateIfDifferent(current_demand ):
            # Hochrechnung
            zaehler_stand_currentOneYearBefore = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", now.replace(year=now.year-1) ).doubleValue()
            forecast_demand = zaehler_stand_old - zaehler_stand_currentOneYearBefore

            zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Demand", start_of_the_year.replace(year=start_of_the_year.year-1) ).doubleValue()

            hochrechnung_demand = int( round( current_demand + forecast_demand ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Forecast").postUpdateIfDifferent(hochrechnung_demand)

            vorjahres_demand = int( round( zaehler_stand_old - zaehler_stand_old_one_year_before ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Demand_Last").postUpdateIfDifferent(vorjahres_demand)
@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Supply")
    ]
)
class EnergyCounterSupply:
    def execute(self, module, input):
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Supply",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Supply").doubleValue() + start_electricity_meter_supply_offset
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_supply_offset)
            self.logger.error("pGF_Utilityroom_Electricity_Meter_Supply: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_supply_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Supply").postUpdateIfDifferent(zaehler_stand_current)

        now = datetime.now().astimezone()

        # *** Tageslieferung ***
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", start_of_the_day ).doubleValue()
        current_supply = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Supply").postUpdateIfDifferent(current_supply)

        # *** Jahreslieferung ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", start_of_the_year).doubleValue()
        current_supply = zaehler_stand_current - zaehler_stand_old

        if Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Current").postUpdateIfDifferent(current_supply):
            # Hochrechnung
            zaehler_stand_currentOneYearBefore = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", now.replace(year=now.year-1) ).doubleValue()
            forecast_supply = zaehler_stand_old - zaehler_stand_currentOneYearBefore

            zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply", start_of_the_year.replace(year=start_of_the_year.year-1)).doubleValue()

            hochrechnung_supply = int( round( current_supply + forecast_supply ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Forecast").postUpdateIfDifferent(hochrechnung_supply)

            vorjahres_supply = int( round( zaehler_stand_old - zaehler_stand_old_one_year_before ) )
            Registry.getItem("pGF_Utilityroom_Electricity_State_Annual_Supply_Last").postUpdateIfDifferent(vorjahres_supply)


#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Consumption").doubleValue()
#zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Consumption", start_of_the_day).doubleValue()
#logger.info("CONSUMPTION: {} => {}, SUM: {}".format(zaehler_stand_old, zaehler_stand_current, zaehler_stand_current - zaehler_stand_old))

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy")
    ]
)
class EnergyDailyConsumptionTotalCalculation:
    def execute(self, module, input):
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Consumption",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = round((Registry.getItemState("pGF_Garage_Solar_Inverter_ConsumptionTotalEnergy").intValue() / 1000) + start_electricity_meter_consumption_offset, 3)
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_consumption_offset)
            self.logger.error("pGF_Utilityroom_Electricity_State_Total_Consumption: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_consumption_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Consumption").postUpdateIfDifferent(zaehler_stand_current)

        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Consumption", start_of_the_day).doubleValue()
        current_consumption = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Consumption").postUpdateIfDifferent(current_consumption);

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ProductionTotalEnergy")
    ]
)
class EnergyDailyProductionTotalCalculation:
    def execute(self, module, input):
        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Electricity_State_Total_Production",scope.DecimalType(0.0)).doubleValue()
        zaehler_stand_current = round((Registry.getItemState("pGF_Garage_Solar_Inverter_ProductionTotalEnergy").intValue() / 1000) + start_electricity_meter_production_offset, 3)
        if zaehler_stand_current < zaehler_stand_saved:
            new_offset = zaehler_stand_saved - ( zaehler_stand_current - start_electricity_meter_production_offset)
            self.logger.error("pGF_Utilityroom_Electricity_State_Total_Production: Calculation is wrong ('{}' < '{}'). Set 'start_electricity_meter_production_offset' to '{}'".format(zaehler_stand_current, zaehler_stand_saved, new_offset ))
            return

        Registry.getItem("pGF_Utilityroom_Electricity_State_Total_Production").postUpdateIfDifferent(zaehler_stand_current)

        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Production", start_of_the_day).doubleValue()
        current_production = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_State_Daily_Production").postUpdateIfDifferent(current_production);

@rule
class EnergyDailyProductionChargerCalculation:
    def __init__(self):
        self.mapping = {
            'pGF_Garage_Solar_Inverter_ChargerEastActualPower': [ 'pGF_Utilityroom_Electricity_State_Total_East_Production', 'pGF_Utilityroom_Electricity_State_Daily_East_Production' ],
            'pGF_Garage_Solar_Inverter_ChargerSouthActualPower': [ 'pGF_Utilityroom_Electricity_State_Total_South_Production', 'pGF_Utilityroom_Electricity_State_Daily_South_Production' ],
            'pGF_Garage_Solar_Inverter_ChargerWestActualPower': [ 'pGF_Utilityroom_Electricity_State_Total_West_Production', 'pGF_Utilityroom_Electricity_State_Daily_West_Production' ]
        }
        self.total_value = {}
        for key, value in self.mapping.items():
            #Registry.getItem(value).postUpdate();
            self.total_value[key] = [Registry.getItemState(value[0]).doubleValue(), Registry.getItem(key).getLastStateChange()]

    def buildTriggers(self):
        triggers = []
        for key in self.mapping.keys():
            triggers.append(ItemStateChangeTrigger(key))
        return triggers

    def execute(self, module, input):
        source = input['event'].getItemName()
        total_target, daily_target = self.mapping[source]
        time = Registry.getItem(source).getLastStateChange()
        value = input['event'].getItemState().intValue() / 1000

        ref_value, ref_time = self.total_value[source]

        duration = (time - ref_time).total_seconds()
        zaehler_stand_current = round(ref_value + (value * (duration / 60 / 60)), 3)

        self.total_value[source] = [zaehler_stand_current, time]

        #print(zaehler_stand_current)

        Registry.getItem(total_target).postUpdateIfDifferent(zaehler_stand_current)

        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState(total_target, start_of_the_day).doubleValue()
        current_production = zaehler_stand_current - zaehler_stand_old
        Registry.getItem(daily_target).postUpdateIfDifferent(current_production);

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ConsumptionActivePower"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_ProductionActivePower"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Storage_ChargerPower"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Storage_DischargerPower")
    ]
)
class EnergyRatioCalculation:
    def execute(self, module, input):
        current_demand = Registry.getItemState("pGF_Garage_Solar_Inverter_ConsumptionActivePower").intValue()
        current_production = Registry.getItemState("pGF_Garage_Solar_Inverter_ProductionActivePower").intValue()
        current_charge = Registry.getItemState("pGF_Garage_Solar_Storage_ChargerPower").intValue()
        current_discharge = Registry.getItemState("pGF_Garage_Solar_Storage_DischargerPower").intValue()

        production = current_production + current_discharge
        consumption = current_demand + current_charge

        ratio = production * 100 / consumption
        if ratio > 100:
            ratio = 100
        Registry.getItem("pGF_Utilityroom_Electricity_State_Ratio").postUpdate(ratio)

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Daily_Demand"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_State_Daily_Consumption")
    ]
)
class EnergyAutarkyCalculation:
    def execute(self, module, input):
        daily_demand = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Demand").floatValue()
        daily_consumption = Registry.getItemState("pGF_Utilityroom_Electricity_State_Daily_Consumption").floatValue()
        autarky = (100 - ((daily_demand * 100) / daily_consumption)) if daily_consumption > 0 else 100
        Registry.getItem("pGF_Utilityroom_Electricity_State_Autarky").postUpdate(autarky)

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_GridActivePower")
    ]
)
class EnergyGridCalculation:
    def execute(self, module, input):
        power = Registry.getItemState("pGF_Garage_Solar_Inverter_GridActivePower").intValue()
        if power < 0:
            Registry.getItem("pGF_Garage_Solar_Inverter_BuyFromGridPower").postUpdate(0)
            Registry.getItem("pGF_Garage_Solar_Inverter_SellToGridPower").postUpdate(power * -1)
        else:
            Registry.getItem("pGF_Garage_Solar_Inverter_BuyFromGridPower").postUpdate(power)
            Registry.getItem("pGF_Garage_Solar_Inverter_SellToGridPower").postUpdate(0)

@rule(
    triggers = [
      ItemStateChangeTrigger("pGF_Garage_Solar_Storage_ActivePower"),
      ItemStateChangeTrigger("pGF_Garage_Solar_Storage_EssSoc")
    ]
)
class EnergyStorageCalculation:
    def execute(self, module, input):
        percent = Registry.getItemState("pGF_Garage_Solar_Storage_EssSoc").intValue()
        if percent > 100:
            return

        power = Registry.getItemState("pGF_Garage_Solar_Storage_ActivePower").intValue()

        if input["event"].getItemName() == "pGF_Garage_Solar_Storage_ActivePower":
            if power < 0:
                Registry.getItem("pGF_Garage_Solar_Storage_DischargerPower").postUpdate(0)
                Registry.getItem("pGF_Garage_Solar_Storage_ChargerPower").postUpdate(power * -1)
            else:
                Registry.getItem("pGF_Garage_Solar_Storage_DischargerPower").postUpdate(power)
                Registry.getItem("pGF_Garage_Solar_Storage_ChargerPower").postUpdate(0)

        if input["event"].getItemName() == "pGF_Garage_Solar_Storage_EssSoc":
            capacity = Registry.getItemState("pGF_Garage_Solar_Storage_Capacity").intValue()
            energy_soc = percent * capacity / 100
            Registry.getItem("pGF_Garage_Solar_Storage_EnergySoc").postUpdate(percent * capacity / 100)
        else:
            energy_soc = Registry.getItemState("pGF_Garage_Solar_Storage_EnergySoc").floatValue()

        Registry.getItem("pGF_Utilityroom_Electricity_State_Battery_Msg").postUpdate(u"{} W ({} % • {:.1f} kWh)".format(power, percent, energy_soc / 1000))

@rule
class EnergyMsg:
    def __init__(self):
        self.mapping = {
            "FromGrid": [ 'pGF_Garage_Solar_Inverter_BuyFromGridPower', 'pGF_Utilityroom_Electricity_State_Daily_Demand', 'pGF_Utilityroom_Electricity_State_Demand_Msg'],
            "ToGrid": [ 'pGF_Garage_Solar_Inverter_SellToGridPower', 'pGF_Utilityroom_Electricity_State_Daily_Supply', 'pGF_Utilityroom_Electricity_State_Supply_Msg'],
            "production": [ 'pGF_Garage_Solar_Inverter_ProductionActivePower', 'pGF_Utilityroom_Electricity_State_Daily_Production', 'pGF_Utilityroom_Electricity_State_Production_Msg'],
            "consumption": [ 'pGF_Garage_Solar_Inverter_ConsumptionActivePower', 'pGF_Utilityroom_Electricity_State_Daily_Consumption', 'pGF_Utilityroom_Electricity_State_Consumption_Msg'],
        }

        self.lookupMap = {}
        for key, mapping in self.mapping.items():
            self.lookupMap[mapping[0]] = key
            self.lookupMap[mapping[1]] = key

    def buildTriggers(self):
        triggers = []
        for mapping in self.mapping.values():
            triggers.append(ItemStateChangeTrigger(mapping[0]))
            triggers.append(ItemStateChangeTrigger(mapping[1]))
        return triggers

    def execute(self, module, input):
        mappingType = self.lookupMap[input['event'].getItemName()]
        mapping = self.mapping[mappingType]

        current = Registry.getItemState(mapping[0]).intValue()
        daily = Registry.getItemState(mapping[1]).floatValue()

        Registry.getItem(mapping[2]).postUpdate(u"{} W ({:.1f} kWh)".format(current, daily))
