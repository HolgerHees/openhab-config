from custom.helper import rule, sendNotification, sendCommand

@rule("_test.py")
class TestRule:
    def __init__(self):
        pass

    def execute(self, module, input):
        pass

#sendCommand("Light_FF_Utilityroom_Ceiling",REFRESH) 
