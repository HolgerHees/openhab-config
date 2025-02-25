from openhab import rule, logger, Registry, Timer
from openhab.triggers import ItemCommandTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger, GenericCronTrigger, SystemStartlevelTrigger

from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper
from custom.weather import WeatherHelper

from datetime import datetime, timedelta
import math


DELAYED_UPDATE_TIMEOUT = 3

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Utilityroom_Ventilation_Filter_Reset"),
        ItemCommandTrigger("pGF_Utilityroom_Ventilation_Error_Reset")
    ]
)
class StateReset:
    def execute(self, module, input):
        Registry.getItem(input['event'].getItemName()).postUpdateIfDifferent(0)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ThingStatusChangeTrigger("comfoair:comfoair:default"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error")
    ]
)
class ErrorMessage:
    def execute(self, module, input):
        thing = Registry.getThing("comfoair:comfoair:default")
        status = thing.getStatus()
        if status.toString() != "ONLINE":
            info = thing.getStatusInfo()
            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent("Thing: {}".format( info.toString() ))
        elif Registry.getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent( Registry.getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() )
        else:
            Registry.getItem("eOther_Error_Ventilation_Message").postUpdateIfDifferent("")

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Error_Message"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Error")
    ]
)
class StateMessage:
    def execute(self, module, input):
        if Registry.getItemState("pGF_Utilityroom_Ventilation_Error_Message").toString() != "No Errors":
            msg = "Error"
        elif Registry.getItemState("pGF_Utilityroom_Ventilation_Filter_Error") == ON:
            msg = "Filter"
        else:
            msg = "Alles ok"

        Registry.getItem("pGF_Utilityroom_Ventilation_State_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
    ]
)
class Efficiency:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        efficiency = 0

        if Registry.getItemState("pGF_Utilityroom_Ventilation_Bypass") == OFF:
            tempOutIn = Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature").doubleValue()
            tempInOut = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").doubleValue()
            tempInIn = Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature").doubleValue()

            if tempInOut != tempOutIn:
                efficiency = ( tempInIn - tempOutIn ) / ( tempInOut - tempOutIn ) * 100
                efficiency = round( efficiency );
            else:
                efficiency = 100
        else:
            efficiency = 0

        Registry.getItem("pGF_Utilityroom_Ventilation_Bypass_Efficiency").postUpdateIfDifferent(efficiency )

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 3)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Filter_Runtime")
    ]
)
class Runtime:
    def execute(self, module, input):
        runtime = input['event'].getItemState().doubleValue()

        weeks = int(math.floor(runtime / 168.0))
        days = int(math.floor((runtime - (weeks * 168.0)) / 24))

        active = []
        if weeks > 0:
            if weeks == 1:
                active.append("1 Woche")
            else:
                active.append("{} Wochen".format(weeks))

        if days > 0:
            if days == 1:
                active.append("1 Tag")
            else:
                active.append("{} Tage".format(days))

        msg = ", ".join(active)

        Registry.getItem("pGF_Utilityroom_Ventilation_Filter_Runtime_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature")
    ]
)
class OutdoorTemperatureMessage:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "→ {}°C, ← {}°C".format(Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Incoming_Temperature").format("%.1f"),Registry.getItemState("pGF_Utilityroom_Ventilation_Outdoor_Outgoing_Temperature").format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Ventilation_Outdoor_Temperature_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature")
    ]
)
class IndoorTemperatureMessage:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "→ {}°C, ← {}°C".format(Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Incoming_Temperature").format("%.1f"),Registry.getItemState("pGF_Utilityroom_Ventilation_Indoor_Outgoing_Temperature").format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Ventilation_Indoor_Temperature_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Incoming"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Outgoing")
    ]
)
class FilterMessage:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "→ {}%, ← {}%".format(Registry.getItemState("pGF_Utilityroom_Ventilation_Incoming").toString(),Registry.getItemState("pGF_Utilityroom_Ventilation_Outgoing").toString())
        Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        GenericCronTrigger("0 */1 * * * ?"),
        ItemCommandTrigger("pGF_Utilityroom_Ventilation_Fan_Level"),
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Auto_Mode", state="ON"),
        ItemStateChangeTrigger("pOther_Presence_State")
    ]
)
class FanLevel:
    def __init__(self):
        self.auto_change_in_progress = False
        self.active_level = -1

    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent" and input['event'].getItemName() == "pGF_Utilityroom_Ventilation_Fan_Level":
            if self.auto_change_in_progress:
                self.auto_change_in_progress = False
            else:
                Registry.getItem("pGF_Utilityroom_Ventilation_Auto_Mode").postUpdate(OFF)
            return

        if Registry.getItemState("pGF_Utilityroom_Ventilation_Auto_Mode") == OFF:
            return

        current_level = Registry.getItemState("pGF_Utilityroom_Ventilation_Fan_Level").intValue()
        if self.active_level == -1:
            self.active_level = current_level

        outdoor_temperature = WeatherHelper.getTemperatureStableItemState(900).doubleValue()

        # antifreeze
        if outdoor_temperature <= -10.0:
            new_level = 1    # Level A
        elif outdoor_temperature <= -5.0:
            new_level = 2    # Level 1
        else:
            indoor_temperature = ToolboxHelper.getStableState("pGF_Livingroom_Air_Sensor_Temperature_Value", 900).doubleValue()
            target_temperature = Registry.getItemState("pGF_Utilityroom_Ventilation_Comfort_Temperature").doubleValue()

            presence_state = Registry.getItemState("pOther_Presence_State").intValue()

            # Sleep
            if presence_state in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                reduced_level = 2    # Level 1
                default_level = 2    # Level 1
                cooling_level = 2    # Level 1
            # Away since 60 minutes
            elif presence_state == [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT] and ToolboxHelper.getLastChange("pOther_Presence_State") < ( datetime.now().astimezone() - timedelta(minutes=60) ):
                reduced_level = 1    # Level A
                default_level = 2    # Level 1
                cooling_level = 3    # Level 2
            else:
                reduced_level = 2    # Level 1
                default_level = 3    # Level 2
                cooling_level = 3    # Level 2

            if indoor_temperature >= target_temperature:
                if outdoor_temperature < indoor_temperature:
                    # cooling_level if it is too warm inside but outside colder then inside
                    new_level = cooling_level
                else:
                    # reduced_level if it is too warm inside and also outside
                    new_level = reduced_level
            else:
                new_level = default_level

        #self.logger.info(str(current_level))
        #self.logger.info(str(new_level))

        if new_level != current_level:
            # 1. self.active_level != current_level means last try was not successful
            # 2. 'event' in input.keys() is an presence or auto mode change
            # 3. is cron triggered event
            # => .getLastChange check to prevent level flapping on temperature changes
            if self.active_level != current_level or input['event'].getType() != "TimerEvent" or ToolboxHelper.getLastChange("pGF_Utilityroom_Ventilation_Fan_Level") < ( datetime.now().astimezone() - timedelta(minutes=15) ):
                self.auto_change_in_progress = True

                Registry.getItem("pGF_Utilityroom_Ventilation_Fan_Level").sendCommand(new_level)
                self.active_level = new_level

@rule()
class ComfortTemperature:
    def buildTriggers(self):
        return ToolboxHelper.getGroupMemberTrigger(ItemStateChangeTrigger, "eOther_Target_Temperatures")

    def execute(self, module, input):
        max_temperature = 0.0
        for item in Registry.getItem("eOther_Target_Temperatures").getAllGroupMembers():
            temperature = item.getState().floatValue()
            if temperature > max_temperature:
                max_temperature = temperature

        Registry.getItem("pGF_Utilityroom_Ventilation_Comfort_Temperature").sendCommandIfDifferent(max_temperature)

