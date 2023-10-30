import math
from java.time import ZonedDateTime, Duration
from java.time.format import DateTimeFormatter
from java.time.temporal import ChronoUnit

from shared.helper import rule, startTimer, getItemState, postUpdate, sendCommand, sendCommandIfChanged, getItemLastChange
from shared.triggers import ItemCommandTrigger, ItemStateChangeTrigger, CronTrigger

circuits = [
    [
      2.0 / 3.0,
      u"Strasse",
      [
        'pOutdoor_Streetside_Lawn_Watering'
      ]
    ],[
      1.0,
      u"Beete",
      [
        'pOutdoor_Streetside_Beds_Watering',
        'pOutdoor_Terrace_Watering',
        'pOutdoor_Garden_Back_Watering'
      ]
    ],[
      1.0,
      u"Garten rechts",
      [
        'pOutdoor_Garden_Right_Watering'
      ]
    ],[
      1.0,
      u"Garten links",
      [
        'pOutdoor_Garden_Left_Watering'
      ]
    ]
]
      
#circuits = [
#    [
#        ['pOutdoor_Streetside_Lawn_Watering_Powered', u"Strasse", 2.0 / 3.0 ],
#        ['pOutdoor_Garden_Right_Watering_Powered', u"Garten rechts", 1.0 ],
#        ['pOutdoor_Garden_Left_Watering_Powered', u"Garten links", 1.0 ]
#    ], [
#        ['pOutdoor_Streetside_Beds_Watering_Powered', u"Beete", 1.0 ]
#    ], [
#        ['pOutdoor_Terrace_Watering_Powered', u"Beete", 1.0 ]
#    ], [
#        ['pOutdoor_Garden_Back_Watering_Powered', u"Beete", 1.0 ]
#    ]
#]

class ScenesWatheringHelper():
    STATE_OFF = 0
    STATE_START_NOW = 1
    STATE_START_MORNING = 2
    STATE_START_EVENING = 3

@rule()
class ScenesWatheringMessage:
    def __init__(self):
        self.triggers = [ ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_Duration") ]

        for group in circuits:
            for circuit in group[2]:
                self.triggers.append(ItemStateChangeTrigger(circuit+"_Auto"))

    def execute(self, module, input):
        reference_duration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue()

        total_duration = 0
        for i in range(len(circuits)):
            for circuit in circuits[i][2]:
                if getItemState(circuit + "_Auto") == ON:
                    duration = ( circuits[i][0] * reference_duration )
                    duration = int( math.floor( duration ) )

                    postUpdate(circuit + "_Info", u"{} min.".format(duration))
                else:
                    postUpdate(circuit + "_Info", u"inaktiv")

            for circuit in circuits[i][2]:
                if getItemState(circuit + "_Auto") == ON:
                    duration = ( circuits[i][0] * reference_duration )
                    duration = int( math.floor( duration ) )
                    total_duration += duration
                    break
        postUpdate("pOutdoor_Watering_Logic_Runtime", total_duration)
        postUpdate("pOutdoor_Watering_Logic_Info", "{} min.".format(total_duration) if total_duration <= 60 else "{}:{}".format(int(total_duration / 60), int(total_duration % 60)))

@rule()
class ScenesWatheringControl():
    def __init__(self):
        self.triggers = [
            ItemCommandTrigger("pOutdoor_Watering_Logic_Program_Start"),
            ItemStateChangeTrigger("pOutdoor_Watering_Logic_Runtime"),
            CronTrigger("0 0 0 * * ?")
        ]

        self.progressTimer = None
        self.currentProgressMsg = ""

        self.activeIndex = -1

        self.programTimerStart = None
        self.programTimer = None

        self.initProgramTimer()

    def disableAllCircuits(self):
        for i in range(len(circuits)):
            group = circuits[i]
            for circuit in group[2]:
                if getItemState(circuit + "_Auto") == ON:
                    sendCommand(circuit + "_Powered", OFF)
        postUpdate("pOutdoor_Watering_Logic_Program_State", u"läuft nicht")
        self.activeIndex = -1

    def cancelProgressTimer(self):
        if self.progressTimer is not None:
            self.progressTimer.cancel()
        self.cleanProgressTimer()

    def cleanProgressTimer(self):
        self.progressTimer = None
        self.currentProgressMsg = ""
        
    def findStep(self):
        duration = getItemState("pOutdoor_Watering_Logic_Program_Duration").intValue() * 60.0
        
        remaining = 0
        info = u""

        # detect current active index
        if self.activeIndex == -1:
            for i in range(len(circuits)):
                group = circuits[i]
                for circuit in group[2]:
                    if getItemState(circuit + "_Powered") == ON:
                        self.activeIndex = i
                        runtime = ChronoUnit.SECONDS.between(getItemLastChange(circuit + "_Powered"),ZonedDateTime.now())
                        remaining = ( duration * group[0] ) - runtime
                        break
                if self.activeIndex != -1:
                    break
        else:
            group = circuits[self.activeIndex]
            for circuit in group[2]:
                if getItemState(circuit + "_Powered") == ON:
                    runtime = ChronoUnit.SECONDS.between(getItemLastChange(circuit + "_Powered"),ZonedDateTime.now())
                    remaining = ( duration * group[0] ) - runtime
                    break

        if remaining <= 0:
            nextIndex = -1

            # detect next index
            for i in range(len(circuits)):
                if self.activeIndex != -1 and i <= self.activeIndex:
                    continue;
                group = circuits[i]
                for circuit in group[2]:
                    if getItemState(circuit + "_Auto") == ON:
                        nextIndex = i;
                        break
                if nextIndex != -1:
                    break
        
            if nextIndex == -1:
                sendCommand("pOutdoor_Watering_Logic_Program_Start", ScenesWatheringHelper.STATE_OFF)
            else:
                for circuit in circuits[nextIndex][2]:
                    if getItemState(circuit + "_Auto") == ON:
                        sendCommand(circuit + "_Powered", ON)
                
                nextGroup = circuits[nextIndex]

                remaining = ( duration * nextGroup[0] )
                info = nextGroup[1]

                # deactivate current index
                if self.activeIndex != -1:
                    for circuit in circuits[self.activeIndex][2]:
                        if getItemState(circuit + "_Auto") == ON:
                            sendCommand(circuit + "_Powered", OFF)

                self.activeIndex = nextIndex
        else:
            info = circuits[self.activeIndex][1]
            for circuit in circuits[self.activeIndex][2]:
                if getItemState(circuit + "_Auto") == ON:
                    if sendCommandIfChanged(circuit + "_Powered", ON):
                        self.log.error("Unexcpected circuit state. Powered ON again.")
        
        return [ info, remaining ]

    def callbackProgress(self):
        if self.progressTimer is not None and self.currentProgressMsg != getItemState("pOutdoor_Watering_Logic_Program_State").toString():
            self.log.info("Cancel Watering Progress Zombie Timer")
            self.cleanProgressTimer()
            return

        msg, remaining = self.findStep()
        
        if remaining <= 0:
            self.cleanProgressTimer()
            return
        
        remainingInMinutes = int( math.floor( remaining / 60.0 ) )

        if remainingInMinutes > 0:
            msg = u"{} noch {} min".format(msg, remainingInMinutes )
        else:
            msg = u"{} gleich fertig".format(msg)

        self.currentProgressMsg = msg
        postUpdate("pOutdoor_Watering_Logic_Program_State", self.currentProgressMsg)

        self.progressTimer = startTimer(self.log, 60.0, self.callbackProgress)

    def triggerProgramTimer(self):
        self.programTimer = None

        active_programm = getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_programm not in [ScenesWatheringHelper.STATE_START_MORNING, ScenesWatheringHelper.STATE_START_EVENING]:
            self.log.error("Invalid call of triggerProgramTimer")
            return

        sendCommand("pOutdoor_Watering_Logic_Program_Start", ScenesWatheringHelper.STATE_START_NOW)

    def initProgramTimer(self, input = None):
        active_programm = input['command'].intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Program_Start" else getItemState("pOutdoor_Watering_Logic_Program_Start").intValue()
        if active_programm not in [ScenesWatheringHelper.STATE_START_MORNING, ScenesWatheringHelper.STATE_START_EVENING]:
            self.programTimer = None
            return

        total_duration = input['event'].getItemState().intValue() if input is not None and input['event'].getItemName() == "pOutdoor_Watering_Logic_Runtime" else getItemState("pOutdoor_Watering_Logic_Runtime").intValue()

        now = ZonedDateTime.now()
        if active_programm == ScenesWatheringHelper.STATE_START_MORNING:
            #next_start = now.plusSeconds(total_duration * 60 + 10)
            next_start = now.withHour(8).withMinute(0).withSecond(0)
        elif active_programm == ScenesWatheringHelper.STATE_START_EVENING:
            next_start = now.withHour(22).withMinute(0).withSecond(0)

        next_start = next_start.minusMinutes(total_duration)

        while next_start.isBefore(now):
            next_start = next_start.plusHours(24)

        time_span = Duration.between(now, next_start).getSeconds() if next_start.isAfter(now) else 0

        #self.log.info("{} -> {}".format(next_start, now))
        self.programTimer = startTimer(self.log, time_span, self.triggerProgramTimer)
        self.programTimerStart = next_start

        self.updateProgramTimerNextStart(now)

        #self.log.info("InitProgramTimer: {} -> {} -> {}".format(active_programm, total_duration, time_span))

    def updateProgramTimerNextStart(self, now):
        if self.programTimerStart is None:
            return

        diff = self.programTimerStart.getDayOfYear() - now.getDayOfYear()
        if diff <= 1:
            offset = "Heute" if diff == 0 else "Morgen"
            fmt = DateTimeFormatter.ofPattern("HH:mm");
            msg = "{}, {}".format(offset, self.programTimerStart.format(fmt))
        else:
            fmt = DateTimeFormatter.ofPattern("dd.MM - HH:mm");
            msg = "Startet {}".format(self.programTimerStart.format(fmt))
        postUpdate("pOutdoor_Watering_Logic_Program_State", msg)

    def execute(self, module, input):
        if input['event'].getType() == "TimerEvent":
            self.updateProgramTimerNextStart(ZonedDateTime.now())
            return

        #self.log.info("-----------------")
        if self.programTimer != None:
            self.programTimer.cancel()
            self.programTimer = None

        self.cancelProgressTimer()

        if input['event'].getItemName() == "pOutdoor_Watering_Logic_Program_Start":
            if input["command"].intValue() == ScenesWatheringHelper.STATE_START_NOW:
                self.log.info("callbackProgress")
                self.callbackProgress()
                return
            else:
                self.disableAllCircuits()
                if input["command"].intValue() == ScenesWatheringHelper.STATE_OFF:
                    return

        self.initProgramTimer(input)
