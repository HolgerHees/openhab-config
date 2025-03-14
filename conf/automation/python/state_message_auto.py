from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from custom.flags import FlagHelper

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pOther_Manual_State_Holiday"),
        ItemStateChangeTrigger("pOther_Manual_State_Heating"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Attic_Light"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Christmas"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Lighting"),
        ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch"),
        ItemStateChangeTrigger("pOther_Manual_State_Auto_Rollershutter")
    ]
)
class StateMessageAuto:
    def format(self, item_name, shortcut, check = None):
        return shortcut if ( Registry.getItemState(item_name) == scope.ON if check is None else check ) else "".join( [ "{}\u0336".format(c) for c in shortcut ] )
        #return shortcut if Registry.getItemState(item_name) == scope.ON else "{}\u0336".format(shortcut)

    def execute(self, module, input):
        active1 = []
        active1.append(self.format("pOther_Manual_State_Holiday",""))

        heatingMode = Registry.getItemState("pOther_Manual_State_Heating").intValue()

        if heatingMode == 0:
            active1.append("h\u0336{}\u0336".format(heatingMode))
        else:
            active1.append("h{}".format(heatingMode))

        active2 = []
        active2.append(self.format("pOutdoor_Light_Automatic_Main_Switch","al"))
        active2.append(self.format("pOther_Manual_State_Auto_Lighting","il"))

        flags = Registry.getItemState("pOther_Manual_State_Auto_Rollershutter").intValue()
        if FlagHelper.hasFlag(FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, flags) and FlagHelper.hasFlag(FlagHelper.AUTO_ROLLERSHUTTER_SHADING, flags):
            active2.append("tb")
        elif FlagHelper.hasFlag(FlagHelper.AUTO_ROLLERSHUTTER_TIME_DEPENDENT, flags):
            active2.append("tb\u0336")
        elif FlagHelper.hasFlag(FlagHelper.AUTO_ROLLERSHUTTER_SHADING, flags):
            active2.append("t\u0336b")
        elif FlagHelper.hasFlag(FlagHelper.OFF, flags):
            active2.append("t\u0336b\u0336")
        else:
            self.logger.error("Unknown flag {}".format(flags))

        active3 = []
        active3.append(self.format("pOther_Manual_State_Auto_Christmas","w"))
        active3.append(self.format("pOther_Manual_State_Auto_Attic_Light","d", Registry.getItemState("pOther_Manual_State_Auto_Attic_Light").intValue() != 1))

        msg = "{},{},{}".format( ",".join(active1), ",".join(active2), ",".join(active3) )

        Registry.getItem("pOther_State_Message_Auto").postUpdateIfDifferent(msg)
