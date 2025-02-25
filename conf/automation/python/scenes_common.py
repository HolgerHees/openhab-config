from openhab import rule, Registry
from openhab.triggers import ItemCommandTrigger


#@rule()
## watch tv
#class ScenesCommon_pOther_Scene1:

#@rule()
## wakeup
#class ScenesCommon_pOther_Scene2:

#@rule()
## go to bed
#class ScenesCommon_pOther_Scene3:

# pOther_Scene4 => is handled in presence_detection.py


@rule(
    triggers = [
        ItemCommandTrigger("pOther_Scene5",command="ON")
    ]
)
# go outside
class ScenesCommon_pOther_Scene5:
    def execute(self, module, input):
        Registry.getItem("pOutdoor_Carport_Automatic_Switch").sendCommand(OFF)
        Registry.getItem("pOutdoor_Streedside_Frontdoor_Automatic_Switch").sendCommand(OFF)
        Registry.getItem("pOutdoor_Terrace_Automatic_Switch").sendCommand(OFF)
        Registry.getItem("pOutdoor_Streedside_Garage_Automatic_Switch").sendCommand(OFF)
        Registry.getItem("pOutdoor_Garden_Garage_Automatic_Switch").sendCommand(ON)
        Registry.getItem("pOutdoor_Toolshed_Right_Automatic_Switch").sendCommand(OFF)

        #Registry.getItem("pOther_Scene5".postUpdate(OFF)

#@rule()
#class ScenesCommon_pOther_Scene6:
