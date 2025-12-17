from openhab import rule, Registry
from openhab.triggers import ItemStateChangeTrigger

from shared.toolbox import ToolboxHelper

from datetime import datetime


@rule(
    triggers = [
        ItemStateChangeTrigger("pMobile_Socket_5_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_6_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_7_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_8_Total_Raw"),
        ItemStateChangeTrigger("pMobile_Socket_9_Total_Raw")
    ]
)
class SocketConsumption:
    def execute(self, module, input):
        now = datetime.now().astimezone()

        raw_item_name = input["event"].getItemName()
        real_item_name = "{}Consumption".format(raw_item_name[:-3])

        new_item_value = input["event"].getItemState().doubleValue()
        old_item_value = input["event"].getOldItemState().doubleValue()

        if new_item_value < old_item_value:
            if abs(new_item_value - old_item_value) <= 0.002:
                self.logger.info("Item {} ignored. {} => {}".format(raw_item_name, old_item_value, new_item_value))
                return
            else:
                self.logger.info("Item {} resetted. {} => {}".format(raw_item_name, old_item_value, new_item_value))
                old_item_value = 0

        real_item = Registry.getItem(real_item_name)

        diff = new_item_value - old_item_value
        real_item_value = real_item.getState().doubleValue() + diff
        real_item.postUpdate(real_item_value)

        start_of_the_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        old_daily_item_value = ToolboxHelper.getPersistedState(real_item, start_of_the_day ).doubleValue()
        Registry.getItem("{}Daily_Consumption".format(real_item_name[:-17])).postUpdate(real_item_value - old_daily_item_value)
