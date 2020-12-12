from shared.helper import rule, getItemState, postUpdate, sendCommand
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
                if getItemState("Window_GF_Livingroom_Terrace") == CLOSED: sendCommand("pGFLivingroom_Shutter_Terrace_Control", DOWN)
                if getItemState("Window_GF_Livingroom_Couch") == CLOSED: sendCommand("pGFLivingroom_Shutter_Couch_Control", DOWN)
                if getItemState("Window_GF_Kitchen") == CLOSED: sendCommand("pGF_Kitchen_Shutter_Control", DOWN)
                if getItemState("Window_GF_Guestroom") == CLOSED: sendCommand("pGF_Guestroom_Shutter_Control", DOWN)
                if getItemState("Window_GF_Guesttoilet") == CLOSED: sendCommand("pGF_Guesttoilet_Shutter_Control", DOWN)

                if getItemState("Window_FF_Bedroom") == CLOSED: sendCommand("pFF_Bedroom_Shutter_Control", DOWN)
                if getItemState("Window_FF_Dressingroom") == CLOSED: sendCommand("pFF_Dressingroom_Shutter_Control", DOWN)
                if getItemState("Window_FF_Child1") == CLOSED: sendCommand("pFF_Child1_Shutter_Control", DOWN)
                if getItemState("Window_FF_Child2") == CLOSED: sendCommand("pFF_Child2_Shutter_Control", DOWN)
                if getItemState("Window_FF_Bathroom") == CLOSED: sendCommand("pFF_Bathroom_Shutter_Control", DOWN)
                if getItemState("Window_Attic") == CLOSED: sendCommand("pAttic_Shutter_Control", DOWN)
            elif getItemState("State_Presence").intValue() == 0:
                sendCommand("gShutters", UP)


@rule("rollershutter_auto.py")
class AtticSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Attic")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Attic") == ON:
                sendCommand("pAttic_Shutter_Control", DOWN)
            else:
                sendCommand("pAttic_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class BathroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Bathroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Bathroom") == ON:
                sendCommand("pFF_Bathroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Bathroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class DressingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Dressingroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Dressingroom") == ON:
                sendCommand("pFF_Dressingroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Dressingroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class BedroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Bedroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON:
            if getItemState("State_Sunprotection_Bedroom") == ON:
                sendCommand("pFF_Bedroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Bedroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class LivingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("State_Sunprotection_Livingroom")]

    def execute(self, module, input):
        if getItemState("Auto_Sunprotection") == ON and getItemState("State_Presence").intValue() == 0:
            if getItemState("State_Sunprotection_Livingroom") == ON:
                sendCommand("pGF_Kitchen_Shutter_Control", DOWN)
                sendCommand("pGFLivingroom_Shutter_Couch_Control", DOWN)
                if getItemState("Window_GF_Livingroom_Terrace") == CLOSED:
                    sendCommand("pGFLivingroom_Shutter_Terrace_Control", DOWN)
            else:
                sendCommand("pGF_Kitchen_Shutter_Control", UP)
                sendCommand("pGFLivingroom_Shutter_Couch_Control", UP)
                sendCommand("pGFLivingroom_Shutter_Terrace_Control", UP)
