from shared.helper import rule, getItemState, postUpdateIfChanged
from shared.triggers import ItemStateChangeTrigger


@rule()
class AstroLightLevel:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOutdoor_Astro_Direct_Radiation")
        ]

    def execute(self, module, input):
        #https://www.extrica.com/article/21667

        radiation = getItemState("pOutdoor_Astro_Direct_Radiation").doubleValue()
        postUpdateIfChanged("pOutdoor_Astro_Light_Level", radiation * 118.0 )
