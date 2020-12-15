from shared.helper import rule, getItemState, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("auto.py")
class AutoProgramRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Christmas"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Lighting"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Sunprotection")
        ]

    def execute(self, module, input):
        active = []

        if getItemState("pOther_Manual_State_Auto_Rollershutter") == ON:        active.append("R")
        if getItemState("pOther_Manual_State_Auto_Sunprotection") == ON:        active.append("S")
        if getItemState("pOther_Manual_State_Auto_Lighting") == ON:             active.append("L")
        if getItemState("pOther_Manual_State_Auto_Christmas") == ON:            active.append("W")
        if getItemState("pOther_Manual_State_Auto_Attic_Light").intValue() > 1: active.append("D")
        if len(active) == 0:                                active.append("Inaktiv")

        msg = ", ".join(active)

        postUpdateIfChanged("pOther_State_Message_Auto", msg)
