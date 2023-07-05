from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger


@rule()
class StateMessageAuto:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Manual_State_Holiday"),
            ItemStateChangeTrigger("pOther_Manual_State_Summer"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Christmas"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Lighting"),
            ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch"),
            ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter")
        ]

    def format(self, itemName, shortcut, check = None):
        return shortcut if ( getItemState(itemName) == ON if check is None else check ) else "".join( [ u"{}\u0336".format(c) for c in shortcut ] )
        #return shortcut if getItemState(itemName) == ON else u"{}\u0336".format(shortcut)

    def execute(self, module, input):
        active1 = []
        active1.append(self.format("pOther_Manual_State_Holiday",u"U"))
        active1.append(self.format("pOther_Manual_State_Summer",u"S"))

        active2 = []
        active2.append(self.format("pOutdoor_Light_Automatic_Main_Switch",u"AL"))
        active2.append(self.format("pOther_Manual_State_Auto_Lighting",u"IL"))
        state = getItemState("pOther_Manual_State_Auto_Rollershutter").intValue()
        if state == 0:
            active2.append(u"TB\u0336")
        elif state == 1:
            active2.append(u"T")
        elif state == 2:
            active2.append(u"B")
        elif state == 3:
            active2.append(u"TB")

        active3 = []
        active3.append(self.format("pOther_Manual_State_Auto_Christmas",u"W"))
        active3.append(self.format("pOther_Manual_State_Auto_Attic_Light",u"D", getItemState("pOther_Manual_State_Auto_Attic_Light").intValue() != 1))

        msg = u"{} | {} | {}".format( u"-".join(active1), u"-".join(active2), u"-".join(active3) )

        postUpdateIfChanged("pOther_State_Message_Auto", msg)
