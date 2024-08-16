import math
from java.time import ZonedDateTime, Duration
from java.time.format import DateTimeFormatter
from java.time.temporal import ChronoUnit

from shared.helper import rule, startTimer, getItemState, postUpdate, sendCommand, sendCommandIfChanged, getItemLastChange
from shared.triggers import ItemCommandTrigger, ItemStateChangeTrigger, CronTrigger

from custom.watering import WateringHelper

    # Water usage,  Runtime usage,   Item [2]
circuits = [
    { "usage": 1.0,  "duration": 0.6, "sensor": "Outdoor_Plant_Sensor_Lawn_Streedside", "item": 'pOutdoor_Streetside_Lawn_Watering',    "name": "Rasen vorne" },
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

    referenceDuration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

    for i in range(len(circuits)):
        group = circuits[i]

        if getItemState(group["item"] + "_Auto") != ON:
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
        duration = int( math.floor( group["duration"] * referenceDuration * factor) )

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
class ScenesWateringMessage:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_Duration") ]

        for group in circuits:
            self.triggers.append(ItemStateChangeTrigger(group["item"] + "_Auto"))

            if group["sensor"] is not None:
                self.triggers.append(ItemStateChangeTrigger("p" + group["sensor"] + "_Soil_Humidity"))

        self.process()

    def process(self):
        referenceDuration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

        for i in range(len(circuits)):
            group = circuits[i]
            if getItemState(group["item"] + "_Auto") == ON:
                factor = WateringHelper.getFactor(group["sensor"]) if AUTO else 1.0
                duration = int( math.floor( group["duration"] * referenceDuration * factor) )
                postUpdate(group["item"] + "_Info", u"{} min.".format(duration))
            else:
                postUpdate(group["item"] + "_Info", u"inaktiv")

        stack = calculateStack()

        total_duration = 0
        for _step in stack:
            total_duration += _step["duration"]

        #self.log.info(str(stack))
        #self.log.info(str(total_duration))

        postUpdate("pOutdoor_Watering_Logic_Runtime", total_duration)
        postUpdate("pOutdoor_Watering_Logic_Info", "{} min.".format(total_duration) if total_duration <= 60 else "{}:{:02d}".format(int(total_duration / 60), int(total_duration % 60)))

    def execute(self, module, input):
        self.process()

@rule()
class ScenesWateringControl():
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pOutdoor_Watering_Logic_Program_Start"),
            ItemStateChangeTrigger("pOutdoor_Watering_Logic_Runtime"),
            CronTrigger("0 0 0 * * ?")
        ]

        self.progressTimer = None

        self.programTimer = None
        self.programTimerStart = None

        self.initProgram()

    def callbackProgress(self, stack = None):
        #if self.progressTimer is not None and self.progressTimer != timer:
        #    self.log.info("Cancel Watering Progress Zombie Timer")
        #    return

        if stack is None:
            stack = calculateStack()

            # find running circuites
            active_items = []
            for i in range(len(circuits)):
                group = circuits[i]
                if getItemState(group["item"] + "_Powered") == ON:
                    active_items.append(group["item"])

            # restore circuites states
            if len(active_items) > 0:
                for step in stack:
                    lastChange = getItemLastChange(step["items"][0] + "_Powered")
                    step["started"] = lastChange
                    if set(step["items"]) != set(active_items):
                        step["finished"] = lastChange
                    else:
                        break

        # find active step
        activeRuntime = 0
        activeStep = None
        for step in stack:
            if step["finished"] is not None:
                continue

            if step["started"] is not None:
                activeRuntime = ChronoUnit.MINUTES.between(step["started"], ZonedDateTime.now())
                if activeRuntime >= step["duration"]:
                    step["finished"] = ZonedDateTime.now()
                    continue
            else:
                step["started"] = ZonedDateTime.now()
                activeRuntime = 0

            activeStep = step
            break

        # no active step => stop program
        if activeStep is None:
            sendCommand("pOutdoor_Watering_Logic_Program_Start", WateringHelper.STATE_CONTROL_OFF)
            self.progressTimer = None

        # show active step msg and continue
        else:
            names = []
            for i in range(len(circuits)):
                group = circuits[i]
                if group["item"] in activeStep["items"]:
                    if DEBUG:
                        self.log.info("ON {}".format(group["item"]))
                    else:
                        sendCommandIfChanged(group["item"] + "_Powered", ON)
                    names.append(group["name"])

            for i in range(len(circuits)):
                group = circuits[i]
                if group["item"] not in activeStep["items"]:
                    if DEBUG:
                        self.log.info("OFF {}".format(group["item"]))
                    else:
                        sendCommandIfChanged(group["item"] + "_Powered", OFF)

            remainingRuntime = int( math.floor( activeStep["duration"] - activeRuntime ) )

            name_str = ""
            if len(names) > 1:
                name_str = " & " + names.pop()
            name_str = ", ".join(names) + name_str

            msg = u"{} noch {} min".format( name_str, remainingRuntime )

            if DEBUG:
                self.log.info(msg)

            #self.log.info(str(msg))
            #self.log.info(str(stack))

            postUpdate("pOutdoor_Watering_Logic_Program_State", msg)

            self.progressTimer = startTimer(self.log, 60.0, self.callbackProgress, args = [stack])

    def initProgram(self, input = None):
        active_program = input['command'].intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Program_Start" else getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_program == WateringHelper.STATE_CONTROL_OFF:
            for i in range(len(circuits)):
                group = circuits[i]
                if getItemState(group["item"] + "_Auto") == ON:
                    sendCommandIfChanged(group["item"] + "_Powered", OFF)
            postUpdate("pOutdoor_Watering_Logic_Program_State", u"läuft nicht")
            return
        elif active_program == WateringHelper.STATE_CONTROL_START_NOW:
            self.callbackProgress()
            return

        total_duration = input['event'].getItemState().intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Runtime" else getItemState("pOutdoor_Watering_Logic_Runtime").intValue()

        now = ZonedDateTime.now()
        if active_program == WateringHelper.STATE_CONTROL_START_MORNING:
            next_start = now.withHour(8).withMinute(0).withSecond(0)
        elif active_program == WateringHelper.STATE_CONTROL_START_EVENING:
            next_start = now.withHour(22).withMinute(0).withSecond(0)

        next_start = next_start.minusMinutes(total_duration)

        while next_start.isBefore(now):
            next_start = next_start.plusHours(24)

        time_span = Duration.between(now, next_start).getSeconds() if next_start.isAfter(now) else 0

        self.programTimer = startTimer(self.log, time_span, self.triggerProgramStart)
        self.programTimerStart = next_start

        self.updateProgramTimerMsg()

    def updateProgramTimerMsg(self):
        diff = self.programTimerStart.getDayOfYear() - ZonedDateTime.now().getDayOfYear()
        if diff <= 1:
            offset = "Heute" if diff == 0 else "Morgen"
            fmt = DateTimeFormatter.ofPattern("HH:mm");
            msg = "{}, {}".format(offset, self.programTimerStart.format(fmt))
        else:
            fmt = DateTimeFormatter.ofPattern("dd.MM - HH:mm");
            msg = "Startet {}".format(self.programTimerStart.format(fmt))
        postUpdate("pOutdoor_Watering_Logic_Program_State", msg)

    def triggerProgramStart(self):
        self.programTimer = None

        active_programm = getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_programm not in [WateringHelper.STATE_CONTROL_START_MORNING, WateringHelper.STATE_CONTROL_START_EVENING]:
            self.log.error("Invalid call of triggerProgramStart")
            return

        sendCommand("pOutdoor_Watering_Logic_Program_Start", WateringHelper.STATE_CONTROL_START_NOW)

    def execute(self, module, input):
        if input['event'].getType() == "TimerEvent":
            if self.programTimer is not None:
                self.updateProgramTimerMsg()
            return

        if input['event'].getItemName() == "pOutdoor_Watering_Logic_Runtime":
            if self.programTimer is None:
                return

        if self.programTimer != None:
            self.programTimer.cancel()
            self.programTimer = None

        if self.progressTimer is not None:
            self.progressTimer.cancel()
            self.progressTimer = None

        self.initProgram(input)
