from java.time import ZonedDateTime

from shared.helper import rule, getItemState, getHistoricItemState, postUpdate, postUpdateIfChanged, startTimer
from shared.triggers import CronTrigger, ItemStateChangeTrigger


DELAYED_UPDATE_TIMEOUT = 3

@rule()
class HeatingMessagesMessagesPower:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Power"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Circuit_Pump_Speed")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}%, {}%".format(getItemState("pGF_Utilityroom_Heating_Power").format("%.0f"),getItemState("pGF_Utilityroom_Heating_Circuit_Pump_Speed").format("%.0f"))
        postUpdateIfChanged("pGF_Utilityroom_Heating_Power_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class HeatingMessagesTemperatureOutdoor:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Outdoor"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Outdoor_Subdued"),
            ItemStateChangeTrigger("pOutdoor_Weather_Forecast_Temperature_4h")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"({}°C) {}°C, {}°C".format(getItemState("pOutdoor_Weather_Forecast_Temperature_4h").format("%.1f"),getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor").format("%.1f"),getItemState("pGF_Utilityroom_Heating_Temperature_Outdoor_Subdued").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Heating_Temperature_Outdoor_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        if input['event'].getItemName() == "pOutdoor_Weather_Forecast_Temperature_4h":
            self.delayUpdate()
        else:
            self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers) - 1)

@rule()
class HeatingMessagesTemperatureOffset:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Offset"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Offset_Target")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}°C, {}°C".format(getItemState("pGF_Utilityroom_Heating_Temperature_Offset").format("%.1f"),getItemState("pGF_Utilityroom_Heating_Temperature_Offset_Target").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Heating_Temperature_Offset_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class HeatingMessagesTemperatureBoiler:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Boiler"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Boiler_Target")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        msg = u"{}°C, {}°C".format(getItemState("pGF_Utilityroom_Heating_Temperature_Boiler").format("%.1f"),getItemState("pGF_Utilityroom_Heating_Temperature_Boiler_Target").format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Heating_Temperature_Boiler_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class HeatingMessagesBurnerStarts:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Burner_Starts")
        ]

    def execute(self, module, input):
        refDay = ZonedDateTime.now()
        start = getHistoricItemState("pGF_Utilityroom_Heating_Burner_Starts", refDay.toLocalDate().atStartOfDay(refDay.getZone())).intValue()
        aktuell = getItemState("pGF_Utilityroom_Heating_Burner_Starts").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("pGF_Utilityroom_Heating_Burner_Starts_Current_Daily", differenz)
            msg = u"{}, {}".format(differenz,aktuell)
            postUpdateIfChanged("pGF_Utilityroom_Heating_Burner_Starts_Message", msg)


@rule()
class HeatingMessagesBurnerHours:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Burner_Hours")
        ]

    def execute(self, module, input):
        refDay = ZonedDateTime.now()
        start = getHistoricItemState("pGF_Utilityroom_Heating_Burner_Hours", refDay.toLocalDate().atStartOfDay(refDay.getZone())).intValue()
        aktuell = getItemState("pGF_Utilityroom_Heating_Burner_Hours").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("pGF_Utilityroom_Heating_Burner_Hours_Current_Daily", differenz)
            msg = u"{} h, {} h".format(differenz,aktuell)
            postUpdateIfChanged("pGF_Utilityroom_Heating_Burner_Hours_Message", msg)


@rule()
class HeatingMessagesTemperatureSolar:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Solar_Collector"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Temperature_Solar_Storage")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        solarCollector = getItemState("pGF_Utilityroom_Heating_Temperature_Solar_Collector")
        solarStorage = getItemState("pGF_Utilityroom_Heating_Temperature_Solar_Storage")
        msg = u"{}°C, {}°C".format(solarCollector.format("%.1f"),solarStorage.format("%.1f"))
        postUpdateIfChanged("pGF_Utilityroom_Heating_Temperature_Solar_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))

@rule()
class HeatingMessagesSolarState:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Pump_State"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Reheating_State")
        ]
        self.updateTimer = None

    def delayUpdate(self):
        if getItemState("pGF_Utilityroom_Heating_Solar_Pump_State").intValue() == 1:
            msg = "an"
        else:
            msg = "aus"

        msg = msg + ", "

        if getItemState("pGF_Utilityroom_Heating_Solar_Reheating_State").intValue() == 1:
            msg = msg + "an"
        else:
            msg = msg + "aus"

        postUpdateIfChanged("pGF_Utilityroom_Heating_Solar_State_Message", msg)

        self.updateTimer = None

    def execute(self, module, input):
        self.updateTimer = startTimer(self.log,DELAYED_UPDATE_TIMEOUT, self.delayUpdate, oldTimer = self.updateTimer, groupCount = len(self.triggers))
 
@rule()
class HeatingMessagesSolarHours:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Hours")
        ]

    def execute(self, module, input):
        refDay = ZonedDateTime.now()
        start = getHistoricItemState("pGF_Utilityroom_Heating_Solar_Hours", refDay.toLocalDate().atStartOfDay(refDay.getZone())).intValue()
        aktuell = getItemState("pGF_Utilityroom_Heating_Solar_Hours").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            msg = u"{} h, {} h".format(differenz,aktuell)
            postUpdateIfChanged("pGF_Utilityroom_Heating_Solar_Hours_Message", msg)


@rule()
class HeatingMessagesSolarPower:
    def __init__(self):
        self.triggers = [
            CronTrigger("15 0 0 * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Heating_Solar_Power")
        ]

    def execute(self, module, input):
        refDay = ZonedDateTime.now()
        start = getHistoricItemState("pGF_Utilityroom_Heating_Solar_Power", refDay.toLocalDate().atStartOfDay(refDay.getZone())).intValue()
        aktuell = getItemState("pGF_Utilityroom_Heating_Solar_Power").intValue()
        if start > 0 and aktuell > 0:
            differenz = aktuell - start
            postUpdate("pGF_Utilityroom_Heating_Solar_Power_Current_Daily", differenz)
            msg = u"{} KW, {} KW".format(differenz,aktuell)
            postUpdateIfChanged("pGF_Utilityroom_Heating_Solar_Power_Message", msg)
