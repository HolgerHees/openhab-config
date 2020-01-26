from custom.helper import rule, getItemState, postUpdate, sendCommand
from core.triggers import ItemStateChangeTrigger

@rule("rollershutter_auto.py")
class RollershutterCleanupRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("Auto_Rollershutter", state="OFF")]

    def execute(self, module, input):
        postUpdate("Auto_Sunprotection", OFF)


@rule("rollershutter_auto.py")
class RollershutterAutoRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Rollershutter")]

    def execute(self, module, input):
        if getItemState("Auto_Rollershutter") == ON:
            if getItemState("State_Rollershutter") == ON:
                if getItemState("Window_FF_Livingroom_Terrace") == CLOSED: sendCommand("Shutters_FF_Livingroom_Terrace", DOWN)
                if getItemState("Window_FF_Livingroom_Couch") == CLOSED: sendCommand("Shutters_FF_Livingroom_Couch", DOWN)
                if getItemState("Window_FF_Kitchen") == CLOSED: sendCommand("Shutters_FF_Kitchen", DOWN)
                if getItemState("Window_FF_Guestroom") == CLOSED: sendCommand("Shutters_FF_Guestroom", DOWN)
                if getItemState("Window_FF_GuestWC") == CLOSED: sendCommand("Shutters_FF_GuestWC", DOWN)

                if getItemState("Window_SF_Bedroom") == CLOSED: sendCommand("Shutters_SF_Bedroom", DOWN)
                if getItemState("Window_SF_Dressingroom") == CLOSED: sendCommand("Shutters_SF_Dressingroom", DOWN)
                if getItemState("Window_SF_Child1") == CLOSED: sendCommand("Shutters_SF_Child1", DOWN)
                if getItemState("Window_SF_Child2") == CLOSED: sendCommand("Shutters_SF_Child2", DOWN)
                if getItemState("Window_SF_Bathroom") == CLOSED: sendCommand("Shutters_SF_Bathroom", DOWN)
                if getItemState("Window_SF_Attic") == CLOSED: sendCommand("Shutters_SF_Attic", DOWN)
            elif getItemState("State_Presence").intValue() == 0:
                sendCommand("Shutters", UP)


@rule("rollershutter_auto.py")
class AtticSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Attic")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Attic") == ON:
                sendCommand("Shutters_SF_Attic", DOWN)
            else:
                sendCommand("Shutters_SF_Attic", UP)


@rule("rollershutter_auto.py")
class BathroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Bathroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Bathroom") == ON:
                sendCommand("Shutters_SF_Bathroom", DOWN)
            else:
                sendCommand("Shutters_SF_Bathroom", UP)


@rule("rollershutter_auto.py")
class DressingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Dressingroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Dressingroom") == ON:
                sendCommand("Shutters_SF_Dressingroom", DOWN)
            else:
                sendCommand("Shutters_SF_Dressingroom", UP)


@rule("rollershutter_auto.py")
class BedroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Bedroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Bedroom") == ON:
                sendCommand("Shutters_SF_Bedroom", DOWN)
            else:
                sendCommand("Shutters_SF_Bedroom", UP)


@rule("rollershutter_auto.py")
class LivingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Livingroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON and getItemState("State_Presence").intValue() == 0:
            if getItemState("State_Sunprotection_Livingroom") == ON:
                sendCommand("Shutters_FF_Kitchen", DOWN)
                sendCommand("Shutters_FF_Livingroom_Couch", DOWN)
                if getItemState("Window_FF_Livingroom_Terrace") == CLOSED:
                    sendCommand("Shutters_FF_Livingroom_Terrace", DOWN)
            else:
                sendCommand("Shutters_FF_Kitchen", UP)
                sendCommand("Shutters_FF_Livingroom_Couch", UP)
                sendCommand("Shutters_FF_Livingroom_Terrace", UP)
