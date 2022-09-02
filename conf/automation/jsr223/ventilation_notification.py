from java.time import ZonedDateTime

from shared.helper import rule, getItemState, getHistoricItemState, getStableItemState, getStableMinMaxItemState, getGroupMember, startTimer, NotificationHelper
from shared.triggers import CronTrigger, ItemStateChangeTrigger

from custom.presence import PresenceHelper


@rule("ventilation_notification.py")
class TemperatureConditionCheckRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */1 * * * ?"),
            ItemStateChangeTrigger("pOther_Presence_State"),
        ]
        self.lastDirection = None
        self.lastGFShouldOpen = None
        self.lastFFShouldOpen = None
        
        self.timer = None
        
    def getOpenState(self,windowGroupItemName,excludedItems=[]):
        isOpen = False
        windows = getGroupMember(windowGroupItemName)
        for item in windows:
            if item.getName() in excludedItems:
                continue
                
            if getItemState(item.getName()) == OPEN:
                isOpen = True
                break
        return isOpen
      
    def getOpenRequest(self,now,gardenTemp,gardenTempMax,direction,refTempItemName,lastState):
        refTemp = round(getStableItemState(now,refTempItemName,15),1)
        
        self.log.info(u"ROOM - {}: {}".format(refTempItemName,refTemp))
              
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
          
    def process(self,recipients):
        now = ZonedDateTime.now()
        
        weatherAvgTemperature = getItemState("pOutdoor_Weather_Current_Temperature_Avg").floatValue()

        room1Temperature = getItemState("pGF_Livingroom_Air_Sensor_Temperature_Value").floatValue()
        room2Temperature = getItemState("pFF_Bedroom_Air_Sensor_Temperature_Value").floatValue()
        
        # if temperature difference
        if weatherAvgTemperature <= room1Temperature or weatherAvgTemperature <= room2Temperature:
            self.log.info(u"PRECONDITION not fit ({} {} {})".format(weatherAvgTemperature,room1Temperature,room2Temperature))
            return

        gardenTemp0, gardenTemp0Min, gardenTemp0Max = getStableMinMaxItemState(now,"pOutdoor_WeatherStation_Temperature",15)
        gardenTemp15, gardenTemp15Min, gardenTemp15Max  = getStableMinMaxItemState(now.minusMinutes(15),"pOutdoor_WeatherStation_Temperature",30)
        gardenTemp45, gardenTemp45Min, gardenTemp45Max  = getStableMinMaxItemState(now.minusMinutes(45),"pOutdoor_WeatherStation_Temperature",30)
        
        gardenTemp0 = round(gardenTemp0,1)
        gardenTemp15 = round(gardenTemp15,1)
        gardenTemp45 = round(gardenTemp45,1)
        
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
                  
        self.log.info(u"GARDEN - Temp0: {}, Temp0Max: {}, Temp15: {}, Temp45: {}".format(gardenTemp0,gardenTemp0Max,gardenTemp15,gardenTemp45))

        gfShouldOpen = self.getOpenRequest(now,gardenTemp0,gardenTemp0Max,direction,"pGF_Livingroom_Air_Sensor_Temperature_Value",self.lastGFShouldOpen)
        gfIsOpen = self.getOpenState("gGF_Sensor_Window",["pGF_Livingroom_Openingcontact_Window_Terrace_State"])
        
        ffShouldOpen = self.getOpenRequest(now,gardenTemp0,gardenTemp0Max,direction,"pFF_Bedroom_Air_Sensor_Temperature_Value",self.lastFFShouldOpen)
        ffIsOpen = self.getOpenState("gFF_Sensor_Window")
        
        if (self.lastGFShouldOpen!=gfShouldOpen and gfShouldOpen!=gfIsOpen) or (self.lastFFShouldOpen!=ffShouldOpen and ffShouldOpen!=ffIsOpen):
            recipients = PresenceHelper.getPresentRecipients()
            
        self.log.info(u"STATE - gfShouldOpen: {}, gfIsOpen: {}, ffShouldOpen: {}, ffIsOpen: {}, direction: {}".format(gfShouldOpen,gfIsOpen,ffShouldOpen,ffIsOpen,direction))
        
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
              
            msg = []
            if len(actions["OPEN"]) == 2:
                msg.append(u"Alle Fenster auf")
            elif len(actions["CLOSE"]) == 2:
                msg.append(u"Alle Fenster zu")
            else:
                if len(actions["OPEN"]) == 1:
                    msg.append(u"{} Fenster auf".format(actions["OPEN"][0]))
                if len(actions["CLOSE"]) == 1:
                    msg.append(u"{} Fenster zu".format(actions["CLOSE"][0]))

            if len(msg) > 0:
                msg = u" und ".join(msg)

                self.log.info(u"MSG: {}".format(msg))
                
                # we are not sleeping
                if getItemState("pOther_Presence_State").intValue() not in [PresenceHelper.STATE_MAYBE_SLEEPING,PresenceHelper.STATE_SLEEPING]:
                    # initial debug
                    if self.lastDirection is None:
                        recipients = ["bot_holger"]
                    NotificationHelper.sendNotification(NotificationHelper.PRIORITY_NOTICE, u"Lüften", msg, recipients = recipients )

        self.lastDirection = direction
        self.lastGFShouldOpen = gfShouldOpen
        self.lastFFShouldOpen = ffShouldOpen
        
    def execute(self, module, input):
        # we don't want do be notified
        if getItemState("pOther_Manual_State_Air_Thoroughly_Notify") != ON:
            return
          
        if 'event' in input:
            if self.timer != None:
                self.timer.cancel()
                self.timer = None
                
            if input['event'].getItemState().intValue() == PresenceHelper.STATE_PRESENT and input['event'].getOldItemState().intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                # delayed notification to give all devices the chance to be detected as present
                self.timer = startTimer(self.log, 60, self.process, args = [ PresenceHelper.getPresentRecipients() ]) # 1 min
        else:
            # we are away
            if getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_MAYBE_PRESENT]:
                return
              
            # recipients will be selected only if there are state changes
            recipients = None
            
            self.process(recipients)

