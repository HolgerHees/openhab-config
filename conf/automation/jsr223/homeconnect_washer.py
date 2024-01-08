from java.time import ZonedDateTime
 
from shared.helper import rule, getItemState, getHistoricItemEntry, postUpdateIfChanged, startTimer, NotificationHelper
from shared.actions import Transformation
from shared.triggers import ItemStateChangeTrigger


@rule()
class HomeConnectWasherMessage:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pGF_Utilityroom_Washer_ActiveProgramState", state="UNDEF")
        ]

        #self.check()

    def check(self):
        max_time = ZonedDateTime.now().minusHours( 24 * 30 * 3 )

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

@rule()
class HomeConnectWasherProgress:
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
        prevState = input['event'].getOldItemState()
        if prevState == NULL or prevState == UNDEF:
            return

        # *** PROGRESS ***
        currentMode = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_OperationState" else getItemState("pGF_Utilityroom_Washer_OperationState")
        if currentMode == NULL or currentMode == UNDEF:
            return

        currentRuntime = input['event'].getItemState() if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState" else getItemState("pGF_Utilityroom_Washer_RemainingProgramTimeState")

        mode = Transformation.transform("MAP", "homeconnect_operation.map", currentMode.toString() )
        msg = u"{}".format(mode)

        if currentRuntime != NULL and currentRuntime != UNDEF and currentRuntime.intValue() > 0 and currentMode.toString() in ['Paused','Delayed','Run']:
            msg = u"{}, {}".format(msg, Transformation.transform("JS", "homeconnect_runtime.js", u"{}".format(currentRuntime.intValue()) ))

        postUpdateIfChanged("pGF_Utilityroom_Washer_Message", msg)

        # *** NOTIFICATION ***
        if input['event'].getItemName() == "pGF_Utilityroom_Washer_RemainingProgramTimeState":
            if currentRuntime != NULL and currentRuntime != UNDEF and currentRuntime.intValue() > 0:
                # refresh timer with additional 10 min delay as a fallback
                self.checkTimer = startTimer(self.log, currentRuntime.intValue() + 600, self.notify, args = [ False ], oldTimer = self.checkTimer)
        else:
            if currentMode.toString() == "Run":
                # start timer with initial 15 min delay as a fallback
                self.checkTimer = startTimer(self.log, 900, self.notify, args = [ False ], oldTimer = self.checkTimer)
            elif currentMode.toString() == "Finished":
                if self.checkTimer != None:
                    self.checkTimer.cancel()
                self.notify( True )
