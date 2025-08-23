from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from shared.notification import NotificationHelper
from shared.toolbox import ToolboxHelper
from shared.user import UserHelper

from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper
from custom.flags import FlagHelper
from custom.weather import WeatherHelper

from datetime import datetime, timedelta
import threading

import scope


@rule(
triggers = [
        GenericCronTrigger("0 * * * * ?"),
        ItemStateChangeTrigger("pOther_Presence_Arrive_State",state="1")
    ]
)
class Notification:
    def __init__(self):
        self.lastDirection = None
        self.lastGFShouldOpen = None
        self.lastFFShouldOpen = None
        
        self.timer = None

        #self.process(None, 3)
        #AlexaHelper.sendTTSTest(self.logger,"test", header = "Lüftungshinweiss")
        
    def getOpenState(self,window_group_item_name,excludedItems=[]):
        isOpen = False
        windows = Registry.getItem(window_group_item_name).getAllMembers()
        for item in windows:
            if item.getName() in excludedItems:
                continue
                
            if Registry.getItemState(item.getName()) == scope.OPEN:
                isOpen = True
                break
        return isOpen
      
    def getOpenRequest(self,gardenTemp, gardenTempMax, direction, refTempItemName, lastState):
        refTemp = round(ToolboxHelper.getStableState(refTempItemName, 15).doubleValue(), 1)
        
        self.logger.info("ROOM - {}: {}".format(refTempItemName,refTemp))
              
        # outside is getting warmer
        if direction > 0:
            # outside is more then 1.0° (0.1°) colder
            if refTemp - gardenTemp > ( 1.0 if not lastState else 0.1 ):
                return True
            else:
                return False
        # outside is getting colder
        elif direction < 0:
            # outside is at least 0.3° (0.1°) colder
            if refTemp - gardenTemp >= ( 0.3 if not lastState else 0.1 ):
                return True
            else:
                return False

        # outside is 2.0° (0.1°) or more colder then inside
        if refTemp - gardenTempMax >= ( 2.0 if not lastState else 0.1 ):
            return True
        else:
            return False
          
    def process(self,recipients, flags):
        #weatherAvgTemperature = Registry.getItemState("pOutdoor_Weather_Current_Temperature_Avg").floatValue()

        #room1Temperature = Registry.getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").floatValue()
        #room2Temperature = Registry.getItemState("pFF_Bedroom_Air_Sensor_Temperature_Value").floatValue()
        
        # if temperature difference
        #if weatherAvgTemperature <= room1Temperature or weatherAvgTemperature <= room2Temperature:
        #    self.logger.info("PRECONDITION not fit ({} {} {})".format(weatherAvgTemperature,room1Temperature,room2Temperature))
        #    return

        now = datetime.now().astimezone()
        gardenTemp0, _, gardenTemp0Max = ToolboxHelper.getStableMinMaxState("pOutdoor_WeatherStation_Temperature", 900)
        gardenTemp0 = gardenTemp0.doubleValue()
        gardenTemp0Max = gardenTemp0Max.doubleValue()

        gardenTemp15  = ToolboxHelper.getStableState("pOutdoor_WeatherStation_Temperature", 1800, now - timedelta(minutes=15)).doubleValue()
        gardenTemp45  = ToolboxHelper.getStableState("pOutdoor_WeatherStation_Temperature", 1800, now - timedelta(minutes=45)).doubleValue()

        gardenTemp0 = round(gardenTemp0, 1)
        gardenTemp15 = round(gardenTemp15, 1)
        gardenTemp45 = round(gardenTemp45, 1)

        if gardenTemp0 > gardenTemp15 > gardenTemp45:
            direction = 1
        elif gardenTemp0 < gardenTemp15 < gardenTemp45:
            direction = -1
        else:
            if self.lastDirection is not None:
                direction = self.lastDirection
                if direction == 1:
                    if not (gardenTemp0 >= gardenTemp15 >= gardenTemp45):
                        direction = 0
                elif direction == -1:
                    if not (gardenTemp0 <= gardenTemp15 <= gardenTemp45):
                        direction = 0
            else:
                direction = 0

        self.logger.info("GARDEN - Temp0: {}, Temp0Max: {}, Temp15: {}, Temp45: {}".format(gardenTemp0, gardenTemp0Max, gardenTemp15, gardenTemp45))

        gfShouldOpen = self.getOpenRequest(gardenTemp0, gardenTemp0Max, direction,"pGF_Livingroom_Air_Sensor_Temperature_Value", self.lastGFShouldOpen)
        gfIsOpen = self.getOpenState("gGF_Sensor_Window",["pGF_Livingroom_Openingcontact_Window_Terrace_State"])

        ffShouldOpen = self.getOpenRequest(gardenTemp0, gardenTemp0Max, direction,"pFF_Bedroom_Air_Sensor_Temperature_Value", self.lastFFShouldOpen)
        ffIsOpen = self.getOpenState("gFF_Sensor_Window")

        if (self.lastGFShouldOpen!=gfShouldOpen and gfShouldOpen!=gfIsOpen) or (self.lastFFShouldOpen!=ffShouldOpen and ffShouldOpen!=ffIsOpen):
            recipients = UserHelper.getPresentUser()
            
        self.logger.info("STATE - gfShouldOpen: {}, gfIsOpen: {}, ffShouldOpen: {}, ffIsOpen: {}, direction: {}".format(gfShouldOpen, gfIsOpen, ffShouldOpen, ffIsOpen, direction))

        if recipients is not None:
            actions = {"OPEN":[],"CLOSE":[]}
            if gfShouldOpen != gfIsOpen:
                if gfShouldOpen:
                    actions["OPEN"].append("EG")
                else:
                    actions["CLOSE"].append("EG")
            if ffShouldOpen != ffIsOpen:
                if ffShouldOpen:
                    actions["OPEN"].append("OG")
                else:
                    actions["CLOSE"].append("OG")
              
            push_msg = []
            alexa_msg = []
            if len(actions["OPEN"]) == 2:
                push_msg.append("Alle Fenster auf")
                alexa_msg.append("Alle Fenster auf")
            elif len(actions["CLOSE"]) == 2:
                push_msg.append("Alle Fenster zu")
                alexa_msg.append("Alle Fenster zu")
            else:
                if len(actions["OPEN"]) == 1:
                    push_msg.append("{} Fenster auf".format(actions["OPEN"][0]))
                    alexa_msg.append("Fenster im {} auf".format("Obergeschoss" if actions["OPEN"][0] == "OG" else "Erdgeschoss"))
                if len(actions["CLOSE"]) == 1:
                    push_msg.append("{} Fenster zu".format(actions["CLOSE"][0]))
                    alexa_msg.append("Fenster im {} zu".format("Obergeschoss" if actions["CLOSE"][0] == "OG" else "Erdgeschoss"))

            # we have messages and we are not sleeping
            if len(push_msg) > 0 and Registry.getItemState("pOther_Presence_State").intValue() not in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                # lastDirection is None after a reloaded rule
                if self.lastDirection is not None:
                    if FlagHelper.hasFlag(FlagHelper.NOTIFY_PUSH, flags):
                        push_msg = ", ".join(push_msg)
                        NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, "Lüften", push_msg, recipients = recipients )

                    if FlagHelper.hasFlag(FlagHelper.NOTIFY_ALEXA, flags) and Registry.getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_PRESENT:
                        alexa_msg = " und ".join(alexa_msg)

                        AlexaHelper.sendTTS(alexa_msg, header = "Lüftungshinweiss")
                else:
                    self.logger.info("MSG: {}".format(push_msg))

        self.lastDirection = direction
        self.lastGFShouldOpen = gfShouldOpen
        self.lastFFShouldOpen = ffShouldOpen

        self.timer = None
        
    def execute(self, module, input):
        if not WeatherHelper.isWorking():
            return

        flags = Registry.getItemState("pOther_Manual_State_Air_Thoroughly_Notify").intValue()

        # we don't want do be notified
        if FlagHelper.hasFlag(FlagHelper.OFF, flags):
            return
          
        if input['event'].getType() != "TimerEvent":
            if self.timer != None:
                self.timer.cancel()
                self.timer = None

            # delayed notification to give all devices the chance to be detected as present
            self.timer = threading.Timer(300, self.process, args = [ UserHelper.getPresentUser(), flags ]) # 5 min
            self.timer.start()
        else:
            # we are away
            if Registry.getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                return
              
            if self.timer is None:
                # recipients will be selected only if there are state changes
                recipients = None

                self.process(recipients, flags)
