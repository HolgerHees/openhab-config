from custom.helper import rule, getGroupMemberChangeTrigger, postUpdate, sendCommand

@rule("values_security_last_changed.py")
class ValuesSecurityLastChangedRule:
    def __init__(self):
        self.triggers = []
        self.triggers += getGroupMemberChangeTrigger("Openingcontacts")
        self.triggers += getGroupMemberChangeTrigger("Sensor_Indoor")

    def execute(self, module, input):
        postUpdate("Security_Last_Change", DateTimeType())
