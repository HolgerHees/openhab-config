from java.time import ZonedDateTime

from shared.helper import rule, isMember, getGroupMemberChangeTrigger, ItemStateChangeTrigger, getItem, getItemState, itemLastChangeNewerThen, NotificationHelper
from custom.presence import PresenceHelper
from custom.alexa import AlexaHelper


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

@rule("sensor_security_notification.py")
class SensorSecurityAlertingRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")

    def execute(self, module, input):
        state = getItemState("pOther_Presence_State").intValue()
        if state != PresenceHelper.STATE_SLEEPING:
            return

        if isMember(input['event'].getItemName(), "gGF_Sensor_Doors"):
            AlexaHelper.sendAlarmTTSToLocation("lFF_Bedroom", "Achtung, die Haustuer wurde unerwartet geoeffnet")
        elif isMember(input['event'].getItemName(), "gGF_Sensor_Window"):
            AlexaHelper.sendAlarmTTSToLocation("lFF_Bedroom", "Achtung, es wurde ein Fenster im Ergeschoss unerwartet geoeffnet")
        else:
            AlexaHelper.sendTTSToLocation("lFF_Bedroom", "<speak><amazon:effect name=\"whispered\">Achtung, es wurde ein Fenster im Obergeschoss unerwartet geoeffnet</amazon:effect></speak>")
