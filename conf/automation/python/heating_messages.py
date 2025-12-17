from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper
from shared.timer import Timer

from datetime import datetime


DELAYED_UPDATE_TIMEOUT = 3

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Power"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Circuit_Pump_Speed")
    ]
)
class Power:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "{}%, {}%".format(Registry.getItemState("pGF_Utilityroom_Heating_Power").format("%.0f"),Registry.getItemState("pGF_Utilityroom_Heating_Circuit_Pump_Speed").format("%.0f"))
        Registry.getItem("pGF_Utilityroom_Heating_Power_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Outdoor"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Outdoor_Subdued")
    ]
)
class TemperatureOutdoor:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "{}°C, {}°C".format(Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor").format("%.1f"),Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor_Subdued").format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Heating_Temperature_Outdoor_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Offset"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Offset_Target")
    ]
)
class TemperatureOffset:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "{}°C, {}°C".format(Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Offset").format("%.1f"),Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Offset_Target").format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Heating_Temperature_Offset_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Boiler"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Boiler_Target")
    ]
)
class TemperatureBoiler:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        msg = "{}°C, {}°C".format(Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Boiler").format("%.1f"),Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Boiler_Target").format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Heating_Temperature_Boiler_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        GenericCronTrigger("15 0 0 * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Burner_Starts")
    ]
)
class BurnerStarts:
    def execute(self, module, input):
        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        start = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heating_Burner_Starts", start_of_the_day).intValue()
        current = Registry.getItemState("pGF_Utilityroom_Heating_Burner_Starts").intValue()

        if start > 0 and current > 0:
            difference = current - start
            Registry.getItem("pGF_Utilityroom_Heating_Burner_Starts_Current_Daily").postUpdate(difference)
            msg = "{}, {}".format(difference,current)
            Registry.getItem("pGF_Utilityroom_Heating_Burner_Starts_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        GenericCronTrigger("15 0 0 * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Burner_Hours")
    ]
)
class BurnerHours:
    def execute(self, module, input):
        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        start = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heating_Burner_Hours", start_of_the_day).intValue()
        current = Registry.getItemState("pGF_Utilityroom_Heating_Burner_Hours").intValue()

        if start > 0 and current > 0:
            difference = current - start
            Registry.getItem("pGF_Utilityroom_Heating_Burner_Hours_Current_Daily").postUpdate(difference)
            msg = "{} h, {} h".format(difference,current)
            Registry.getItem("pGF_Utilityroom_Heating_Burner_Hours_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Solar_Collector"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Solar_Storage")
    ]
)
class TemperatureSolar:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        solar_collector = Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Solar_Collector")
        solar_storage = Registry.getItemState("pGF_Utilityroom_Heating_Temperature_Solar_Storage")
        msg = "{}°C, {}°C".format(solar_collector.format("%.1f"),solar_storage.format("%.1f"))
        Registry.getItem("pGF_Utilityroom_Heating_Temperature_Solar_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Pump_State"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Reheating_State")
    ]
)
class SolarState:
    def __init__(self):
        self.update_timer = None

    def delayUpdate(self):
        if Registry.getItemState("pGF_Utilityroom_Heating_Solar_Pump_State").intValue() == 1:
            msg = "an"
        else:
            msg = "aus"

        msg = msg + ", "

        if Registry.getItemState("pGF_Utilityroom_Heating_Solar_Reheating_State").intValue() == 1:
            msg = msg + "an"
        else:
            msg = msg + "aus"

        Registry.getItem("pGF_Utilityroom_Heating_Solar_State_Message").postUpdateIfDifferent(msg)

        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(DELAYED_UPDATE_TIMEOUT, self.delayUpdate, old_timer = self.update_timer, max_count = 2)

@rule(
    triggers = [
        GenericCronTrigger("15 0 0 * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Hours")
    ]
)
class SolarHours:
    def execute(self, module, input):
        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        start = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heating_Solar_Hours", start_of_the_day).intValue()
        current = Registry.getItemState("pGF_Utilityroom_Heating_Solar_Hours").intValue()

        if start > 0 and current > 0:
            difference = current - start
            msg = "{} h, {} h".format(difference,current)
            Registry.getItem("pGF_Utilityroom_Heating_Solar_Hours_Message").postUpdateIfDifferent(msg)

@rule(
    triggers = [
        GenericCronTrigger("15 0 0 * * ?"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Power")
    ]
)
class SolarPower:
    def execute(self, module, input):
        start_of_the_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)

        start = ToolboxHelper.getPersistedState("pGF_Utilityroom_Heating_Solar_Power", start_of_the_day).intValue()
        current = Registry.getItemState("pGF_Utilityroom_Heating_Solar_Power").intValue()

        if start > 0 and current > 0:
            difference = current - start
            Registry.getItem("pGF_Utilityroom_Heating_Solar_Power_Current_Daily").postUpdate(difference)
            msg = "{} KW, {} KW".format(difference,current)
            Registry.getItem("pGF_Utilityroom_Heating_Solar_Power_Message").postUpdateIfDifferent(msg)
