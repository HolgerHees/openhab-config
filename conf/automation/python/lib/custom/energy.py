from datetime import datetime, timedelta
from openhab import Registry
from shared.toolbox import ToolboxHelper


class EnergyHelper:
    last_update = {}

    @staticmethod
    def calculateStats(logger, meter_value, meter_offset, total_item, daily_item, annual_current_item, annual_forecast_item, annual_last_year_item, annual_message_item, ndigits = 3, ndigits_message = 0):
        now = datetime.now().astimezone()

        total_old = Registry.getItemState(total_item).doubleValue()
        if meter_offset >= 0:
            total_new = round(meter_value + meter_offset, ndigits)
            if total_new < total_old: # looks like a meter reset
                new_offset = meter_offset + (total_old - total_new)
                #new_offset = total_old - ( total_new - meter_offset)
                logger.error("{}: Calculation is wrong ('{}' < '{}'). Set 'offset' to '{}'".format(total_item, total_new, total_old, new_offset))
                return total_old
        else:
            total_new = round(meter_value, ndigits)
            if total_new < total_old: # looks like a meter reset
                return total_old

        #logger.info("calculateStats item: {}, old: {}, new: {}".format(total_item, total_old, total_new))

        if total_old == total_new and total_item in EnergyHelper.last_update and EnergyHelper.last_update[total_item].date() == now.date():
            #logger.info("SKIP calculateStats of item: {}".format(total_item))
            return total_old

        Registry.getItem(total_item).postUpdate(total_new)
        #logger.info("DEBUG: {} = {}".format(total_item, total_new))

        # *** Current Day ***
        total_value_on_today_morning = ToolboxHelper.getPersistedState(total_item, now.replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        daily = round(total_new - total_value_on_today_morning, ndigits)
        Registry.getItem(daily_item).postUpdate(daily)
        #logger.info("DEBUG: {} = {}".format(daily_item, daily))

        # *** Yearly Values ***
        annual_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        total_on_annual_start = ToolboxHelper.getPersistedState(total_item, annual_start).doubleValue()
        annual_current = round(total_new - total_on_annual_start, 3)

        # *** Current Year ***
        Registry.getItem(annual_current_item).postUpdate(annual_current)
        #logger.info("DEBUG: {} = {}".format(annual_current_item, annual_current))

        if total_on_annual_start == 0:
            annual_forecast = annual_current
            annual_last_year = 0
        else:
            total_one_year_ago = ToolboxHelper.getPersistedState(total_item, now.replace(year=now.year-1) ).doubleValue()
            annual_expected = total_on_annual_start - total_one_year_ago
            annual_forecast = round(annual_current + annual_expected, ndigits)

            total_on_annual_start_one_year_before = ToolboxHelper.getPersistedState(total_item, annual_start.replace(year=annual_start.year-1) ).doubleValue()
            annual_last_year = round(total_on_annual_start - total_on_annual_start_one_year_before, ndigits)

        # *** Current Forecast ***
        Registry.getItem(annual_forecast_item).postUpdateIfDifferent(annual_forecast)
        #logger.info("DEBUG: {} = {}".format(annual_forecast_item, annual_forecast))

        # *** Forecast Message ***
        annual_current_msg = round(annual_current, ndigits_message)
        annual_forcast_msg = round(annual_forecast, ndigits_message)
        msg = "{} / {}".format(annual_current_msg if ndigits_message > 0 else int(annual_current_msg), annual_forcast_msg if ndigits_message > 0 else int(annual_forcast_msg))
        Registry.getItem(annual_message_item).postUpdate(msg)
        #logger.info("DEBUG: {} = {}".format(annual_message_item, msg))

        if total_item in EnergyHelper.last_update and EnergyHelper.last_update[total_item].year != now.year:
            # *** Last Year ***
            Registry.getItem(annual_last_year_item).postUpdateIfDifferent(annual_last_year)
            #logger.info("DEBUG: {} = {}".format(annual_last_year_item, annual_last_year))

        EnergyHelper.last_update[total_item] = now

        return total_new

    @staticmethod
    def calculateJAZ(logger, thermal_value, thermal_item, electric_item, jaz_item):
        end_datetime = datetime.now().astimezone()
        start_datetime = end_datetime.replace(month=9, day=1, hour=0, minute=0, second=0, microsecond=0) if end_datetime.year == 2026 else end_datetime.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        total_thermal_consumption_end = thermal_value #Registry.getItemState(thermal_item).doubleValue()
        total_thermal_consumption_start = ToolboxHelper.getPersistedState(thermal_item, start_datetime).doubleValue()
        thermal_consumption = total_thermal_consumption_end - total_thermal_consumption_start

        total_electrial_consumption_end = Registry.getItemState(electric_item).doubleValue()
        total_electrial_consumption_start = ToolboxHelper.getPersistedState(electric_item, start_datetime).doubleValue()
        electrial_consumption = total_electrial_consumption_end - total_electrial_consumption_start

        Registry.getItem(jaz_item).postUpdateIfDifferent(thermal_consumption / electrial_consumption if electrial_consumption > 0 else 0)


#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Total_Consumption").getPersistence("jdbc").persist(start_of_the_day, 0)

#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Compressor_ActivePower").postUpdate(0)
#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Electric_ActivePower").postUpdate(0)

#Registry.getItem("pGF_Utilityroom_Electricity_State_Heatpump_Heating_Total_Consumption").getPersistence("jdbc").persist(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), 0)
