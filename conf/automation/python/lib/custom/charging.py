from datetime import datetime, timedelta
import time

class ChargingHelper:
    def __init__(self, stock_price_persistence ):
        self.stock_price_persistence = stock_price_persistence

        self.last_price_day = -1

        self.price_map = None
        self.date_map = None

        self.is_grid_mode = False

    @staticmethod
    def findValueFromMap(key, values):
        slot_key = None
        slot_value = None
        for _slot_key, _slot_value in values.items():
            if slot_value is None or key > _slot_key:
                slot_key = _slot_key
                slot_value = _slot_value
            elif key < _slot_key:
                max_diff_key = _slot_key - slot_key
                max_diff_value = _slot_value - slot_value

                diff_key = key - slot_key

                slot_value += (max_diff_value * (diff_key / max_diff_key))
                break
        return slot_value

    def refresh(self, now, is_grid_mode):
        self.is_grid_mode = is_grid_mode

        last_price_date = self.stock_price_persistence.persistedState(now + timedelta(days=2)).getTimestamp()
        if self.last_price_day != last_price_date.day:
            prices = self.stock_price_persistence.getAllStatesBetween(now - timedelta(minutes=15), last_price_date)

            price_map = {}
            date_map = []
            for price in prices:
                value = price.getState().doubleValue()

                price_date = price.getTimestamp()
                slot = {"price": value, "start": price_date, "end": price_date + timedelta(minutes=15)}

                date_map.append(slot)

                if value not in price_map:
                    price_map[value] = []
                price_map[value].append(slot)

            for price, slots in price_map.items():
                slots.sort(key=lambda x: x["start"].timestamp(), reverse=True)

            self.date_map = date_map
            self.price_map = dict(sorted(price_map.items(), key=lambda item: item[0]))
            self.last_price_day = last_price_date.day

        if self.date_map[0]["end"] < now:
            self.price_map[self.date_map[0]["price"]].remove(self.date_map[0])
            del self.date_map[0]

    def isGridMode(self):
        return self.is_grid_mode

    def calculateRemainingSlots(self, start_time, end_time, current_time, current_energy_soc, target_energy_soc, min_charging_power, max_charging_power, charging_callback):
        missing_energy = target_energy_soc - current_energy_soc

        start_time = current_time if current_time > start_time else start_time

        remaining_slots_charged_energy = 0
        remaining_slots = []
        for price in list(self.price_map.keys()):
            for slot in self.price_map[price]:
                if slot["end"].timestamp() < start_time.timestamp() or slot["end"].timestamp() > end_time.timestamp():
                    continue

                remaining_slots_charged_energy += max_charging_power / 4
                remaining_slots.append({ "price": price, "start": slot["start"], "end": slot["end"]})

            if remaining_slots_charged_energy >= missing_energy:
                break

        active_slot = next_slot = charge_msg = None
        if len(remaining_slots) > 0:
            min_price = remaining_slots[0]["price"]
            max_price = remaining_slots[-1]["price"]

            remaining_slots.sort(key=lambda item: item["start"].timestamp()) # sort by timestamp for performance reason

            # If slot count does not matter (like for the highest price which is not fully used), distribute the load across all remaining slots with "fixed" power
            if remaining_slots_charged_energy > missing_energy:
                # remove "unneeded" leading slots, if they are from the same price as we use for "override_power"
                while remaining_slots[0]["price"] == max_price:
                    if remaining_slots_charged_energy - max_charging_power / 4 < missing_energy:
                        break
                    remaining_slots_charged_energy -= max_charging_power / 4
                    remaining_slots.pop(0)

                max_price_count = sum(1 for slot in remaining_slots if slot["price"] == max_price)
                override_power = round( max_charging_power - (( remaining_slots_charged_energy - missing_energy ) / max_price_count) * 4, 2)
                if override_power < min_charging_power:
                    override_power = min_charging_power
                charged_enery = missing_energy
            else:
                override_power = None
                charged_enery = remaining_slots_charged_energy

            next_slot = remaining_slots[0]
            active_slot = next_slot if next_slot is not None and current_time >= next_slot["start"] else None
            if active_slot is not None:
                charging_power = charging_callback(current_energy_soc)
                active_slot["charging_power"] = override_power if override_power is not None and max_price == active_slot["price"] and charging_power > override_power else charging_power
                next_slot = remaining_slots[1] if len(remaining_slots) > 1 else None

            if next_slot is not None:
                charging_power = charging_callback(current_energy_soc + ( active_slot["charging_power"] / 4 if active_slot is not None else 0 ))
                next_slot["charging_power"] = override_power if override_power is not None and max_price == next_slot["price"] and charging_power > override_power else charging_power

            #print(remaining_slots_charged_energy, missing_energy)
            #charging_power = charging_callback(current_energy_soc)
            #energy = 0.0
            #print("CHARGIN POWER", charging_power, override_power)
            #for slot in remaining_slots:
            #    _charging_power = override_power if override_power is not None and max_price == slot["price"] and charging_power > override_power else charging_power
            #    print(max_price == slot["price"], slot["price"], _charging_power)
            #    energy += _charging_power / 4
            #print(energy)

            hours, remainder = divmod(len(remaining_slots) * 900, 3600)
            minutes, _ = divmod(remainder, 60)

            price_msg = "{:.2f}-{:.2f}".format(min_price, max_price) if min_price != max_price else "{:.2f}".format(min_price)
            between_msg = "{} and {}".format(remaining_slots[0]["start"].strftime('%H:%M'), remaining_slots[-1]["end"].strftime('%H:%M'))
            charge_msg = "🔋 Total {:.2f}kWh 💰 Price {}€/kWh 🕐 Between {} • Duration {:02d}:{:02d} ({} slots)".format(charged_enery, price_msg, between_msg, hours, minutes, len(remaining_slots))

        return [active_slot, next_slot, charge_msg]

    def calculateRequestedPower(self, start_time, end_time, current_time, current_energy_soc, target_energy_soc, min_charging_power, max_charging_power, charging_callback):
        requested_power = charge_msg = None
        state = "Inactive"

        if self.is_grid_mode:
            if target_energy_soc <= current_energy_soc:
                state_msg = "No charging needed"
            elif self.date_map[-1]["end"] < end_time:
                state_msg = "Prices are not available yet"
            else:
                active_slot, next_slot, charge_msg = self.calculateRemainingSlots(start_time, end_time, current_time, current_energy_soc, target_energy_soc, min_charging_power, max_charging_power, charging_callback)
                if active_slot is not None:
                    requested_power = active_slot["charging_power"]
                    if ( next_slot is None or next_slot["start"] != active_slot["end"] ) and start_time >= active_slot["end"] - timedelta(minutes=1):
                        state = "Ending"
                        requested_power = None # if it ends in one minute, reset the requested power to trigger the inverter's watchdog timer within one minute
                    else:
                        state = "Active"
                    state_msg = "With {:.2f}kWh for {:.2f}€/kWh".format(active_slot["charging_power"], active_slot["price"])
                else:
                    state_msg = "No slot matches"

                if next_slot is not None:
                    state_msg = "{} • Next slot at {} with {:.2f}kWh for {:.2f}€/kWh".format(state_msg, next_slot["start"].strftime('%H:%M'), next_slot["charging_power"], next_slot["price"])
        else:
            state_msg = "No charging possible"

        return [requested_power, state, state_msg, charge_msg]
