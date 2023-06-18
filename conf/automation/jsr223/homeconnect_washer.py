from shared.helper import rule, getItemState, getItemLastChange, getHistoricItemEntry, postUpdateIfChanged, startTimer, NotificationHelper
from shared.actions import Transformation
from shared.triggers import CronTrigger, ItemStateChangeTrigger

from java.time import ZonedDateTime
 
@rule("homeconnect_washer.py")
class HomeConnectWasherMessageRule:
    def __init__(self):
        self.triggers = [
            #CronTrigger("0/5 * * * * ?"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_ActiveProgramState", state="UNDEF")
        ]

        #self.check()

    def check(self):
        max_time = ZonedDateTime.now().minusHours( 24 * 31 )

        #if getItemState("pGF_Utilityroom_Washer_ActiveProgramState") != UNDEF:
        #    return

        currentTime = ZonedDateTime.now()

        found = False
        while True:
            historicEntry = getHistoricItemEntry("pGF_Utilityroom_Washer_ActiveProgramState", currentTime )
            currentTime = historicEntry.getTimestamp()

            if currentTime.isBefore(max_time):
                break

            #self.log.info("{}".format(historicEntry.getState().toString()))
            if historicEntry.getState().toString() == "Drum Clean":
                found = True
                break

            currentTime = currentTime.minusNanos(1)

        if not found:
            NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Waschmaschine", u"Trommelreinigung nötig" )

        #self.log.info(u"{}".format(found))

    def execute(self, module, input):
        self.check()

@rule("homeconnect_washer.py")
class HomeConnectWasherProgressRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_RemainingProgramTimeState"),
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_OperationState")
        ]

        self.checkTimer = None

    def notify(self,state):
        self.checkTimer = None
        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Waschmaschine", u"Wäsche ist fertig" if state else u"Wäsche ist wahrscheinlich fertig" )
  
    def execute(self, module, input):
        # *** PROGRESS ***
        operation = getItemState("pGF_Utilityroom_Washer_OperationState")
        if operation != NULL and operation != UNDEF:
            mode = Transformation.transform("MAP", "homeconnect_operation.map", operation.toString() )
            msg = u"{}".format(mode)

            runtime = getItemState("pGF_Utilityroom_Washer_RemainingProgramTimeState")
            if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0 and operation.toString() in ['Paused','Delayed','Run']:
                runtime = Transformation.transform("JS", "homeconnect_runtime.js", u"{}".format(runtime.intValue()) )
                msg = u"{}, {}".format(msg,runtime)

            postUpdateIfChanged("pGF_Utilityroom_Washer_Message", msg)

        # *** NOTIFICATION ***
        if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState":
            runtime = input['event'].getItemState()
            if runtime != NULL and runtime != UNDEF and runtime.intValue() > 0 and self.checkTimer != None:
                # refresh timer with additional 10 min delay as a fallback
                self.checkTimer = startTimer(self.log, runtime.intValue() + 600, self.notify, args = [ False ], oldTimer = self.checkTimer)
        else:
            prevMode = input['event'].getOldItemState().toString()
            if prevMode != NULL and prevMode != UNDEF:
                currentMode = input['event'].getItemState().toString()
                if currentMode == "Run":
                    # start timer with initial 15 min delay as a fallback
                    self.checkTimer = startTimer(self.log, 900, self.notify, args = [ False ], oldTimer = self.checkTimer)
                elif currentMode == "Finished"and self.checkTimer != None:
                    self.checkTimer.cancel()
                    self.notify( True )
