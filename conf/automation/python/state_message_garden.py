from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

import scope


@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_State"),
        ItemStateChangeTrigger("gOutdoor_Watering_Circuits"),
        ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch")
    ]
)
class Main:
    def execute(self, module, input):
        active = []
        
        if Registry.getItemState("gOutdoor_Watering_Circuits") == scope.ON:
            active.append(u"Bewässerung")

        if Registry.getItemState("pOutdoor_Light_Automatic_Main_Switch") != scope.ON:
            active.append(u"Beleuchtung")

        if len(active) == 0:
            active.append(u"Alles ok")

        msg = ", ".join(active)

        Registry.getItem("pOther_State_Message_Garden").postUpdateIfDifferent(msg)
