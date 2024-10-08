from shared.helper import rule, getItemState

from custom.shuffle import ShuffleHelper


@rule("_test.py")
class TestRule:
    def __init__(self):

        self.log.info(str(getItemState("pGF_Utilityroom_Heating_Power")))
        pass
        #answer = ShuffleHelper.getRandomSynonym2(self.log, "Gute Nacht" )
        #self.log.info(answer)

    def execute(self, module, input):
        pass
  
  
            
             
                       
