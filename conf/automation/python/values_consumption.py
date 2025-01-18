from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger

from shared.toolbox import ToolboxHelper

from datetime import datetime, timedelta


#from org.openhab.core.types.RefreshType import REFRESH

total_supply = 3600 # total possible photovoltaic power in watt
maxTimeSlot = 300000 # value timeslot to messure average power consumption => 5 min

# offset values for electricity meter demand and supply (total values at the time when new electricity meter was changed)
start_electricity_meter_demand_offset = 0.0
start_electricity_meter_supply_offset = 0.0

# offset values for gas meter (total value at the time when knx based impulse counter was resettet)
start_gas_meter_value = 10405.39
start_gas_impulse_counter = 0

#dateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS")

#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Current_Daily_Demand",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Current_Daily_Demand",value)
#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Current_Daily_Supply",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Current_Daily_Supply",value)
#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_Total_Supply",value)
#value = ToolboxHelper.getPersistedState("pGF_Garage_Solar_Inverter_Power_Limitation",datetime.now().astimezone()).intValue()
#postUpdate("pGF_Garage_Solar_Inverter_Power_Limitation",value)

def getHistoricReference(logger, item_name, value_time, outdated_time, messure_time, interval_time):

    item = Registry.getItem(item_name)
    end_time = ToolboxHelper.getLastChange(item)

    now = datetime.now().astimezone()
 
    if end_time < now - timedelta(seconds=outdated_time):
        logger.info( "No consumption. Last value is too old." )
        return 0

    min_messured_time = now - timedelta(seconds=messure_time)

    end_value = item.getState().doubleValue()

    start_time = end_time
    start_value = 0

    current_time = start_time - timedelta(microseconds=1)

    item_count = 0

    while True:
        item_count = item_count + 1

        historic_entry = ToolboxHelper.getPersistedEntry(item, current_time )

        start_value = historic_entry.getState().doubleValue()

        _time = historic_entry.getTimestamp()

        # current item is older then the allowed timeRange
        if _time < min_messured_time:
            logger.info( "Consumption time limit exceeded" )
            start_time = start_time - timedelta(seconds=interval_time)
            if _time > start_time:
                 start_time = _time
            break
        # 2 items are enough to calculate with
        elif item_count >= 2:
            logger.info( "Consumption max item count exceeded" )
            start_time = _time
            break
        else:
            start_time = _time
            current_time = start_time - timedelta(microseconds=1)
            
    duration_in_seconds = (end_time - start_time).total_seconds()
    value = ( (end_value - start_value) / duration_in_seconds) * value_time
    if value < 0:
        value = 0

    logger.info( "Consumption {} messured from {} ({}) to {} ({})".format(value, start_value, start_time.strftime("%Y-%m-%d %H:%M:%S"), end_value, end_time.strftime("%Y-%m-%d %H:%M:%S")))

    return value

@rule(
    triggers = [
        GenericCronTrigger("45 */30 * * * ?")
    ]
)
class SolarPower5min:
    def execute(self, module, input):
        value5Min = getHistoricReference(self.logger, "pGF_Utilityroom_Heating_Solar_Power", 300, 3600, 5600, 1800)
        Registry.getItem("pGF_Utilityroom_Heating_Solar_Power_Current5Min").postUpdateIfDifferent(value5Min)

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Demand")
    ]
)
class EnergyCounterDemand:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Demand").doubleValue() + start_electricity_meter_demand_offset
        Registry.getItem("pGF_Utilityroom_Electricity_Total_Demand").postUpdateIfDifferent(zaehler_stand_current)

        # *** Tagesbezug ***
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Demand", start_of_the_day ).doubleValue()
        current_demand = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_Current_Daily_Demand").postUpdateIfDifferent(current_demand)

        # *** Jahresbezug ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Demand", start_of_the_year).doubleValue()
        current_demand = zaehler_stand_current - zaehler_stand_old

        if Registry.getItem("pGF_Utilityroom_Electricity_Current_Annual_Demand").postUpdateIfDifferent(current_demand ):
            # Hochrechnung
            zaehler_stand_currentOneYearBefore = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Demand", now.replace(year=now.year-1) ).doubleValue()
            forecast_demand = zaehler_stand_old - zaehler_stand_currentOneYearBefore

            zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Demand", start_of_the_year.replace(year=start_of_the_year.year-1) ).doubleValue()

            hochrechnung_demand = int( round( current_demand + forecast_demand ) )
            vorjahres_demand = int( round( zaehler_stand_old - zaehler_stand_old_one_year_before ) )
            msg = "{} kWh, {} kWh".format(hochrechnung_demand,vorjahres_demand)
            Registry.getItem("pGF_Utilityroom_Electricity_Current_Annual_Demand_Forecast").postUpdate(msg)

@rule(
    triggers = [
      GenericCronTrigger("1 0 0 * * ?"),
      ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Meter_Supply")
    ]
)
class EnergyCounterSupply:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        
        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Electricity_Meter_Supply").doubleValue() + start_electricity_meter_supply_offset
        Registry.getItem("pGF_Utilityroom_Electricity_Total_Supply").postUpdateIfDifferent(zaehler_stand_current)

        # *** Tageslieferung ***
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", start_of_the_day ).doubleValue()
        current_supply = zaehler_stand_current - zaehler_stand_old
        Registry.getItem("pGF_Utilityroom_Electricity_Current_Daily_Supply").postUpdateIfDifferent(current_supply)

        # *** Jahreslieferung ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", start_of_the_year).doubleValue()
        current_supply = zaehler_stand_current - zaehler_stand_old

        if Registry.getItem("pGF_Utilityroom_Electricity_Current_Annual_Supply").postUpdateIfDifferent(current_supply):
            # Hochrechnung
            zaehler_stand_currentOneYearBefore = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", now.replace(year=now.year-1) ).doubleValue()
            forecast_supply = zaehler_stand_old - zaehler_stand_currentOneYearBefore

            zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", start_of_the_year.replace(year=start_of_the_year.year-1)).doubleValue()

            hochrechnung_supply = int( round( current_supply + forecast_supply ) )
            vorjahres_supply = int( round( zaehler_stand_old - zaehler_stand_old_one_year_before ) )
            msg = "{}kWh, {} kWh".format(hochrechnung_supply,vorjahres_supply)
            Registry.getItem("pGF_Utilityroom_Electricity_Current_Annual_Supply_Forecast").postUpdate(msg)

@rule(
    triggers = [
        GenericCronTrigger("0 * * * * ?")
    ]
)
class EnergyTotalYieldRefresh:
    def execute(self, module, input):
        if Registry.getItemState("pOther_Automatic_State_Solar") == ON:
            # triggers solar value update
            Registry.getItem("pGF_Garage_Solar_Inverter_Total_Yield").sendCommand(REFRESH)
        
@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Power_Demand_Active"),
        ItemStateChangeTrigger("pGF_Utilityroom_Power_Supply_Active"),
        ItemStateUpdateTrigger("pGF_Garage_Solar_Inverter_AC_Power")
    ]
)
class EnergyCurrentDemandAndConsumption:
    def __init__(self):
        self.current_demand = self.power_demand = self.power_supply = None
        
    def updateConsumption(self,solarPower):
        consumption = self.current_demand + solarPower
        
        if consumption > 0:
            Registry.getItem("pGF_Utilityroom_Electricity_Current_Consumption").postUpdateIfDifferent(consumption)
        else:
            self.logger.info("Skip consumption update. power_demand: {}, power_supply: {}, solarPower: {}".format(self.power_demand,self.power_supply,solarPower))

    def execute(self, module, input):
        if input["event"].getItemName() == "pGF_Garage_Solar_Inverter_AC_Power":
            if self.current_demand is not None:
                self.updateConsumption(input["event"].getItemState().intValue())
        else:
            if input["event"].getItemName() == "pGF_Utilityroom_Power_Demand_Active":
                self.power_demand = input["event"].getItemState().intValue()
                self.power_supply = Registry.getItemState("pGF_Utilityroom_Power_Supply_Active").intValue()
                
                if self.power_demand != Registry.getItemState("pGF_Utilityroom_Power_Demand_Active").intValue():
                    self.logger.error("Item demand state differences: {}, item state: {}".format(self.power_demand, Registry.getItemState("pGF_Utilityroom_Power_Demand_Active").intValue()))
            else:
                self.power_demand = Registry.getItemState("pGF_Utilityroom_Power_Demand_Active").intValue()
                self.power_supply = input["event"].getItemState().intValue()
                
                if self.power_supply != Registry.getItemState("pGF_Utilityroom_Power_Supply_Active").intValue():
                    self.logger.error("Item supply state differences: {}, item state: {}".format(self.power_supply, Registry.getItemState("pGF_Utilityroom_Power_Supply_Active").intValue()))

            self.current_demand = self.power_demand - self.power_supply
            
            #self.logger.info("{}".format(itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_Total_Yield", datetime.now().astimezone().minusMinutes(15))))
            
            now = datetime.now().astimezone()
            if Registry.getItemState("pOther_Automatic_State_Solar") == ON:
                if ToolboxHelper.getLastUpdate("pOther_Automatic_State_Solar") < now - timedelta(minutes=60):
                    # solar value update was not successful for a while
                    #solarActive = Registry.getItemState("pOther_Automatic_State_Solar") == ON
                    #if itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_Total_Yield", now - timedelta(hours=5) if solarActive else now - timedelta(hours=14)):
                    if ToolboxHelper.getLastUpdate("pGF_Garage_Solar_Inverter_Total_Yield") < now - timedelta(minutes=15) or (ToolboxHelper.getLastUpdate("pGF_Garage_Solar_Inverter_AC_Power") < now - timedelta(minutes=60) and Registry.getItemState("pGF_Garage_Solar_Inverter_AC_Power").intValue() > 0):
                        #(itemLastUpdateOlderThen("pGF_Garage_Solar_Inverter_AC_Power", datetime.now().astimezone().minusMinutes(15)) or Registry.getItemState("pGF_Garage_Solar_Inverter_AC_Power").intValue() == 0)):
                        if Registry.getItem("eOther_Error_Solar_Inverter_Message").postUpdateIfDifferent("Keine Updates mehr seit mehr als 60 Minuten"):
                            Registry.getItem("pGF_Garage_Solar_Inverter_AC_Power").postUpdate(0)
                            Registry.getItem("pGF_Garage_Solar_Inverter_DC_Power").postUpdateIfDifferent(0)
                            Registry.getItem("pGF_Garage_Solar_Inverter_DC_Current").postUpdateIfDifferent(0)
                            Registry.getItem("pGF_Garage_Solar_Inverter_DC_Voltage").postUpdateIfDifferent(0)
                            Registry.getItem("pGF_Garage_Solar_Inverter_Daily_Yield").postUpdateIfDifferent(0)
                    else:
                        Registry.getItem("eOther_Error_Solar_Inverter_Message").postUpdateIfDifferent("")

                # triggers solar value update
                Registry.getItem("pGF_Garage_Solar_Inverter_AC_Power").sendCommand(REFRESH)
            else:
                self.updateConsumption(0)
                Registry.getItem("eOther_Error_Solar_Inverter_Message").postUpdateIfDifferent("")
            Registry.getItem("pGF_Utilityroom_Electricity_Current_Demand").postUpdateIfDifferent(self.current_demand)

@rule(
    triggers = [
        #ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Current_Daily_Demand"),
        #ItemStateChangeTrigger("pGF_Utilityroom_Electricity_Current_Daily_Supply"),
        #ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Daily_Yield")
        # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
        GenericCronTrigger("30 */5 * * * ?")
    ]
)
class EnergyDailyConsumption:
    def execute(self, module, input):
        dailyEnergyDemand = Registry.getItemState("pGF_Utilityroom_Electricity_Current_Daily_Demand").doubleValue()
        dailyEnergySupply = Registry.getItemState("pGF_Utilityroom_Electricity_Current_Daily_Supply").doubleValue()
        dailySolarSupply = Registry.getItemState("pGF_Garage_Solar_Inverter_Daily_Yield").doubleValue()

        Registry.getItem("pGF_Utilityroom_Electricity_Current_Daily_Consumption").postUpdateIfDifferent(dailyEnergyDemand - dailyEnergySupply + dailySolarSupply)

@rule(
    triggers = [
        #ItemStateChangeTrigger("Electricity_Meter_Supply"),
        #ItemStateChangeTrigger("pGF_Garage_Solar_Inverter_Total_Yield"),
        # should be cron based, otherwise it will create until 3 times more values if it is based on ItemStateChangeTrigger
        GenericCronTrigger("15 */5 * * * ?")
    ]
)
class SolarConsumption:
    def execute(self, module, input):
        now = datetime.now().astimezone()
      
        current_supply = Registry.getItemState("pGF_Utilityroom_Electricity_Total_Supply").doubleValue()
        current_yield = Registry.getItemState("pGF_Garage_Solar_Inverter_Total_Yield").doubleValue()
        
        # Tagesverbrauch
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_supply = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", start_of_the_day ).doubleValue()
        start_yield = ToolboxHelper.getPersistedState("pGF_Garage_Solar_Inverter_Total_Yield", start_of_the_day ).doubleValue()

        # sometimes solar converter is providing wrong value. Mostly if he is inactive in the night
        if current_yield > 1000000000 or start_yield > 1000000000:
            # can be INFO because it is a 'normal' behavior of this  solar converter
            self.logger.info("Wrong Solar Value: current_yield is {}, start_yield is {}".format(current_yield,start_yield))
            return

        total_supply = current_supply - start_supply
        total_yield = current_yield - start_yield
        daily_consumption = total_yield - total_supply
        
        Registry.getItem("pGF_Garage_Solar_Inverter_Daily_Yield").postUpdateIfDifferent(total_yield)
        
        #self.logger.info("A {} {}".format(current_supply,current_yield))
        #self.logger.info("B {} {}".format(start_supply,start_yield))
        #self.logger.info("C {} {}".format(total_supply,total_yield))
        
        Registry.getItem("pGF_Garage_Solar_Inverter_Daily_Consumption").postUpdateIfDifferent(daily_consumption)
        
        # Jahresverbrauch
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        start_supply = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_Total_Supply", start_of_the_year ).doubleValue()
        start_yield = ToolboxHelper.getPersistedState("pGF_Garage_Solar_Inverter_Total_Yield", start_of_the_year ).doubleValue()

        total_supply = current_supply - start_supply
        total_yield = current_yield - start_yield
        annualConsumption = total_yield - total_supply
        
        #self.logger.info("D {} {}".format(start_supply,start_yield))
        #self.logger.info("E {}".format(annualConsumption))
        
        Registry.getItem("pGF_Garage_Solar_Inverter_Annual_Consumption").postUpdateIfDifferent(annualConsumption)

@rule(
    triggers = [
        GenericCronTrigger("15 */5 * * * ?")
    ]
)
class GasConsumption5Min:
    def execute(self, module, input):
        value5Min = getHistoricReference( self.logger, "pGF_Utilityroom_Gas_Meter_Current_Count", 300, 615, 900, 300 )
        Registry.getItem("pGF_Utilityroom_Gas_Current_Consumption").postUpdateIfDifferent(value5Min)

@rule(
    triggers = [
        GenericCronTrigger("0 0 0 * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Gas_Meter_Pulse_Counter")
    ]
)
class GasConsumption:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        current_end = Registry.getItemState("pGF_Utilityroom_Gas_Meter_Pulse_Counter").doubleValue()

        # Aktueller Zählerstand
        zaehler_stand_current = start_gas_meter_value + ((current_end - start_gas_impulse_counter) * 0.01)

        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Gas_Meter_Current_Count",DecimalType(0.0)).doubleValue()
        
        #self.logger.info("{}".format(zaehler_stand_current))
        
        if zaehler_stand_current < zaehler_stand_saved:
            self.logger.error("Consumption: Calculation is wrong {} {}".format(zaehler_stand_current,zaehler_stand_saved))
            return

        if zaehler_stand_current > zaehler_stand_saved:
            # Aktueller Zählerstand
            Registry.getItem("pGF_Utilityroom_Gas_Meter_Current_Count").postUpdate(zaehler_stand_current )

        # *** Aktueller Tagesverbrauch ***
        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Gas_Meter_Current_Count", start_of_the_day ).doubleValue()
        current_consumption = zaehler_stand_current - zaehler_stand_old
        if current_consumption < 0:
            current_consumption = 0

        Registry.getItem("pGF_Utilityroom_Gas_Current_Daily_Consumption").postUpdateIfDifferent(current_consumption)

        # *** Jahresverbrauch ***
        start_of_the_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        zaehler_stand_old = ToolboxHelper.getPersistedState("pGF_Utilityroom_Gas_Meter_Current_Count", start_of_the_year ).doubleValue()
        current_consumption = zaehler_stand_current - zaehler_stand_old
        if current_consumption < 0:
            current_consumption = 0

        Registry.getItem("pGF_Utilityroom_Gas_Annual_Consumption").postUpdateIfDifferent(current_consumption )

        # Hochrechnung
        zaehler_stand_currentOneYearBefore = ToolboxHelper.getPersistedState("pGF_Utilityroom_Gas_Meter_Current_Count", now.replace(year=now.year-1) ).doubleValue()
        forecast_consumption = zaehler_stand_old - zaehler_stand_currentOneYearBefore

        zaehler_stand_old_one_year_before = ToolboxHelper.getPersistedState("pGF_Utilityroom_Gas_Meter_Current_Count", start_of_the_year.replace(year=start_of_the_year.year-1) ).doubleValue()

        hochrechnungVerbrauch = round( current_consumption + forecast_consumption )

        msg = "{} m³, {} m³".format(hochrechnungVerbrauch, round( zaehler_stand_old - zaehler_stand_old_one_year_before ) )
        Registry.getItem("pGF_Utilityroom_Gas_Forecast").postUpdate(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pMobile_Socket_5_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_6_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_7_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_8_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_9_Total_Raw")
    ]
)
class SocketConsumption:
    def execute(self, module, input):
        now = datetime.now().astimezone()

        raw_item_name = input["event"].getItemName()
        real_item_name = "{}Consumption".format(raw_item_name[:-3])

        new_item_value = input["event"].getItemState().doubleValue()
        old_item_value = input["event"].getOldItemState().doubleValue()

        if new_item_value < old_item_value:
            if abs(new_item_value - old_item_value) <= 0.002:
                self.logger.info("Item {} ignored. {} => {}".format(raw_item_name, old_item_value, new_item_value))
                return
            else:
                self.logger.info("Item {} resetted. {} => {}".format(raw_item_name, old_item_value, new_item_value))
                old_item_value = 0

        real_item = Registry.getItem(real_item_name)

        diff = new_item_value - old_item_value
        real_item_value = real_item.getState().doubleValue() + diff
        real_item.postUpdate(real_item_value)

        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        old_daily_item_value = ToolboxHelper.getPersistedState(real_item, start_of_the_day ).doubleValue()
        Registry.getItem("{}Daily_Consumption".format(real_item_name[:-17])).postUpdate(real_item_value - old_daily_item_value)
