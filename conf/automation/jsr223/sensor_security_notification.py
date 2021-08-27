from shared.helper import rule, getGroupMemberChangeTrigger, sendNotification, getItem, getItemState
from custom.presence import PresenceHelper

@rule("sensor_security_notification.py")
class SensorSecurityNotificationRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Doors")
        self.triggers += getGroupMemberChangeTrigger("gGF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gFF_Sensor_Window")
        self.triggers += getGroupMemberChangeTrigger("gSensor_Indoor")
        self.timer = None
        
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

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Notify") == ON and getItemState("pOther_Presence_State").intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING]:
            itemName = input['event'].getItemName()
            item = getItem(itemName)
            
            location = self.getLocation(item)

            if "Door" in itemName:
                msg = u"Tür im {} {}".format( location.getLabel(), u"offen" if input['event'].getItemState() == OPEN else u"geschlossen" )
            elif "Window" in itemName:
                msg = u"Fenster im {} {}".format( location.getLabel(), u"offen" if input['event'].getItemState() == OPEN else u"geschlossen" )
            elif "Motiondetector" in itemName:
                # during sleep, ignore moving detection
                if getItemState("pOther_Presence_State").intValue() == PresenceHelper.STATE_SLEEPING:
                    return
                if input['event'].getItemState() == CLOSED:
                    return
                msg = u"Bewegung im {} erkannt".format(location.getLabel())
                
            #self.log.info(u"{} {} {} {}".format(group,itemName,item.getLabel(),location.getLabel()))

            sendNotification(u"Alarm", u"{}".format(msg))
