from marvin.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged
from openhab.triggers import CronTrigger, ItemStateChangeTrigger

infoConfig = [
    ["Air_FF_Livingroom_Message", "Temperature_FF_Livingroom", "Humidity_FF_Livingroom", "Heating_Temperature_Livingroom_Target"],
    ["Air_FF_Boxroom_Message", "Temperature_FF_Boxroom", "Humidity_FF_Boxroom", None],
    ["Air_FF_Guestroom_Message", "Temperature_FF_Guestroom", "Humidity_FF_Guestroom", None],
    ["Air_FF_GuestWC_Message", "Temperature_FF_GuestWC", "Humidity_FF_GuestWC", None],
    ["Air_FF_Floor_Message", "Temperature_FF_Floor", "Humidity_FF_Floor", None],
    ["Air_FF_Utilityroom_Message", "Temperature_FF_Utilityroom", "Humidity_FF_Utilityroom", None],
    ["Air_FF_Garage_Message", "Temperature_FF_Garage", "Humidity_FF_Garage", None],
    ["Air_SF_Bedroom_Message", "Temperature_SF_Bedroom", "Humidity_SF_Bedroom", "Heating_Temperature_Bedroom_Target"],
    ["Air_SF_Dressingroom_Message", "Temperature_SF_Dressingroom", "Humidity_SF_Dressingroom", None],
    ["Air_SF_Child1_Message", "Temperature_SF_Child1", "Humidity_SF_Child1", None],
    ["Air_SF_Child2_Message", "Temperature_SF_Child2", "Humidity_SF_Child2", None],
    ["Air_SF_Bathroom_Message", "Temperature_SF_Bathroom", "Humidity_SF_Bathroom", None],
    ["Air_SF_Floor_Message", "Temperature_SF_Floor", "Humidity_SF_Floor", None],
    ["Air_SF_Attic_Message", "Temperature_SF_Attic", "Humidity_SF_Attic", None],
    ["Air_Wireless_Message", "Temperature_Wireless", "Humidity_Wireless", None],
    ["Air_Garden_Message", "Temperature_Garden", "Humidity_Garden", None]
]

rawItems = {
    "Temperature_FF_Livingroom": ["Temperature_FF_Livingroom_Raw", -0.1, -1.4],
    "Humidity_FF_Livingroom": ["Humidity_FF_Livingroom_Raw", 7.4, 0.0],
    "Temperature_FF_Boxroom": ["Temperature_FF_Boxroom_Raw", -0.1, -1.4],
    "Humidity_FF_Boxroom": ["Humidity_FF_Boxroom_Raw", 1.9, 0.0],
    "Temperature_FF_Guestroom": ["Temperature_FF_Guestroom_Raw", -0.1, -1.4],
    "Humidity_FF_Guestroom": ["Humidity_FF_Guestroom_Raw", 2.6, 0.0],
    "Temperature_FF_GuestWC": ["Temperature_FF_GuestWC_Raw", 0.1, -1.4],
    "Humidity_FF_GuestWC": ["Humidity_FF_GuestWC_Raw", 0.7, 0.0],
    "Temperature_FF_GuestWC": ["Temperature_FF_GuestWC_Raw", 0.1, -1.4],
    "Humidity_FF_GuestWC": ["Humidity_FF_GuestWC_Raw", 0.7, 0.0],
    "Temperature_FF_Floor": ["Temperature_FF_Floor_Raw", 0.1, -1.4],
    "Humidity_FF_Floor": ["Humidity_FF_Floor_Raw", 4.0, 0.0],
    "Temperature_FF_Utilityroom": ["Temperature_FF_Utilityroom_Raw", -0.1, -1.4],
    "Humidity_FF_Utilityroom": ["Humidity_FF_Utilityroom_Raw", 1.7, 0.0],
    "Temperature_FF_Garage": ["Temperature_FF_Garage_Raw", 0.0, -1.4],
    "Humidity_FF_Garage": ["Humidity_FF_Garage_Raw", 3.6, 0.0],
    "Temperature_SF_Bedroom": ["Temperature_SF_Bedroom_Raw", -0.1, -1.4],
    "Humidity_SF_Bedroom": ["Humidity_SF_Bedroom_Raw", 5.2, 0.0],
    "Temperature_SF_Dressingroom": ["Temperature_SF_Dressingroom_Raw", 0.1, -1.4],
    "Humidity_SF_Dressingroom": ["Humidity_SF_Dressingroom_Raw", 0.4, 0.0],
    "Temperature_SF_Child1": ["Temperature_SF_Child1_Raw", 0.0, -1.4],
    "Humidity_SF_Child1": ["Humidity_SF_Child1_Raw", 1.1, 0.0],
    "Temperature_SF_Child2": ["Temperature_SF_Child2_Raw", 0.1, -1.4],
    "Humidity_SF_Child2": ["Humidity_SF_Child2_Raw", 2.8, 0.0],
    "Temperature_SF_Bathroom": ["Temperature_SF_Bathroom_Raw", 0.1, -1.4],
    "Humidity_SF_Bathroom": ["Humidity_SF_Bathroom_Raw", 5.3, 0.0],
    "Temperature_SF_Floor": ["Temperature_SF_Floor_Raw", 0.3, -1.4],
    "Humidity_SF_Floor": ["Humidity_SF_Floor_Raw", 2.5, 0.0],
    "Temperature_SF_Attic": ["Temperature_SF_Attic_Raw", -0.1, -0.9],
    "Humidity_SF_Attic": ["Humidity_SF_Attic_Raw", 1.9, 0.0]
}


@rule("sensor_temperatures_humidity_messages.py")
class InfoValueRule:
    def __init__(self):
        self.triggers = []
        self.triggerMappings = {}
        self.rawMappings = {}
        for i, entry in enumerate(infoConfig):

            # *** TEMPERATURE ***
            # if exists, map raw temperature trigger
            temperaturItem = entry[1]
            if temperaturItem in rawItems:
                _temperaturItem = temperaturItem
                temperaturItem = rawItems[temperaturItem][0]
                self.rawMappings[temperaturItem]=_temperaturItem

            # add temperature trigger and store infoData index
            self.triggerMappings[temperaturItem]=i
            self.triggers.append(ItemStateChangeTrigger(temperaturItem))

            # *** HUMIDITY ***
            # if exists, map raw humidity trigger
            humidityItem = entry[2]
            if humidityItem in rawItems:
                _humidityItem = humidityItem
                humidityItem = rawItems[humidityItem][0]
                self.rawMappings[humidityItem]=_humidityItem

            # add humidity trigger and store infoData index
            self.triggerMappings[humidityItem]=i
            self.triggers.append(ItemStateChangeTrigger(humidityItem))

            # *** TARGET VALUE ***
            if entry[3] is not None:
                self.triggerMappings[entry[3]]=i
                self.triggers.append(ItemStateChangeTrigger(entry[3]))

    def processRawValue(self, valueItem, rawState, calibrationDiff, finalDiff):
        value = (round(rawState.doubleValue() * 10.0) / 10.0) + calibrationDiff + finalDiff
        return postUpdateIfChanged(valueItem, value)

    def updateInfoMessage(self, infoItem, temperatureItem, humidityItem, temperatureTargetItem=None):
        msg = u"";
        if temperatureTargetItem is not None:
            msg = u"{}({}°C) ".format(msg,getItemState(temperatureTargetItem).format("%.1f"))

        msg = u"{}{}°C, ".format(msg,getItemState(temperatureItem).format("%.1f"))
        msg = u"{}{}%".format(msg,getItemState(humidityItem).format("%.1f"))

        postUpdateIfChanged(infoItem, msg)

    def execute(self, module, input):

        itemName = input['event'].getItemName()

        # was it a raw trigger?
        if itemName in self.rawMappings:
            rawItemName = self.rawMappings[itemName]
            entry = rawItems[ rawItemName ]

            if not self.processRawValue( rawItemName, input['event'].getItemState(), entry[1], entry[2]):
                return

        data = infoConfig[ self.triggerMappings[itemName] ]
        self.updateInfoMessage(data[0], data[1], data[2], data[3])


@rule("sensor_temperatures_humidity_messages.py")
class UpdateRainTodayRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 5 0 * * ?"),
            ItemStateChangeTrigger("Rain_Garden_Counter"),
            ItemStateChangeTrigger("Regen_State_Garden")
        ]

    def execute(self, module, input):
        zaehlerNeu = getItemState("Rain_Garden_Counter").intValue()
        zaehlerAlt = getHistoricItemState("Rain_Garden_Counter", getNow().withTimeAtStartOfDay()).intValue()
        todayRain = 0

        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            todayRain = float(differenz) * 295.0 / 1000.0

        postUpdateIfChanged("Rain_Garden_Current_Daily", todayRain)

        msg = u"{}".format(round(todayRain * 10.0) / 10.0)

        if getItemState("Regen_State_Garden").intValue() == 1:
            msg = u"(Regen) {} mm".format(msg)
        else:
            msg = u"{} mm".format(msg)

        postUpdateIfChanged("Rain_Garden_Message", msg)


@rule("sensor_temperatures_humidity_messages.py")
class UpdateRainLastHourRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 * * * ?")]

    def execute(self, module, input):
        zaehlerNeu = getItemState("Rain_Garden_Counter").intValue()
        zaehlerAlt = getHistoricItemState("Rain_Garden_Counter", getNow().minusHours(1)).intValue()
        lastHourRain = 0

        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            lastHourRain = float(differenz) * 295.0 / 1000.0

        postUpdateIfChanged("Rain_Garden_Current", lastHourRain)


@rule("sensor_temperatures_humidity_messages.py")
class RainConvertRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Wind_Garden")]

    def execute(self, module, input):
        value = round(getItemState("Wind_Garden").doubleValue() * 3.6)

        postUpdateIfChanged("Wind_Garden_Converted", value)


@rule("sensor_temperatures_humidity_messages.py")
class UpdateWindLast15MinutesRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 */15 * * * ?")]

    def execute(self, module, input):
        value = getMaxItemState("Wind_Garden_Converted", getNow().minusMinutes(15)).doubleValue()

        postUpdateIfChanged("Wind_Garden_Current", value)


@rule("sensor_temperatures_humidity_messages.py")
class WindRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Wind_Garden_Converted"),
            ItemStateChangeTrigger("Wind_Direction")
        ]

    def execute(self, module, input):
        msg = u""
        if getItemState("Wind_Garden_Converted").intValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("Wind_Garden_Converted").format("%.1f"),getItemState("Wind_Direction").toString())

        postUpdateIfChanged("Wind_Message", msg)
