from openhab import rule, Registry, logger
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper

from datetime import datetime, timedelta

import scope


# offset values for gas meter (total value at the time when knx based impulse counter was resettet)
start_gas_meter_value = 12852.13
#start_gas_meter_value = 12849.42
#start_gas_meter_value = 12770.69
#start_gas_meter_value = 10405.39
start_gas_impulse_counter = 0

#dateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS")

#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Daily_Demand",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_State_Daily_Demand",value)
#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Daily_Supply",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_State_Daily_Supply",value)
#value = ToolboxHelper.getPersistedState("pGF_Utilityroom_Electricity_State_Total_Supply",datetime.now().astimezone()).doubleValue()
#postUpdate("pGF_Utilityroom_Electricity_State_Total_Supply",value)
#value = ToolboxHelper.getPersistedState("pGF_Garage_Solar_Inverter_Power_Limitation",datetime.now().astimezone()).intValue()
#postUpdate("pGF_Garage_Solar_Inverter_Power_Limitation",value)

def getHistoricReference(logger, item_name, value_time, outdated_time, messure_time, interval_time):

    item = Registry.getItem(item_name)
    end_time = item.getLastStateChange()

    now = datetime.now().astimezone()
 
    if end_time == None or end_time < now - timedelta(seconds=outdated_time):
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

        zaehler_stand_saved = Registry.getItemState("pGF_Utilityroom_Gas_Meter_Current_Count",scope.DecimalType(0.0)).doubleValue()
        
        #self.logger.info("{}".format(zaehler_stand_current))
        
        if zaehler_stand_current < zaehler_stand_saved:
            self.logger.error("Consumption: Calculation '{}' is wrong. Set 'start_gas_impulse_counter' to '{}'".format(zaehler_stand_current, zaehler_stand_saved))
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
