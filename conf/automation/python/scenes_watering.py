from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger, ItemCommandTrigger, SystemStartlevelTrigger

from custom.watering import WateringHelper

from datetime import datetime, timedelta
import math
import threading

import scope


     # Water usage,  Runtime usage,   Item [2]
circuits = [
    { "usage": 1.0,  "duration": 1.0, "sensor": "Outdoor_Plant_Sensor_Lawn_Streedside", "item": 'pOutdoor_Streetside_Lawn_Watering',    "name": "Rasen vorne" },
    { "usage": 0.33, "duration": 0.5, "sensor": "Outdoor_Plant_Sensor_Hedge_Street",    "item": 'pOutdoor_Streetside_Beds_Watering',    "name": "Beete vorne" },
    { "usage": 0.33, "duration": 0.5, "sensor": "Outdoor_Plant_Sensor_Terrace",         "item": 'pOutdoor_Terrace_Watering',            "name": "Terassenbeete" },
    { "usage": 0.33, "duration": 0.5, "sensor": "Outdoor_Plant_Sensor_Blackberries",    "item": 'pOutdoor_Garden_Back_Watering',        "name": "Brombeeren" },
#    { "usage": 0.33, "duration": 0.5, "sensor": "Outdoor_Plant_Sensor_Bed_Back_Right",    "item": 'pOutdoor_Garden_Back_Watering',        "name": "Blumenwiese hinten rechts" },
    { "usage": 1.0,  "duration": 1.0, "sensor": "Outdoor_Plant_Sensor_Lawn_Back_Left",  "item": 'pOutdoor_Garden_Right_Watering',       "name": "Rasen hinten rechts" },
    { "usage": 1.0,  "duration": 1.0, "sensor": "Outdoor_Plant_Sensor_Lawn_Back_Left",  "item": 'pOutdoor_Garden_Left_Watering',        "name": "Rasen hinten links" }
]

AUTO = False
DEBUG = False

def calculateStack():
    stack = []

    reference_duration = Registry.getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

    for i in range(len(circuits)):
        group = circuits[i]

        if Registry.getItemState(group["item"] + "_Auto") != scope.ON:
            continue

        step = None
        step_pos = 0
        for j in range(len(stack)):
            _step = stack[j]
            if _step["usage"] + group["usage"] <= 1.0:
                step = _step
                step_pos = j
                break

        factor = WateringHelper.getFactor(group["sensor"]) if AUTO else 1.0
        duration = int( math.floor( group["duration"] * reference_duration * factor) )

        if duration == 0:
            continue

        if step is None:
            step = {"usage": group["usage"], "duration": duration, "items": [group["item"]], "started": None, "finished": None}
            stack.append(step)
            step_pos = len(stack) - 1
        else:
            step["usage"] += group["usage"]

            if duration > step["duration"]:
                stack.insert(step_pos + 1, {"usage": group["usage"], "duration": duration - step["duration"], "items": [group["item"]], "started": None, "finished": None})
            elif duration < step["duration"]:
                stack.insert(step_pos + 1, {"usage": step["usage"], "duration": step["duration"] - duration, "items": step["items"][:], "started": None, "finished": None})
                step["duration"] = duration

            step["items"].append(group["item"])

    return stack

@rule()
class Message:
    def buildTriggers(self):
        triggers = [
            SystemStartlevelTrigger(80),
            ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_Duration")
        ]

        for group in circuits:
            triggers.append(ItemStateChangeTrigger(group["item"] + "_Auto"))

            if group["sensor"] is not None:
                triggers.append(ItemStateChangeTrigger("p" + group["sensor"] + "_Soil_Humidity"))

        return triggers

    def execute(self, module, input):
        reference_duration = Registry.getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

        for i in range(len(circuits)):
            group = circuits[i]
            if Registry.getItemState(group["item"] + "_Auto") == scope.ON:
                factor = WateringHelper.getFactor(group["sensor"]) if AUTO else 1.0
                duration = int( math.floor( group["duration"] * reference_duration * factor) )
                Registry.getItem(group["item"] + "_Info").postUpdate("{} min.".format(duration))
            else:
                Registry.getItem(group["item"] + "_Info").postUpdate("inaktiv")

        stack = calculateStack()

        total_duration = 0
        for _step in stack:
            total_duration += _step["duration"]

        #self.logger.info(str(stack))
        #self.logger.info(str(total_duration))

        Registry.getItem("pOutdoor_Watering_Logic_Runtime").postUpdate(total_duration)
        Registry.getItem("pOutdoor_Watering_Logic_Info").postUpdate("{} min.".format(total_duration) if total_duration <= 60 else "{}:{:02d}".format(int(total_duration / 60), int(total_duration % 60)))

@rule(
    triggers = [
        ItemCommandTrigger("pOutdoor_Watering_Logic_Program_Start"),
        ItemStateChangeTrigger("pOutdoor_Watering_Logic_Runtime"),
        GenericCronTrigger("0 0 0 * * ?"),
        SystemStartlevelTrigger(80)
    ]
)
class Control():
    def __init__(self):
        self.progress_timer = None

        self.program_timer = None
        self.program_timer_start = None

    def callbackProgress(self, stack = None):
        #if self.progress_timer is not None and self.progress_timer != timer:
        #    self.logger.info("Cancel Watering Progress Zombie Timer")
        #    return

        if stack is None:
            stack = calculateStack()

            # find running circuites
            active_items = []
            for i in range(len(circuits)):
                group = circuits[i]
                if Registry.getItemState(group["item"] + "_Powered") == scope.ON:
                    active_items.append(group["item"])

            # restore circuites states
            if len(active_items) > 0:
                for step in stack:
                    lastChange = Registry.getItem(step["items"][0] + "_Powered").getLastStateChange()
                    step["started"] = lastChange
                    if set(step["items"]) != set(active_items):
                        step["finished"] = lastChange
                    else:
                        break

        # find active step
        active_runtime = 0
        active_step = None
        for step in stack:
            if step["finished"] is not None:
                continue

            if step["started"] is not None:
                active_runtime = int((datetime.now().astimezone() - step["started"]).total_seconds() / 60)
                if active_runtime >= step["duration"]:
                    step["finished"] = datetime.now().astimezone()
                    continue
            else:
                step["started"] = datetime.now().astimezone()
                active_runtime = 0

            active_step = step
            break

        # no active step => stop program
        if active_step is None:
            Registry.getItem("pOutdoor_Watering_Logic_Program_Start").sendCommand(WateringHelper.STATE_CONTROL_OFF)
            self.progress_timer = None

        # show active step msg and continue
        else:
            names = []
            for i in range(len(circuits)):
                group = circuits[i]
                if group["item"] in active_step["items"]:
                    if DEBUG:
                        self.logger.info("ON {}".format(group["item"]))
                    else:
                        Registry.getItem(group["item"] + "_Powered").sendCommandIfDifferent(scope.ON)
                    names.append(group["name"])

            for i in range(len(circuits)):
                group = circuits[i]
                if group["item"] not in active_step["items"]:
                    if DEBUG:
                        self.logger.info("OFF {}".format(group["item"]))
                    else:
                        Registry.getItem(group["item"] + "_Powered").sendCommandIfDifferent(scope.OFF)

            remaining_runtime = int( math.floor( active_step["duration"] - active_runtime ) )

            name_str = ""
            if len(names) > 1:
                name_str = " & " + names.pop()
            name_str = ", ".join(names) + name_str

            msg = "{} noch {} min".format( name_str, remaining_runtime )

            if DEBUG:
                self.logger.info(msg)

            #self.logger.info(str(msg))
            #self.logger.info(str(stack))

            Registry.getItem("pOutdoor_Watering_Logic_Program_State").postUpdate(msg)

            self.progress_timer = threading.Timer(60.0, self.callbackProgress, args = [stack])
            self.progress_timer.start()

    def initProgram(self, input = None):
        active_program = input['command'].intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Program_Start" else Registry.getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_program == WateringHelper.STATE_CONTROL_OFF:
            for i in range(len(circuits)):
                group = circuits[i]
                if Registry.getItemState(group["item"] + "_Auto") == scope.ON:
                    Registry.getItem(group["item"] + "_Powered").sendCommandIfDifferent(scope.OFF)
            Registry.getItem("pOutdoor_Watering_Logic_Program_State").postUpdate("läuft nicht")
            return
        elif active_program == WateringHelper.STATE_CONTROL_START_NOW:
            self.callbackProgress()
            return

        total_duration = input['event'].getItemState().intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Runtime" else Registry.getItemState("pOutdoor_Watering_Logic_Runtime").intValue()

        now = datetime.now().astimezone()
        if active_program == WateringHelper.STATE_CONTROL_START_MORNING:
            next_start = now.replace(hour=8,minute=0,second=0)
        elif active_program == WateringHelper.STATE_CONTROL_START_EVENING:
            next_start = now.replace(hour=22,minute=0,second=0)

        next_start = next_start - timedelta(minutes=total_duration)

        while next_start < now:
            next_start = next_start + timedelta(hours=24)

        time_span = (next_start - now).total_seconds()

        self.program_timer = threading.Timer(time_span, self.triggerProgramStart)
        self.program_timer.start()
        self.program_timer_start = next_start

        self.updateProgramTimerMsg()

    def updateProgramTimerMsg(self):
        diff = self.program_timer_start.timetuple().tm_yday - datetime.now().astimezone().timetuple().tm_yday
        if diff <= 1:
            offset = "Heute" if diff == 0 else "Morgen"
            msg = "{}, {}".format(offset, self.program_timer_start.strftime("%H:%M"))
        else:
            msg = "Startet {}".format(self.program_timer_start.strftime("%d.%m - %H:%M"))
        Registry.getItem("pOutdoor_Watering_Logic_Program_State").postUpdate(msg)

    def triggerProgramStart(self):
        self.program_timer = None

        active_programm = Registry.getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_programm not in [WateringHelper.STATE_CONTROL_START_MORNING, WateringHelper.STATE_CONTROL_START_EVENING]:
            self.logger.error("Invalid call of triggerProgramStart")
            return

        Registry.getItem("pOutdoor_Watering_Logic_Program_Start").sendCommand(WateringHelper.STATE_CONTROL_START_NOW)

    def execute(self, module, input):
        if input['event'].getType() != "StartlevelEvent":
            if input['event'].getType() == "TimerEvent":
                if self.program_timer is not None:
                    self.updateProgramTimerMsg()
                return

            if input['event'].getItemName() == "pOutdoor_Watering_Logic_Runtime":
                if self.program_timer is None:
                    return

            if self.program_timer != None:
                self.program_timer.cancel()
                self.program_timer = None

            if self.progress_timer is not None:
                self.progress_timer.cancel()
                self.progress_timer = None

            self.initProgram(input)
        else:
            self.initProgram()
