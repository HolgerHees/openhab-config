from custom.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger
from core.actions import Mqtt

@rule("sensor_weatherstation.py")
class BatteryMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Battery_Level"),
            ItemStateChangeTrigger("WeatherStation_Battery_Current")
        ]

    def execute(self, module, input):
        msg = u"";
        msg = u"{}{}%, ".format(msg,getItemState("WeatherStation_Battery_Level").format("%d"))
        msg = u"{}{}mA".format(msg,getItemState("WeatherStation_Battery_Current").format("%.1f"))

        postUpdateIfChanged("WeatherStation_Battery_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Rain_Counter"),
            ItemStateChangeTrigger("WeatherStation_Rain_State"),
            ItemStateChangeTrigger("WeatherStation_Rain_Heater")
        ]

    def execute(self, module, input):
        zaehlerNeu = getItemState("WeatherStation_Rain_Counter").intValue()
        zaehlerAlt = getHistoricItemState("WeatherStation_Rain_Counter", getNow().withTimeAtStartOfDay()).intValue()
        todayRain = 0
        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            todayRain = float(differenz) * 295.0 / 1000.0
            todayRain = round(todayRain * 10.0) / 10.0
        postUpdateIfChanged("WeatherStation_Rain_Daily", todayRain)

        if getItemState("WeatherStation_Rain_State").intValue() == 0:
            rainState = "Trocken"
        elif getItemState("WeatherStation_Rain_State").intValue() < 3:
            rainState = "Leicht"
        elif getItemState("WeatherStation_Rain_State").intValue() < 6:
            rainState = "Mittel"
        elif getItemState("WeatherStation_Rain_State").intValue() < 9:
            rainState = "Stark"
        else:
            rainState = "Extrem"
      
        msg = u"";
        msg = u"{}{}".format(msg,"{}mm, ".format(todayRain) if todayRain > 0 else "" )
        msg = u"{}{}, ".format(msg,rainState)
        msg = u"{}{}".format(msg,"An" if getItemState("WeatherStation_Rain_Heater").intValue() == 1 else "Aus" )

        postUpdateIfChanged("WeatherStation_Rain_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationRainCounterRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Rain_Amount")
        ]

    def execute(self, module, input):
        counter = getItemState("WeatherStation_Rain_Counter").intValue();
        counter += getItemState("WeatherStation_Rain_Amount").intValue();

        postUpdateIfChanged("WeatherStation_Rain_Counter", counter)

@rule("sensor_weatherstation.py")
class WeatherstationRainLastHourRule:
    def __init__(self):
        self.triggers = [CronTrigger("0 0 * * * ?")]

    def execute(self, module, input):
        zaehlerNeu = getItemState("WeatherStation_Rain_Counter").intValue()
        zaehlerAlt = getHistoricItemState("WeatherStation_Rain_Counter", getNow().minusHours(1)).intValue()
        lastHourRain = 0

        if zaehlerAlt != zaehlerNeu:
            differenz = zaehlerNeu - zaehlerAlt
            if differenz < 0:
                differenz = zaehlerNeu

            lastHourRain = float(differenz) * 295.0 / 1000.0
            #0.2794 mm

        postUpdateIfChanged("WeatherStation_Rain_Current", lastHourRain)
        
@rule("sensor_weatherstation.py")
class WeatherstationRainHeaterRule:
    def __init__(self):
        self.triggers = [
            ItemStateUpdateTrigger("WeatherStation_Rain_Heater_Request")
        ]

    def execute(self, module, input):
        Mqtt.publish("mosquitto","mysensors-sub-1/1/4/1/0/2",getItemState("WeatherStation_Rain_Heater").toString());

@rule("sensor_weatherstation.py")
class WeatherstationWindMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("WeatherStation_Wind_Speed"),
            ItemStateChangeTrigger("WeatherStation_Wind_Direction")
        ]

    def execute(self, module, input):
        msg = u""
        if getItemState("WeatherStation_Wind_Speed").intValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("WeatherStation_Wind_Speed").format("%.1f"),getItemState("WeatherStation_Wind_Direction").toString())

        postUpdateIfChanged("WeatherStation_Wind_Message", msg)
        
@rule("sensor_weatherstation.py")
class WeatherstationAir1MessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature1"),
            ItemStateChangeTrigger("WeatherStation_Humidity1")
        ]

    def execute(self, module, input):
        msg = u"";
        msg = u"{}{}°C, ".format(msg,getItemState("WeatherStation_Temperature1").format("%.1f"))
        msg = u"{}{}%".format(msg,getItemState("WeatherStation_Humidity1").format("%.1f"))

        postUpdateIfChanged("WeatherStation_Air1_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationAir2MessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature2"),
            ItemStateChangeTrigger("WeatherStation_Humidity2")
        ]

    def execute(self, module, input):
        msg = u"";
        msg = u"{}{}°C, ".format(msg,getItemState("WeatherStation_Temperature2").format("%.1f"))
        msg = u"{}{}%".format(msg,getItemState("WeatherStation_Humidity2").format("%.1f"))

        postUpdateIfChanged("WeatherStation_Air2_Message", msg)

@rule("sensor_weatherstation.py")
class UVMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_UV_Index"),
            ItemStateChangeTrigger("WeatherStation_UV_A"),
            ItemStateChangeTrigger("WeatherStation_UV_B")
        ]

    def execute(self, module, input):
        msg = u"";
        msg = u"{}{} (".format(msg,getItemState("WeatherStation_UV_Index").format("%.1f"))
        msg = u"{}{}a,".format(msg,getItemState("WeatherStation_UV_A").format("%.1f"))
        msg = u"{}{}b)".format(msg,getItemState("WeatherStation_UV_B").format("%.1f"))

        postUpdateIfChanged("WeatherStation_UV_Message", msg)
