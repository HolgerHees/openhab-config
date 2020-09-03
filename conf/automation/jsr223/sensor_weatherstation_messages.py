from custom.helper import rule, getNow, getItemState, getHistoricItemState, getMaxItemState, postUpdate, postUpdateIfChanged
from core.triggers import CronTrigger, ItemStateChangeTrigger, ItemStateUpdateTrigger
from core.actions import Mqtt

OFFSET_TEMPERATURE_1  = 0.0
OFFSET_HUMIDITY_1     = 0
OFFSET_TEMPERATURE_2  = 1.1
OFFSET_HUMIDITY_2     = 7.5
OFFSET_WIND_DIRECTION = 0

#UVA_RESPONSE_FACTOR = 0.001461
UVA_RESPONSE_FACTOR = 0.002303
#UVB_RESPONSE_FACTOR = 0.002591
UVB_RESPONSE_FACTOR = 0.004686

@rule("sensor_weatherstation.py")
class WeatherstationBatteryMessageRule:
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
            ItemStateChangeTrigger("WeatherStation_Wind_Direction_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Wind_Direction_Raw":
            direction = input['event'].getItemState().intValue() + OFFSET_WIND_DIRECTION
            postUpdate("WeatherStation_Wind_Direction",direction)
        else:
            direction = getItemState("WeatherStation_Wind_Direction").intValue()

        msg = u""
        if getItemState("WeatherStation_Wind_Speed").intValue() == 0:
            msg = u"Ruhig"
        else:
            msg = u"{} km/h, {}".format(getItemState("WeatherStation_Wind_Speed").format("%.1f"),direction)

        postUpdateIfChanged("WeatherStation_Wind_Message", msg)
  
@rule("sensor_weatherstation.py")
class WeatherstationAir1MessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature1_Raw"),
            ItemStateChangeTrigger("WeatherStation_Humidity1_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Temperature1_Raw":
            temperature = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_TEMPERATURE_1, 1)
            postUpdate("WeatherStation_Temperature1",temperature)
            humidity = getItemState("WeatherStation_Humidity1").intValue()
        else:
            temperature = getItemState("WeatherStation_Temperature1").format("%.1f")
            humidity = input['event'].getItemState().intValue() + OFFSET_HUMIDITY_1
            postUpdate("WeatherStation_Humidity1",humidity)
      
        msg = u"";
        msg = u"{}{}°C, ".format(msg,temperature)
        msg = u"{}{}%".format(msg,humidity)

        postUpdateIfChanged("WeatherStation_Air1_Message", msg)

@rule("sensor_weatherstation.py")
class WeatherstationAir2MessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_Temperature2_Raw"),
            ItemStateChangeTrigger("WeatherStation_Humidity2_Raw")
        ]

    def execute(self, module, input):
        if input['event'].getItemName() == "WeatherStation_Temperature2_Raw":
            temperature = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_TEMPERATURE_2, 1)
            postUpdate("WeatherStation_Temperature2",temperature)
            humidity = getItemState("WeatherStation_Humidity2").format("%.1f")
        else:
            temperature = getItemState("WeatherStation_Temperature2").format("%.1f")
            humidity = round(round(input['event'].getItemState().doubleValue(),1) + OFFSET_HUMIDITY_2, 1)
            postUpdate("WeatherStation_Humidity2",humidity)
      
        msg = u"";
        msg = u"{}{}°C, ".format(msg,temperature)
        msg = u"{}{}%".format(msg,humidity)

        postUpdateIfChanged("WeatherStation_Air2_Message", msg)

@rule("sensor_weatherstation.py")
class UVMessageRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("WeatherStation_UV_A"),
            ItemStateChangeTrigger("WeatherStation_UV_B")
        ]

    def execute(self, module, input):
      
        uva_state = getItemState("WeatherStation_UV_A");
        uvb_state = getItemState("WeatherStation_UV_B");
        
        uva_weighted = uva_state.doubleValue() * UVA_RESPONSE_FACTOR;
        uvb_weighted = uvb_state.doubleValue() * UVB_RESPONSE_FACTOR;
        uv_index = (uva_weighted + uvb_weighted) / 2.0;
      
        msg = u"";
        msg = u"{}{} (".format(msg,round(uv_index * 10.0) / 10.0)
        msg = u"{}{}a,".format(msg,uva_state.format("%.1f"))
        msg = u"{}{}b)".format(msg,uvb_state.format("%.1f"))

        postUpdateIfChanged("WeatherStation_UV_Message", msg)
