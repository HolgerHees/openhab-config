from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger


@rule(
    triggers = [
        ItemStateChangeTrigger("pOutdoor_Astro_Total_Radiation")
    ]
)
class LightLevel:
    def execute(self, module, input):
        #https://www.extrica.com/article/21667
        radiation = Registry.getItemState("pOutdoor_Astro_Total_Radiation").doubleValue()
        Registry.getItem("pOutdoor_Astro_Light_Level").postUpdateIfDifferent( radiation * 118.0 )
