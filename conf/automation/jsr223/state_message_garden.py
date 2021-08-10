from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger


@rule("state_message_garden.py")
class StateMessageGardenRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Watering_Logic_Program_State"),
            ItemStateChangeTrigger("gOutdoor_Watering_Circuits"),
            ItemStateChangeTrigger("pOutdoor_Light_Automatic_Main_Switch")
        ]

    def execute(self, module, input):
        active = []
        
        if getItemState("gOutdoor_Watering_Circuits") == ON:
            active.append(u"Bewässerung")

        if getItemState("pOutdoor_Light_Automatic_Main_Switch") != ON:
            active.append(u"Beleuchtung")

        if len(active) == 0:
            active.append(u"Alles ok")

        msg = ", ".join(active)

        postUpdateIfChanged("pOther_State_Message_Garden", msg)
