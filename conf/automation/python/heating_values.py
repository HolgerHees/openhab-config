from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, SystemStartlevelTrigger
from openhab.actions import Transformation

from datetime import datetime, timedelta

from shared.toolbox import ToolboxHelper

import scope


@rule(
    triggers = [
        GenericCronTrigger("0 */5 * * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_S_Fehlerfrei")
    ]
)
class ErrorMessage:
    def execute(self, module, input):
        if Registry.getItemState("pGF_Utilityroom_Heatpump_S_Fehlerfrei").intValue() == 0:
            Registry.getItem("eOther_Error_Heating_Message").postUpdateIfDifferent(Transformation.transform("MAP", "heatpump_fehlerliste.map", Registry.getItemState("pGF_Utilityroom_Heatpump_S_Fehler").toString() ))
            return

        Registry.getItem("eOther_Error_Heating_Message").postUpdateIfDifferent("")

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Auto_Mode"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_S_Betriebstatusanzeige")
    ]
)
class SummaryMessage:
    def execute(self, module, input):
        mode = Registry.getItemState("pGF_Utilityroom_Heatpump_Auto_Mode")
        status = Registry.getItemState("pGF_Utilityroom_Heatpump_S_Betriebstatusanzeige")

        msg = "{} - {}".format(Transformation.transform("MAP", "heatpump_mode.map", mode.toString()), Transformation.transform("MAP", "heatpump_betriebstatusanzeige.map", status.toString()))

        Registry.getItem("pGF_Utilityroom_Heatpump_Summary_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_S_Betriebstatusanzeige"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_WP_Leistungsanforderung"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_Vorlaufsolltemperatur")
    ]
)
class HeatpumpState:
    def execute(self, module, input):
        wp_status = Registry.getItemState("pGF_Utilityroom_Heatpump_S_Betriebstatusanzeige").intValue()
        wp_power = Registry.getItemState("pGF_Utilityroom_Heatpump_WP_Leistungsanforderung").doubleValue()

        ww_status = hw_status = hk2_status = scope.OFF
        if wp_power > 0:
            if wp_status == 20:
                ww_status = scope.ON
            elif wp_status == 19:
                hw_status = scope.ON

        if wp_status == 19 and Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_Vorlaufsolltemperatur").doubleValue() > 20.0:
            #temperature_pipe_out = Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Pipe_Out").doubleValue()
            #temperature_pipe_in = Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Pipe_In").doubleValue()
            #if temperature_pipe_out - temperature_pipe_in > 1.0:
            hk2_status = scope.ON

        Registry.getItem("pGF_Utilityroom_Heatpump_HK2_State").postUpdateIfDifferent(hk2_status)
        Registry.getItem("pGF_Utilityroom_Heatpump_HW_State").postUpdateIfDifferent(hw_status)
        Registry.getItem("pGF_Utilityroom_Heatpump_WW_State").postUpdateIfDifferent(ww_status)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_State"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_Volumenstrom"),
    ]
)
class HeatpumpInfo:
    def execute(self, module, input):
        hk2_state = Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_State") == scope.ON
        hk2_volume = Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_Volumenstrom").doubleValue()

        if hk2_state and hk2_volume > 0:
            info = "Pumpe an und HK {:.1f} l/min".format(hk2_volume)
        elif hk2_state:
            info = "Pumpe an und HK aus"
        elif hk2_volume > 0:
            info = "Pumpe aus und HK an"
        else:
            info = "Pumpe aus und HK aus"
        Registry.getItem("pGF_Utilityroom_Heatpump_HK2_Info").postUpdateIfDifferent(info)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Pipe_Out"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_Vorlauftemperatur"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_Vorlaufsolltemperatur")
    ]
)
class HeatpumpVorlaufInfo:
    def execute(self, module, input):
        vorlauf_sensor = Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Pipe_Out").doubleValue()
        vorlauf_ist_wp = Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_Vorlauftemperatur").doubleValue()
        vorlauf_soll_wp = Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_Vorlaufsolltemperatur").doubleValue()

        Registry.getItem("pGF_Utilityroom_Heatpump_HK2_Vorlauf_Info").postUpdateIfDifferent("{:.1f}/{:.1f} ({:.1f}) °C".format(vorlauf_sensor, vorlauf_ist_wp, vorlauf_soll_wp))

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_WW_Warmwassertemperatur"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_WW_Warmwassersolltemperatur")
    ]
)
class HeatpumpWarmwasserInfo:
    def execute(self, module, input):
        ist_wp = Registry.getItemState("pGF_Utilityroom_Heatpump_WW_Warmwassertemperatur").doubleValue()
        soll_wp = Registry.getItemState("pGF_Utilityroom_Heatpump_WW_Warmwassersolltemperatur").doubleValue()

        Registry.getItem("pGF_Utilityroom_Heatpump_WW_Info").postUpdateIfDifferent("{:.1f} ({:.1f}) °C".format(ist_wp, soll_wp))

@rule(
    triggers = [
        #SystemStartlevelTrigger(80),
        GenericCronTrigger("0 */15 * * * ?")
    ]
)
class HeatpumpSolarEnergy:
    def execute(self, module, input):
        now = datetime.now().astimezone()
        energy_in_watt_second = Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Power").getPersistence("jdbc").riemannSumBetween(now - timedelta(minutes=15), now).doubleValue()

        energy = round(energy_in_watt_second / 60 / 60 / 1000, 3) # W/s => kW/h

        #self.logger.info("SOLAR THERMIE DEBUG: ENERGY: {:.3f}".format(energy))

        zaehler_stand_current = Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Energy_Total").doubleValue()
        zaehler_stand_current += energy

        Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Energy_Total").postUpdate(zaehler_stand_current)

        zaehler_stand_heute_morgen = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heatpump_Solar_Energy_Total", now.replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue()
        Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Energy_Daily").postUpdateIfDifferent(zaehler_stand_current - zaehler_stand_heute_morgen)

#now = datetime.now().astimezone()
#energy_in_watt_second = Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Power").getPersistence("jdbc").riemannSumBetween(now - timedelta(minutes=1), now).doubleValue()
#print(energy_in_watt_second)
#print(round(energy_in_watt_second / 60 / 60 / 1000, 3))

#start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
#Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Energy_Total").getPersistence("jdbc").persist(start_of_the_day, 0)
#print(ToolboxHelper.getPersistedState("pGF_Utilityroom_Heatpump_Solar_Energy_Total", datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0) ).doubleValue())
#print(Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Energy_Total").doubleValue())

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Solar_Temperature_Vorlauf"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Solar_Temperature_Ruecklauf")
    ]
)
class HeatpumpSolarInfo:
    def execute(self, module, input):
        messured_power = Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Power_Current_Test").doubleValue()
        pump_level = Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Pump_State").intValue()

        vorlauf = Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Temperature_Vorlauf").doubleValue()
        ruecklauf = Registry.getItemState("pGF_Utilityroom_Heatpump_Solar_Temperature_Ruecklauf").doubleValue()
        temp_diff = vorlauf - ruecklauf
        if temp_diff < 0:
            temp_diff = 0

        if pump_level == 0:
          current_flow = 0
          #self.logger.info("SOLAR THERMIE DEBUG: INACTIVE")
        else:
          max_flow = 240 / 60 # l/min
          current_flow = ( pump_level * max_flow / 100.0 )


        #self.logger.info(str(current_flow))
        Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Flow").postUpdate(current_flow)

        calculated_power = round(((current_flow * 3.7 * temp_diff) / 60) * 1000)

        Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Power").postUpdate(calculated_power)

        #self.logger.info("SOLAR THERMIE DEBUG: MESSURED POWER: {:.1f}, CALC POWER: {:.1f}, Flow: {:.1f}, Vorlauf: {:.1f}, Rücklauf: {:.1f}, Diff: {:.1f}, Pump Level: {:.1f}".format(messured_power, calculated_power, current_flow, vorlauf, ruecklauf, temp_diff, pump_level))

Registry.getItem("pGF_Utilityroom_Heatpump_Solar_Flow").postUpdate(2.1)
