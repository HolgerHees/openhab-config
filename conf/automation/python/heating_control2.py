from datetime import datetime, timedelta

from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.weather import WeatherHelper

from custom.heating2 import Heating, HeatingLogHelper
from custom.heating2 import BuildingConfig

import scope


heating = Heating(
    rooms = BuildingConfig,

    data_item_name = "pGF_Utilityroom_Heatpump_Data",

    forecast_cloud_cover_item_name = "pOutdoor_WeatherService_Cloud_Cover",
    forecast_temperature_item_name = "pOutdoor_WeatherService_Temperature",

    ventilation_volume_item_name = "pGF_Utilityroom_Ventilation_Clime_Outgoing_Airflow",
    ventilation_outgoing_temperature_item_name = "pGF_Utilityroom_Ventilation_Extract_Temperature", #"pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"
    ventilation_incoming_temperature_item_name = "pGF_Utilityroom_Ventilation_Supply_Temperature", #"pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"

    heating_state_item_name = "pGF_Utilityroom_Heatpump_HK2_State",
    heating_temperature_pipe_out_item_name = "pGF_Utilityroom_Heatpump_HK2_Temperature_Pipe_Out",
    heating_temperature_pipe_in_item_name = "pGF_Utilityroom_Heatpump_HK2_Temperature_Pipe_In",

    presence_status_item_name = "pOther_Presence_State",
    heating_reduction_item_name = "pOther_Manual_State_Heating",

    temperature_sensor_item_name_placeholder = "p{}_Air_Sensor_Temperature_Value",
    temperature_target_item_name_placeholder = "p{}_Temperature_Desired",

    heating_hk_item_name_placeholder = "p{}_Heating_HK",
    heating_circuit_item_name_placeholder = "p{}_Heating_Circuit",
#    heating_buffer_item_name_placeholder = "p{}_Heating_Charged",
    heating_demand_item_name_placeholder = "p{}_Heating_Demand",
    heating_target_temperature_item_name_placeholder = "p{}_Heating_Temperature_Target"   ,
)

@rule(
    triggers = [
       GenericCronTrigger("0 10 * * * ?")
    ]
)
class HeatingForecastRefresh:
    def execute(self, module, input):
        heating.refreshForecastInterval()

@rule(
    triggers = [
        GenericCronTrigger("10 * * * * ?"),
#        GenericCronTrigger("*/15 * * * * ?"),
#        ItemStateChangeTrigger("pOther_Manual_State_Traveling"),
#        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Mode"),
#        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_State")
    ]
#    , profile_code=True
)
class MainControl:
    def execute(self, module, input):
        self.logger.info("--------: >>>" )

        now = datetime.now().astimezone()

        heating.refreshHeatingInterval(WeatherHelper.getTemperatureItemName(), now)


        measured_radiation_short_term = WeatherHelper.getSolarPowerStableItemState(10).doubleValue()
        measured_radiation_long_term = WeatherHelper.getSolarPowerStableItemState(30).doubleValue()
        #measured_light_level_short_term = WeatherHelper.getLightLevelStableItemState(30).doubleValue()
        measured_light_level_long_term = WeatherHelper.getLightLevelStableItemState(60).doubleValue()

        heating.calculate(measured_radiation_short_term)

        HeatingLogHelper.logCoolingAndRadiations(self.logger, heating, "FC8     ", "8")
        HeatingLogHelper.logCoolingAndRadiations(self.logger, heating, "FC4     ", "4")
        HeatingLogHelper.logCoolingAndRadiations(self.logger, heating, "Current ", "0", measured_radiation_long_term, measured_light_level_long_term)

        self.logger.info("--------: <<<" )
