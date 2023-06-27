from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger


@rule("state_message_auto.py")
class AutoProgramRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Christmas"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Lighting"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Sunprotection")
        ]

    def format(self, itemName, shortcut):
        return shortcut if getItemState(itemName) == ON else u"X"

    def execute(self, module, input):
        active = []

        active.append(self.format("pOther_Manual_State_Auto_Rollershutter",u"R"))
        active.append(self.format("pOther_Manual_State_Auto_Sunprotection",u"S"))
        active.append(self.format("pOther_Manual_State_Auto_Lighting",u"L"))
        active.append(self.format("pOther_Manual_State_Auto_Christmas",u"W"))
        active.append(self.format("pOther_Manual_State_Auto_Attic_Light",u"D"))

        msg = u"-".join(active)

        postUpdateIfChanged("pOther_State_Message_Auto", msg)
