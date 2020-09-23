from custom.helper import rule, getNow, getItemState, getHistoricItemState, postUpdate, postUpdateIfChanged, startTimer
from core.triggers import CronTrigger, ItemStateChangeTrigger

DELAYED_UPDATE_TIMEOUT = 3

@rule("heating_messages.py")
class HeatingPowerMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Power"),
            ItemStateChangeTrigger("Heating_Circuit_Pump_Speed")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}%, {}%".format(getItemState("Heating_Power").format("%.0f"),getItemState("Heating_Circuit_Pump_Speed").format("%.0f"))
        postUpdateIfChanged("Heating_Power_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("heating_messages.py")
class HeatingTemperatureOutdoorMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Temperature_Outdoor"),
            ItemStateChangeTrigger("Heating_Temperature_Outdoor_Subdued"),
            ItemStateChangeTrigger("Temperature_Garden_Forecast4")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"({}°C) {}°C, {}°C".format(getItemState("Temperature_Garden_Forecast4").format("%.1f"),getItemState("Heating_Temperature_Outdoor").format("%.1f"),getItemState("Heating_Temperature_Outdoor_Subdued").format("%.1f"))
        postUpdateIfChanged("Heating_Temperature_Outdoor_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        if input['event'].getItemName() == "Temperature_Garden_Forecast4":
            self.delayUpdate()
        else:
            self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers) - 1)

@rule("heating_messages.py")
class HeatingTemperatureOffsetMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Temperature_Offset"),
            ItemStateChangeTrigger("Heating_Temperature_Offset_Target")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}°C, {}°C".format(getItemState("Heating_Temperature_Offset").format("%.1f"),getItemState("Heating_Temperature_Offset_Target").format("%.1f"))
        postUpdateIfChanged("Heating_Temperature_Offset_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("heating_messages.py")
class HeatingTemperatureBoilerMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Temperature_Boiler"),
            ItemStateChangeTrigger("Heating_Temperature_Boiler_Target")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}°C, {}°C".format(getItemState("Heating_Temperature_Boiler").format("%.1f"),getItemState("Heating_Temperature_Boiler_Target").format("%.1f"))
        postUpdateIfChanged("Heating_Temperature_Boiler_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("heating_messages.py")
class BurnerStartsRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("Heating_Burner_Starts")
        ]

    def execute(self, module, input):
        start = getHistoricItemState("Heating_Burner_Starts", getNow().withTimeAtStartOfDay()).intValue()
        aktuell = getItemState("Heating_Burner_Starts").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("Heating_Burner_Starts_Current_Daily", differenz)
            msg = u"{}, {}".format(differenz,aktuell)
            postUpdateIfChanged("Heating_Burner_Starts_Message", msg)


@rule("heating_messages.py")
class BurnerHoursRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("Heating_Burner_Hours")
        ]

    def execute(self, module, input):
        start = getHistoricItemState("Heating_Burner_Hours", getNow().withTimeAtStartOfDay()).intValue()
        aktuell = getItemState("Heating_Burner_Hours").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("Heating_Burner_Hours_Current_Daily", differenz)
            msg = u"{} h, {} h".format(differenz,aktuell)
            postUpdateIfChanged("Heating_Burner_Hours_Message", msg)


@rule("heating_messages.py")
class HeatingTemperatureSolarMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Temperature_Solar_Collector"),
            ItemStateChangeTrigger("Heating_Temperature_Solar_Storage")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        solarCollector = getItemState("Heating_Temperature_Solar_Collector")
        solarStorage = getItemState("Heating_Temperature_Solar_Storage")
        msg = u"{}°C, {}°C".format(solarCollector.format("%.1f"),solarStorage.format("%.1f"))
        postUpdateIfChanged("Heating_Temperature_Solar_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule("heating_messages.py")
class HeatingSolarStateMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Heating_Solar_Pump_State"),
            ItemStateChangeTrigger("Heating_Solar_Reheating_State")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        if getItemState("Heating_Solar_Pump_State").intValue() == 1:
            msg = "an"
        else:
            msg = "aus"

        msg = msg + ", "

        if getItemState("Heating_Solar_Reheating_State").intValue() == 1:
            msg = msg + "an"
        else:
            msg = msg + "aus"

        postUpdateIfChanged("Heating_Solar_State_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
 
@rule("heating_messages.py")
class SolarHoursRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("Heating_Solar_Hours")
        ]

    def execute(self, module, input):
        start = getHistoricItemState("Heating_Solar_Hours", getNow().withTimeAtStartOfDay()).intValue()
        aktuell = getItemState("Heating_Solar_Hours").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            msg = u"{} h, {} h".format(differenz,aktuell)
            postUpdateIfChanged("Heating_Solar_Hours_Message", msg)


@rule("heating_messages.py")
class SolarPowerRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("Heating_Solar_Power")
        ]

    def execute(self, module, input):
        start = getHistoricItemState("Heating_Solar_Power", getNow().withTimeAtStartOfDay()).intValue()
        aktuell = getItemState("Heating_Solar_Power").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("Heating_Solar_Power_Current_Daily", differenz)
            msg = u"{} KW, {} KW".format(differenz,aktuell)
            postUpdateIfChanged("Heating_Solar_Power_Message", msg)
