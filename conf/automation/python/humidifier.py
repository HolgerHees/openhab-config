from openhab import rule, Registry
from openhab.triggers import ItemCommandTrigger, ItemStateChangeTrigger, ThingStatusChangeTrigger, SystemStartlevelTrigger, GenericCronTrigger

from shared.toolbox import ToolboxHelper

from custom.presence import PresenceHelper


TARGET_HUMIDITY = 50.0

MAX_SLEEPING_LEVEL = 1
MAX_PRESENT_LEVEL = 3
MAX_AWAY_LEVEL = 3

@rule()
class ThingState:
    def buildTriggers(self):
        self.thing_uid_map = {
            "tuya:tuyaDevice:humidifier_eg": "pGF_Livingroom_Humidifier_Online",
            "tuya:tuyaDevice:humidifier_og": "pFF_Bedroom_Humidifier_Online"
        }

        triggers = [SystemStartlevelTrigger(80)]
        for thing_uid in self.thing_uid_map.keys():
            triggers.append(ThingStatusChangeTrigger(thing_uid))
            #startTimer(self.log, 5, self.check, args=[thing_uid,])
        return triggers

    def check(self, thing_uid):
        thing = Registry.getThing(thing_uid)
        status = thing.getStatus()
        info = thing.getStatusInfo()

        if status is not None and info is not None:
            if status.toString() != "ONLINE":
                if Registry.getItem(self.thing_uid_map[thing_uid]).postUpdateIfDifferent(OFF):
                    self.logger.info("Humidifier State Change: {} - {}".format(status.toString(), info.toString()))
            else:
                Registry.getItem(self.thing_uid_map[thing_uid]).postUpdateIfDifferent(ON)

    def execute(self, module, input):
        if input['event'].getType() == "StartlevelEvent":
            for thing_uid in self.thing_uid_map.keys():
                self.check(thing_uid)
        else:
            self.check(str(input['event'].getThingUID()))

@rule(
    triggers = [
        ItemCommandTrigger("pGF_Livingroom_Humidifier_Filter_Reset"),
        ItemCommandTrigger("pFF_Bedroom_Humidifier_Filter_Reset")
    ]
)
class StateReset:
    def execute(self, module, input):
        Registry.getItem(input['event'].getItemName()).postUpdate(OFF)

@rule(
    triggers = [
        SystemStartlevelTrigger(80),
        ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Replace_Filter"),
        ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Replace_Filter"),
        ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Fault"),
        ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Fault")
    ]
)
class StateMessage:
    def check(self, item_location):
        filterState = Registry.getItemState("{}_Humidifier_Replace_Filter".format(item_location))
        faultState = Registry.getItemState("{}_Humidifier_Fault".format(item_location))

        msg = []
        if filterState == ON:
            msg.append("Filter")

        if faultState.intValue() == 1:
            msg.append("Wasser")

        if len(msg) == 0:
            msg.append("Alles ok")

        msg = ", ".join(msg)

        Registry.getItem("{}_Humidifier_State_Message".format(item_location)).postUpdateIfDifferent(msg)

    def execute(self, module, input):
        if input['event'].getType() == "StartlevelEvent":
            for item_location in ["pGF_Livingroom","pFF_Bedroom"]:
                self.check(item_location)
        else:
            item_location = "_".join(input['event'].getItemName().split("_")[:2])
            self.check(item_location)

@rule()
class Level:
    def buildTriggers(self):
        self.sensor_location_map = {
            "pGF_Livingroom_Air_Sensor_Humidity_Value": "pGF_Livingroom",
            "pGF_Corridor_Air_Sensor_Humidity_Value": "pGF_Livingroom",

            "pFF_Dressingroom_Air_Sensor_Humidity_Value": "pFF_Bedroom",
            "pFF_Bedroom_Air_Sensor_Humidity_Value": "pFF_Bedroom"
        #    "pFF_Corridor_Air_Sensor_Humidity_Value": "pFF_Bedroom"
        }

        self.autoChangeInProgress = {
            "pGF_Livingroom": False,
            "pFF_Bedroom": False
        }

        triggers = [
            GenericCronTrigger("0 * * * * ?"),

            ItemCommandTrigger("pGF_Livingroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pGF_Livingroom_Humidifier_Auto_Mode", state="ON"),

            ItemCommandTrigger("pFF_Bedroom_Humidifier_Speed"),
            ItemStateChangeTrigger("pFF_Bedroom_Humidifier_Auto_Mode", state="ON"),

            ItemStateChangeTrigger("pOther_Presence_State")
        ]
        for sensor in self.sensor_location_map.keys():
            triggers.append(ItemStateChangeTrigger(sensor))
        return triggers

    def execute(self, module, input):
        if input['event'].getType() != "TimerEvent" and "Humidifier_Speed" in input['event'].getItemName():
            item_location = "_".join(input['event'].getItemName().split("_")[:2])

            if self.autoChangeInProgress[item_location]:
                self.autoChangeInProgress[item_location] = False
            else:
                Registry.getItem("{}_Humidifier_Auto_Mode".format(item_location)).postUpdate(OFF)
            return

        if input['event'].getType() == "TimerEvent" or input['event'].getItemName() == "pOther_Presence_State":
            humidifier_locations = list(self.autoChangeInProgress.keys())

            if input['event'].getType() == "TimerEvent":
                for humidifier_location in humidifier_locations:
                    # sometimes, if humidifier items are reloaded humidifier target is falling back to 40%
                    Registry.getItem("{}_Humidifier_Target".format(humidifier_location)).sendCommandIfDifferent("CO")

                    # sometimes, if humidifier was offline for some seconds, state is powered off
                    #Registry.getItem("{}_Humidifier_Power".format(humidifier_location)").sendCommandIfDifferent(ON)
        else:
            if input['event'].getItemName() in self.sensor_location_map:
                humidifier_locations = [ self.sensor_location_map[input['event'].getItemName()] ]
            else:
                humidifier_locations = [ "_".join(input['event'].getItemName().split("_")[:2]) ]

        for humidifier_location in humidifier_locations:
            if Registry.getItemState("{}_Humidifier_Auto_Mode".format(humidifier_location)) == OFF:
                continue

            if Registry.getItemState("{}_Humidifier_Online".format(humidifier_location)) == OFF:
                continue

            currentLevel = int(Registry.getItemState("{}_Humidifier_Speed".format(humidifier_location)).toString()[-1])
            presenceState = Registry.getItemState("pOther_Presence_State").intValue()

            # Sleep
            if presenceState in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                maxLevel = MAX_SLEEPING_LEVEL
            # Away since 60 minutes
            elif presenceState == [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT] and ToolboxHelper.getLastChange("pOther_Presence_State") < ( datetime.now().astimezone() - timedelta(minutes=60) ):
                maxLevel = MAX_AWAY_LEVEL
            else:
                maxLevel = MAX_PRESENT_LEVEL

            humidity = 100
            for sensor, location in self.sensor_location_map.items():
                if humidifier_location != location:
                    continue

                _humidity = Registry.getItemState(sensor).doubleValue()
                if _humidity < humidity:
                    humidity = _humidity

            # slowdown, if humidity >= 55
            # speedup if humidity <= 50
            if TARGET_HUMIDITY - humidity <= (0 - ( 5 if currentLevel > 1 else 0) ):
                newLevel = 1
            # slowdown, if humidity >= 50
            # speedup if humidity <= 45
            elif TARGET_HUMIDITY - humidity <= (5 - ( 5 if currentLevel > 2 else 0) ):
                newLevel = 2
            else:
                newLevel = 3

            #self.logger.info("{} {} {} {}".format(humidifier_location, humidity, currentLevel, newLevel))

            if newLevel > maxLevel:
                newLevel = maxLevel

            if newLevel != currentLevel:
                # 1. input['event'].getType() != "TimerEvent" is an presence or auto mode change
                # 2. is cron triggered event
                # => .getLastChange check to prevent level flapping on humidity changes
                if input['event'].getType() != "TimerEvent" or ToolboxHelper.getLastChange("{}_Humidifier_Speed".format(humidifier_location)) < ( datetime.now().astimezone() - timedelta(minutes=15) ):
                    self.autoChangeInProgress[humidifier_location] = True

                    Registry.getItem("{}_Humidifier_Speed".format(humidifier_location)).sendCommand("level_{}".format(newLevel))
