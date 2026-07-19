from openhab import rule, logger, Registry
from openhab.triggers import ItemCommandTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger, GenericCronTrigger, SystemStartlevelTrigger
from openhab.actions import Transformation

from shared.toolbox import ToolboxHelper
from shared.timer import Timer

from custom.presence import PresenceHelper
from custom.weather import WeatherHelper
from custom.heating import HeatingHelper

from datetime import datetime, timedelta
import math

import scope


DELAYED_UPDATE_TIMEOUT = 3

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Utilityroom_Ventilation_Error_Reset")
    ]
)
class StateReset:
    def execute(self, module, input):
        Registry.getItem(input['event'].getItemName()).postUpdateIfDifferent(scope.OFF)

#@rule(
#    triggers = [
#        SystemStartlevelTrigger(80),
#        ThingStatusChangeTrigger("comfoair:comfoair:default")
#    ]
#)
#class ErrorMessage:
#    def execute(self, module, input):
#        thing = Registry.getThing("comfoair:comfoair:default")
#        status = thing.getStatus()
#        if status.toString() != "ONLINE":
#            info = thing.getStatusInfo()
#            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent("Thing: {}".format( info.toString() ))
#        elif Registry.getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
#            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent( Registry.getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() )
#        else:
#            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent("")

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Error"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Dirty")
    ]
)
class StateMessage:
    def execute(self, module, input):
        if Registry.getItemState("pGF_Utilityroom_Ventilation_Error") == scope.ON:
            msg = "Error"
        elif Registry.getItemState("pGF_Utilityroom_Ventilation_Filter_Dirty") == scope.ON:
            msg = "Filter"
        else:
            msg = "Alles ok"
        Registry.getItem("pGF_Utilityroom_Ventilation_State_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Auto_Mode"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Fan_Level"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Headpump_Status")
    ]
)
class SummaryMessage:
    def execute(self, module, input):
        mode = Registry.getItemState("pGF_Utilityroom_Ventilation_Auto_Mode")
        fan_level = Registry.getItemState("pGF_Utilityroom_Ventilation_Fan_Level")
        status = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Headpump_Status")

        msg = "{} - Stufe {} - {}".format("Manuel" if mode == scope.OFF else "Auto", fan_level, Transformation.transform("MAP", "ventilation_clime_state.map", status.toString()))

        Registry.getItem("pGF_Utilityroom_Ventilation_Summary_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Incomming_Airflow"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Outgoing_Airflow")
    ]
)
class AirflowMessage:
    def execute(self, module, input):
        incomming = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Incomming_Airflow")
        outgoing = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Outgoing_Airflow")

        msg = "→ {}m³/h, ← {}m³/h".format(incomming.format("%d"),outgoing.format("%d"))

        Registry.getItem("pGF_Utilityroom_Ventilation_Airflow_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Target_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Target_Temperature")
    ]
)
class TargetTemperatureMessage:
    def execute(self, module, input):
        target_ventilation = Registry.getItemState("pGF_Utilityroom_Ventilation_Target_Temperature")
        target_clime = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Target_Temperature")

        msg = "{}°C (Lüftung), {}°C (Klima)".format(target_ventilation.format("%.1f"),target_clime.format("%.1f"))

        Registry.getItem("pGF_Utilityroom_Ventilation_Target_Temperature_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Supply_Temperature"),
        ItemStateChangeTrigger("pGF_Livingroom_Air_Sensor_Temperature_Value"),
        ItemStateChangeTrigger("pFF_Bedroom_Air_Sensor_Temperature_Value")
    ]
)
class CoolingTemperatureMessage:
    def execute(self, module, input):
        supply_temperature = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Supply_Temperature")
        livingroom_temperature = Registry.getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value")
        bedroom_temperature = Registry.getItemState("pFF_Bedroom_Air_Sensor_Temperature_Value")

        msg = "{}°C → {}°C (WZ), {}°C (SZ)".format(supply_temperature.format("%.1f"),livingroom_temperature.format("%.1f"),bedroom_temperature.format("%.1f"))

        Registry.getItem("pGF_Utilityroom_Ventilation_Cooling_Temperature_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Supply_Fan_Speed"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Exhaust_Fan_Speed")
    ]
)
class FanSpeedMessage:
    def execute(self, module, input):
        supply = Registry.getItemState("pGF_Utilityroom_Ventilation_Supply_Fan_Speed")
        exhaust = Registry.getItemState("pGF_Utilityroom_Ventilation_Exhaust_Fan_Speed")

        msg = "→ {}%, ← {}%".format(supply.format("%d"),exhaust.format("%d"))

        Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Speed_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
    ]
)
class Efficiency:
    def execute(self, module, input):
        efficiency = 0

        if Registry.getItemState("pGF_Utilityroom_Ventilation_Bypass_State").intValue() == 0:
            temp_out_in_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature")
            temp_in_out_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
            temp_in_in_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature")
            if temp_out_in_state == scope.UNDEF or temp_in_out_state == scope.UNDEF or temp_in_in_state == scope.UNDEF :
                return

            temp_out_in = temp_out_in_state.doubleValue()
            temp_in_out = temp_in_out_state.doubleValue()
            if temp_in_out != temp_out_in:
                efficiency = ( temp_in_in_state.doubleValue() - temp_out_in ) / ( temp_in_out - temp_out_in ) * 100
                efficiency = round( efficiency );
            else:
                efficiency = 100
        else:
            efficiency = 0

        Registry.getItem("pGF_Utilityroom_Ventilation_Bypass_Efficiency").postUpdateIfDifferent(efficiency )

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Humidity"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Humidity")
    ]
)
class OutdoorTemperatureMessage:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        incoming_t_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature")
        outgoing_t_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature")
        incoming_h_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Humidity")
        outgoing_h_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Humidity")

        msg = "→ {}°C ({} %), ← {}°C ({} %)".format(incoming_t_state.format("%.1f"), incoming_h_state.format("%d"), outgoing_t_state.format("%.1f"), outgoing_h_state.format("%d"))
        Registry.getItem("pGF_Utilityroom_Ventilation_Outdoor_Temperature_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        #SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Humidity"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Humidity")
    ]
)
class IndoorTemperatureMessage:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        incoming_t_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature")
        outgoing_t_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
        incoming_h_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Humidity")
        outgoing_h_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Humidity")

        msg = "→ {}°C ({} %), ← {}°C ({} %)".format(incoming_t_state.format("%.1f"), incoming_h_state.format("%d"), outgoing_t_state.format("%.1f"), outgoing_h_state.format("%d"))
        Registry.getItem("pGF_Utilityroom_Ventilation_Indoor_Temperature_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

#@rule(
#    triggers = [
#        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Incoming"),
#        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outgoing")
#    ]
#)
#class FilterMessage:
#    def __init__(self):
#        self.update_timer = None
#
#    def delayUpdate(self):
#        incoming_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Incoming")
#        outgoing_state = Registry.getItemState("pGF_Utilityroom_Ventilation_Outgoing")
#        if incoming_state == scope.UNDEF or outgoing_state == scope.UNDEF:
#                return
#
#        msg = "→ {}%, ← {}%".format(incoming_state.toString(),outgoing_state.toString())
#        Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Message").postUpdateIfDifferent(msg)
#
#        self.update_timer = None
#
#    def execute(self, module, input):
#        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        GenericCronTrigger("0 */1 * * * ?"),
#        GenericCronTrigger("*/15 * * * * ?"),
        ItemStateChangeTrigger("pOther_Presence_State"),

        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Auto_Mode", state=scope.ON),
        ItemCommandTrigger("pGF_Utilityroom_Ventilation_Fan_Level"),

        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Auto_Mode"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Target_Temperature"),
        ItemStateChangeTrigger("pGF_Livingroom_Air_Sensor_Temperature_Value")
    ]
)
class FanLevel:
    def __init__(self):
        self.last_refresh = None

    def execute(self, module, input):
        if Registry.getItemState("pGF_Utilityroom_Ventilation_Auto_Mode") == scope.OFF:
            return

        eventSourceItem = input['event'].getItemName() if input['event'].getType() != "TimerEvent" else None
        current_level = new_level = Registry.getItemState("pGF_Utilityroom_Ventilation_Fan_Level").intValue()

        if eventSourceItem == "pGF_Utilityroom_Ventilation_Fan_Level":
            if "FanLevelAutomatic" in input['event'].getSource():
                return
            Registry.getItem("pGF_Utilityroom_Ventilation_Auto_Mode").postUpdate(scope.OFF)
        else:
            outdoor_temperature = WeatherHelper.getTemperatureStableItemState(900).doubleValue()

            now = datetime.now().astimezone()

            # antifreeze
            if outdoor_temperature <= -10.0:
                new_level = 0
            elif outdoor_temperature <= -5.0:
                new_level = 1
            else:
                indoor_temperature = ToolboxHelper.getStableState("pGF_Livingroom_Air_Sensor_Temperature_Value", 900).doubleValue()

                presence_state = Registry.getItemState("pOther_Presence_State").intValue()

                # Sleep
                if presence_state in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                    new_level = 1
                # Away since 60 minutes
                elif presence_state in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT] and Registry.getItem("pOther_Presence_State").getLastStateChange() < ( now - timedelta(minutes=60) ):
                    new_level = 1
                else:
                    new_level = 2

                    # possible boost for cooling
                    hour = now.hour
                    if hour >= 7 and hour < 22:
                        diff = indoor_temperature - Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Target_Temperature").doubleValue()

                        is_cooling = Registry.getItemState("pGF_Utilityroom_Heatpump_Auto_Mode").intValue() == HeatingHelper.STATE_MODE_COOLING

                        # => is_cooling => true => starts if 1 °C too warm
                        # => is_cooling => false => starts if 1 + diff_offset (2) °C too warm
                        diff_offset = 0 if is_cooling else 2
                        if diff > 1.0 + diff_offset: # activate if temp is 1.0°C to warm
                            new_level = 3
                        elif diff > 0.5 + diff_offset and current_level == 3:  # stay activate if temp is still 0.5°C to warm
                            new_level = 3

            if new_level != current_level:
                # 1. 'event' in input.keys() is an presence or auto mode change
                # 2. is cron triggered event
                # => .getLastChange check to prevent level flapping on temperature changes
                if eventSourceItem == "pGF_Utilityroom_Ventilation_Auto_Mode" or Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Level").getLastStateChange() < ( now - timedelta(minutes=15) ):
                    self.last_refresh = now
                    Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Level").sendCommand(new_level, "FanLevelAutomatic")
                else:
                    self.logger.info("Delayed ventilation fan level change")
            elif current_level != 2:
                if (self.last_refresh is None or (now - self.last_refresh).total_seconds() > 3600):
                    self.last_refresh = now
                    Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Level").sendCommand(current_level, "FanLevelAutomatic")

#Registry.getItem("pGF_Utilityroom_Ventilation_Auto_Mode").sendCommand(scope.ON, "custom_script")
#Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Level").sendCommand(3)

@rule
class ComfortTemperature:
    def buildTriggers(self):
        triggers = []
        for item in Registry.getItem("eOther_Target_Temperatures").getAllMembers():
            triggers.append(ItemStateChangeTrigger(item.getName()))
        return triggers

    def execute(self, module, input):
        max_temperature = 0.0
        for item in Registry.getItem("eOther_Target_Temperatures").getAllMembers():
            temperature = item.getState().floatValue()
            if temperature > max_temperature:
                max_temperature = temperature

        Registry.getItem("pGF_Utilityroom_Ventilation_Target_Mode").sendCommandIfDifferent(2)
        Registry.getItem("pGF_Utilityroom_Ventilation_Target_Temperature").sendCommandIfDifferent(max_temperature)

        offset = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Target_Offset").intValue()
        Registry.getItem("pGF_Utilityroom_Ventilation_Clime_Target_Temperature").sendCommandIfDifferent(max_temperature + offset)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Auto_Mode")
    ]
)
class ComfortCoolingControl:
    def execute(self, module, input):
        season = 2 if Registry.getItemState("pGF_Utilityroom_Heatpump_Auto_Mode").intValue() == 1 else 0
        Registry.getItem("pGF_Utilityroom_Ventilation_Clime_Season").sendCommandIfDifferent(season)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Clime_Target_Offset")
    ]
)
class ComfortOffsetControl:
    def execute(self, module, input):
        target = Registry.getItemState("pGF_Utilityroom_Ventilation_Target_Temperature").doubleValue()
        offset = Registry.getItemState("pGF_Utilityroom_Ventilation_Clime_Target_Offset").intValue()

        Registry.getItem("pGF_Utilityroom_Ventilation_Clime_Target_Temperature").sendCommandIfDifferent(target + offset)

#Registry.getItem("pGF_Utilityroom_Ventilation_Target_Mode").sendCommandIfDifferent(2)
#Registry.getItem("pGF_Utilityroom_Ventilation_Target_Temperature").sendCommandIfDifferent(23.0)

#Registry.getItem("pGF_Utilityroom_Ventilation_Clime_Target_Temperature").sendCommand(23.0)
#Registry.getItem("pGF_Utilityroom_Ventilation_Clime_Control_Season").sendCommand(0)









