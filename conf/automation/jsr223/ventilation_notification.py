from shared.helper import rule, getItemState, getHistoricItemState, getGroupMember, sendNotification
from custom.presence import PresenceHelper
from core.triggers import CronTrigger, ItemStateChangeTrigger
from java.time import ZonedDateTime

@rule("ventilation_notification.py")
class TemperatureConditionCheckRule:
    def __init__(self):
        self.triggers = [
            CronTrigger("0 */1 * * * ?"),
            ItemStateChangeTrigger("pOther_Presence_Holger_State",state="ON"),
            ItemStateChangeTrigger("pOther_Presence_Sandra_State",state="ON")
        ]
        self.lastState = 0
        self.lastPrefix = u""
        
    def check(self,gardenTempNow,gardenTempPast,refTempItemName,windowGroupItemName):
        refTemp = getItemState(refTempItemName).doubleValue()
        allWindowsClosed = True
        windows = getGroupMember(windowGroupItemName)
        for item in windows:
            if getItemState(item.getName()) == OPEN:
                allWindowsClosed = False
                break
              
        # outside is getting warmer
        if gardenTempNow > gardenTempPast:
            # indoor temperature is NOT at least 0.2° warmer then outside
            if refTemp - gardenTempNow <= 0.2:
                if not allWindowsClosed:
                    return -1
        # outside is getting colder or does not change
        else:
            # indoor temperature is at least 0.2° warmer then outside
            if refTemp - gardenTempNow >= 0.2:
                if allWindowsClosed:
                    return 1
                  
        return 0
                    
    def execute(self, module, input):
        # we don't want do be notified
        if getItemState("pOther_Manual_State_Air_Thoroughly_Notify") != ON:
            return
          
        # no device presence state change
        if 'event' not in input:
            # we are away
            if getItemState("pOther_Presence_State").intValue() == 0:
                return
              
            # recipients will be selected only if there are state changes
            recipients = None
        else:
            recipients = [ PresenceHelper.getRecipientByStateItem( ['event'].getItemName() ) ]
          
        now = ZonedDateTime.now()

        gardenTempNow = getItemState("pOutdoor_WeatherStation_Temperature").doubleValue()
        gardenTempPast  = getHistoricItemState("pOutdoor_WeatherStation_Temperature",now.minusMinutes(120)).doubleValue()

        stateGF = self.check(gardenTempNow,gardenTempPast,"pGF_Livingroom_Air_Sensor_Temperature_Value","gGF_Sensor_Window")
        stateFF = self.check(gardenTempNow,gardenTempPast,"pFF_Bedroom_Air_Sensor_Temperature_Value","gGF_Sensor_Window")
        
        state = 0
        prefix = u""
        if stateGF == stateFF:
            prefix = u"Alle"
            state = stateGF
        else:
            prefix = u"EG" if stateGF != 0 else u"OG"
            state = stateGF if stateGF != 0 else stateFF
            
        if self.lastState != state or self.lastPrefix != prefix:
            recipients = PresenceHelper.getPresentRecipients()
            
        if recipients is not None:
            # we are not sleeping
            if getItemState("pOther_Presence_State").intValue() != 2:
                if state == 1:
                    sendNotification(u"Lüften", u"{} Fenster auf. Es ist kühl genug.".format(prefix), recipients = recipients )
                elif state == -1:
                    sendNotification(u"Lüften", u"{} Fenster zu. Es ist zu warm.".format(prefix), recipients = recipients )
            self.lastState = state
            self.lastPrefix = prefix
