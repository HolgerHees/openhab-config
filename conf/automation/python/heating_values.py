from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, SystemStartlevelTrigger
from openhab.actions import Transformation

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
