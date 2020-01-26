from custom.helper import rule, getItemState, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("auto.py")
class AutoProgramRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Auto_Attic_Light"),
            ItemStateChangeTrigger("Auto_Christmas"),
            ItemStateChangeTrigger("Auto_Lighting"),
            ItemStateChangeTrigger("Auto_Rollershutter"),
            ItemStateChangeTrigger("Auto_Sunprotection")
        ]

    def execute(self, module, input):
        active = []

        if getItemState("Auto_Rollershutter") == ON:        active.append("R")
        if getItemState("Auto_Sunprotection") == ON:        active.append("S")
        if getItemState("Auto_Lighting") == ON:             active.append("L")
        if getItemState("Auto_Christmas") == ON:            active.append("W")
        if getItemState("Auto_Attic_Light").intValue() > 1: active.append("D")
        if len(active) == 0:                                active.append("Inaktiv")

        msg = ", ".join(active)

        postUpdateIfChanged("AutoStatus", msg)
