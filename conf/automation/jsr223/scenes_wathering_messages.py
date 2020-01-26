from custom.helper import rule, getItemState, postUpdateIfChanged
from core.triggers import ItemStateChangeTrigger


@rule("scenes_wathering_messages.py")
class ScenesWatheringMessagesRule:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("Watering_Program_State"),
            ItemStateChangeTrigger("Watering_Circuits"),
            ItemStateChangeTrigger("Motiondetector_Outdoor_Switch")
        ]

    def execute(self, module, input):
        active = []
        
        if getItemState("Watering_Circuits") == ON:
            active.append(u"Bewässerung")

        if getItemState("Motiondetector_Outdoor_Switch") != ON:
            active.append(u"Beleuchtung")

        if len(active) == 0:
            active.append(u"Alles normal")

        msg = ", ".join(active)

        postUpdateIfChanged("GardenStatus", msg)
