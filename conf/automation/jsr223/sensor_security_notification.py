from java.time import ZonedDateTime

from shared.helper import rule, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getItem, getItemState, itemLastChangeNewerThen, NotificationHelper
from custom.presence import PresenceHelper


@rule("sensor_security_notification.py")
class SensorSecurityNotificationRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gSensor_Indoor")
        self.triggers += [ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Garden_State")]
        # Other main door events are handled inside presence detection.
        #ItemStateChangeTrigger("pGF_Corridor_Openingcontact_Door_State"),
        #ItemStateChangeTrigger("pGF_Garage_Openingcontact_Door_Streedside_State"),

        self.last_notification = ZonedDateTime.now()
        
    def getLocation(self,item):
        for parentName in item.getGroupNames():
            parent = getItem(parentName)
            if parentName[0:1] == 'l':
                return parent
            else:
                location = self.getLocation(parent)
                if location != None:
                    return location
        return None

    def confirmArriving(self):
        state = getItemState("pOther_Presence_State").intValue()


    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Notify") != ON:
            return

        state = getItemState("pOther_Presence_State").intValue()
        
        if state in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            itemName = input['event'].getItemName()
            item = getItem(itemName)
            
            location = self.getLocation(item)

            if "pGF_Garage_Openingcontact_Door_Garden_State" == itemName:
                msg = u"Garagentür zum Garten {}".format( u"offen" if input['event'].getItemState() == OPEN else u"geschlossen" )
            elif "Openingcontact_Window" in itemName:
                msg = u"Fenster im {} {}".format( location.getLabel(), u"offen" if input['event'].getItemState() == OPEN else u"geschlossen" )
            elif "Motiondetector" in itemName:
                if input['event'].getItemState() == CLOSED:
                    return

                # during sleep, ignore moving detection
                if state == PresenceHelper.STATE_SLEEPING:
                    return

                msg = u"Bewegung im {} erkannt".format(location.getLabel())
                
            #self.log.info(u"{} {} {} {}".format(group,itemName,item.getLabel(),location.getLabel()))

            now = ZonedDateTime.now()
            if ChronoUnit.MINUTES.between(self.last_notification, now) > 5:
                if "Motiondetector" in itemName:
                    NotificationHelper.sendNotificationToAllAdmins(NotificationHelper.PRIORITY_ALERT, u"Alarm", u"{}".format(msg))
                else:
                    NotificationHelper.sendNotification(NotificationHelper.PRIORITY_ALERT, u"Alarm", u"{}".format(msg))
                self.last_notification = now
