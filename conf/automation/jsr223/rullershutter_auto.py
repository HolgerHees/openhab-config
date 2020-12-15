from shared.helper import rule, getItemState, postUpdate, sendCommand
from core.triggers import ItemStateChangeTrigger

@rule("rollershutter_auto.py")
class RollershutterCleanupRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter", state="OFF")]

    def execute(self, module, input):
        postUpdate("pOther_Manual_State_Auto_Sunprotection", OFF)


@rule("rollershutter_auto.py")
class RollershutterAutoRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Rollershutter")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Rollershutter") == ON:
            if getItemState("pOther_Automatic_State_Rollershutter") == ON:
                if getItemState("pGF_Livingroom_Openingcontact_Window_Terrace_State") == CLOSED: sendCommand("pGF_Livingroom_Shutter_Terrace_Control", DOWN)
                if getItemState("pGF_Livingroom_Openingcontact_Window_Couch_State") == CLOSED: sendCommand("pGF_Livingroom_Shutter_Couch_Control", DOWN)
                if getItemState("pGF_Kitchen_Openingcontact_Window_State") == CLOSED: sendCommand("pGF_Kitchen_Shutter_Control", DOWN)
                if getItemState("pGF_Guestroom_Openingcontact_Window_State") == CLOSED: sendCommand("pGF_Guestroom_Shutter_Control", DOWN)
                if getItemState("pGF_Guesttoilet_Openingcontact_Window_State") == CLOSED: sendCommand("pGF_Guesttoilet_Shutter_Control", DOWN)

                if getItemState("pFF_Bedroom_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Bedroom_Shutter_Control", DOWN)
                if getItemState("pFF_Dressingroom_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Dressingroom_Shutter_Control", DOWN)
                if getItemState("pFF_Child1_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Child1_Shutter_Control", DOWN)
                if getItemState("pFF_Child2_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Child2_Shutter_Control", DOWN)
                if getItemState("pFF_Bathroom_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Bathroom_Shutter_Control", DOWN)
                if getItemState("pFF_Attic_Openingcontact_Window_State") == CLOSED: sendCommand("pFF_Attic_Shutter_Control", DOWN)
            elif getItemState("pOther_Presence_State").intValue() == 0:
                sendCommand("gShutters", UP)


@rule("rollershutter_auto.py")
class AtticSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Attic")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON:
            if getItemState("pOther_Automatic_State_Sunprotection_Attic") == ON:
                sendCommand("pFF_Attic_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Attic_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class BathroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Bathroom")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON:
            if getItemState("pOther_Automatic_State_Sunprotection_Bathroom") == ON:
                sendCommand("pFF_Bathroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Bathroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class DressingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Dressingroom")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON:
            if getItemState("pOther_Automatic_State_Sunprotection_Dressingroom") == ON:
                sendCommand("pFF_Dressingroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Dressingroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class BedroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Bedroom")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON:
            if getItemState("pOther_Automatic_State_Sunprotection_Bedroom") == ON:
                sendCommand("pFF_Bedroom_Shutter_Control", DOWN)
            else:
                sendCommand("pFF_Bedroom_Shutter_Control", UP)


@rule("rollershutter_auto.py")
class LivingroomSunprotectionRule:
    def __init__(self):
        self.triggers = [ItemStateChangeTrigger("pOther_Automatic_State_Sunprotection_Livingroom")]

    def execute(self, module, input):
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON and getItemState("pOther_Presence_State").intValue() == 0:
            if getItemState("pOther_Automatic_State_Sunprotection_Livingroom") == ON:
                sendCommand("pGF_Kitchen_Shutter_Control", DOWN)
                sendCommand("pGF_Livingroom_Shutter_Couch_Control", DOWN)
                if getItemState("pGF_Livingroom_Openingcontact_Window_Terrace_State") == CLOSED:
                    sendCommand("pGF_Livingroom_Shutter_Terrace_Control", DOWN)
            else:
                sendCommand("pGF_Kitchen_Shutter_Control", UP)
                sendCommand("pGF_Livingroom_Shutter_Couch_Control", UP)
                sendCommand("pGF_Livingroom_Shutter_Terrace_Control", UP)
