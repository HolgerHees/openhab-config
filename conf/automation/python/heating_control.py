from openhab import rule, Registry
from openhab.triggers import GenericCronTrigger, ItemStateChangeTrigger

from custom.heating.heating import Heating, HeatingLogHelper
from custom.heating.house import Window
from custom.heating.config import BuildingConfig
from custom.heating import HeatingHelper

from custom.ventilation import VentilationHelper
from custom.suncalculation import SunRadiation
from custom.sunprotection import SunProtectionHelper
from custom.weather import WeatherHelper
from custom.presence import PresenceHelper

from datetime import datetime, timedelta

import scope


heating = Heating(BuildingConfig)

@rule(
    triggers = [
       GenericCronTrigger("0 10 * * * ?")
    ]
)
class HeatingForecastRefresh:
    def execute(self, module, input):
        heating.refreshForecastInterval()

@rule(
    triggers = [
        # refresh heating ventile twice per week
        #GenericCronTrigger("*/15 * * * * ?"),
        GenericCronTrigger("0 */10 1 ? * MON,FRI"),
        GenericCronTrigger("0 0 2 ? * MON,FRI")
    ]
)
class Ventile:
    maintenanceMode = {}

    def checkCircuit(self, now, circuitName):
        circuitItem = Registry.getItem(circuitName)
        if now.hour == 2:
            if circuitName not in Ventile.maintenanceMode:
                return
            circuitItem.sendCommand(scope.ON if circuitItem.getState() == scope.OFF else scope.OFF)
            del Ventile.maintenanceMode[circuitName]
        elif circuitItem.getLastStateChange() is None or circuitItem.getLastStateChange() < now - timedelta(hours=24):
            circuitItem.sendCommand(scope.ON if circuitItem.getState() == scope.OFF else scope.OFF)
            Ventile.maintenanceMode[circuitName] = True

    def execute(self, module, input):
        now = datetime.now().astimezone()
        for room in filter( lambda room: room.getHeatingVolume() is not None,heating.getRooms()):
            self.checkCircuit(now, heating.getHeatingCircuitItemName(room))
            if room.hasAdditionalRadiator():
                self.checkCircuit(now, heating.getHeatingHKItemName(room))

@rule(
    triggers = [
        ItemStateChangeTrigger("pGF_Utilityroom_Ventilation_Mode")
    ]
)
class HeatingModeControl:
    def execute(self, module, input):
        is_cooling = Registry.getItemState("pGF_Utilityroom_Ventilation_Mode").intValue() == VentilationHelper.STATE_MODE_COOLING
        Registry.getItem("pGF_Utilityroom_Heatpump_Mode").postUpdateIfDifferent(HeatingHelper.STATE_MODE_SUSPENDED if is_cooling else HeatingHelper.STATE_MODE_HEATING)

@rule(
    triggers = [
        GenericCronTrigger("0 0 9,20 * * ?"),
        ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_PRESENT, previous_state=PresenceHelper.STATE_MAYBE_SLEEPING),
        ItemStateChangeTrigger("pOther_Presence_State", state=PresenceHelper.STATE_PRESENT, previous_state=PresenceHelper.STATE_SLEEPING),
        ItemStateChangeTrigger("pOther_Manual_State_Traveling")
    ]
)
class WarmWaterControl:
    def execute(self, module, input):
        # Travel
        if Registry.getItemState("pOther_Manual_State_Traveling") == scope.ON:
            Registry.getItem("pGF_Utilityroom_Heatpump_WW_Reduced").sendCommandIfDifferent(scope.ON)
        else:
            now = datetime.now().astimezone()

            # Evening
            if now.hour >= 20:
                Registry.getItem("pGF_Utilityroom_Heatpump_WW_Reduced").sendCommandIfDifferent(scope.ON)
            # Wakeup
            elif input['event'].getType() == "ItemStateChangedEvent" and input['event'].getItemName() == "pOther_Presence_State":
                Registry.getItem("pGF_Utilityroom_Heatpump_WW_Reduced").sendCommandIfDifferent(scope.OFF)
            # A heatup will happen with the wakup event or latest after 9
            elif now.hour >= 9:
                Registry.getItem("pGF_Utilityroom_Heatpump_WW_Reduced").sendCommandIfDifferent(scope.OFF)

@rule(
    triggers = [
        GenericCronTrigger("15 * * * * ?"),
#        GenericCronTrigger("*/15 * * * * ?"),
        ItemStateChangeTrigger("pOther_Manual_State_Traveling"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_Mode"),
        ItemStateChangeTrigger("pGF_Utilityroom_Heatpump_HK2_State")
    ]
#    , profile_code=True
)
class MainControl:
    def setHeatingCircuitControlStates(self, hk_reduced_state, hk_blocked_state, hk_heating_blocked_state):
        if Registry.getItem("pGF_Utilityroom_Heatpump_HK_Reduced").sendCommandIfDifferent(hk_reduced_state):
            self.logger.info(f"Heatpump: Switch 'HK Reduced' to {hk_reduced_state}")
        if Registry.getItem("pGF_Utilityroom_Heatpump_HK_Blocked").sendCommandIfDifferent(hk_blocked_state):
            self.logger.info(f"Heatpump: Switch 'HK Blocked' to {hk_blocked_state}")
        if Registry.getItem("pGF_Utilityroom_Heatpump_HK_Heating_Blocked").sendCommandIfDifferent(hk_heating_blocked_state):
            self.logger.info(f"Heatpump: Switch 'HK Heating Blocked' to {hk_heating_blocked_state}")

    def setHeatingControl(self, now, requested_volume, active_volume, nightmode_volume):
        hk_reduced_state = scope.ON if Registry.getItemState("pOther_Manual_State_Traveling") == scope.ON else scope.OFF

        # Night Mode Activated
        if nightmode_volume == heating.getTotalHeatingVolume():
            hk2_demand = False
            hk_night_mode = True

            hk_blocked_state = scope.ON
            hk_heating_blocked_state = scope.ON
        else:
            hk2_demand = requested_volume > 0
            hk_night_mode = False

            # CONTROL STATES
            hk_blocked_state = scope.ON if not hk2_demand else scope.OFF
            hk_heating_blocked_state = scope.ON if not hk2_demand or (nightmode_volume > 0 and active_volume < heating.getTotalHeatingVolume() * 0.5) else scope.OFF

        # Min Runtime Check
        if hk_heating_blocked_state == scope.ON and hk_heating_blocked_state != Registry.getItemState("pGF_Utilityroom_Heatpump_HK_Heating_Blocked") \
           and \
           Registry.getItemState("pGF_Utilityroom_Heatpump_HW_State") == scope.ON and Registry.getItem("pGF_Utilityroom_Heatpump_HW_State").getLastStateChange() > now - timedelta(minutes=30):
            self.logger.info("Heatpump: MIN RUNTIME FORCED")
            hk_night_mode = False
            hk_heating_blocked_state = scope.OFF

        self.setHeatingCircuitControlStates(hk_reduced_state, hk_blocked_state, hk_heating_blocked_state)

        Registry.getItem("pGF_Utilityroom_Heatpump_HK2_Demand").postUpdateIfDifferent(scope.ON if hk2_demand else scope.OFF)
        Registry.getItem("pGF_Utilityroom_Heatpump_HK_Night_Mode").postUpdateIfDifferent(scope.ON if hk_night_mode else scope.OFF)

        return hk2_demand, hk_night_mode

    def calculateHeatingVolume(self, cr):
        if Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_State") == scope.ON:
            active_volume = 0
            for room in heating.getHeatedRooms():
                circuit_item = heating.getHeatingCircuitItemName(room)
                if circuit_item in Ventile.maintenanceMode or Registry.getItemState(circuit_item) != scope.ON:
                    continue
                active_volume += cr.getRoomState(room.getName()).getPossibleHeatingVolume()
            active_volume = active_volume / 60
        else:
            active_volume = -1

        Registry.getItem("pGF_Utilityroom_Heatpump_HK2_Volumenstrom").postUpdateIfDifferent(active_volume)

    def execute(self, module, input):
        self.logger.info("--------: >>>" )

        now = datetime.now().astimezone()

        # REFRESH TEMPERATUR ITEM
        heating.refreshHeatingInterval(self.logger, now, WeatherHelper.getTemperatureItemName())

        measured_radiation_short_term = WeatherHelper.getSolarPowerStableItemState(10).doubleValue()
        measured_radiation_long_term = WeatherHelper.getSolarPowerStableItemState(30).doubleValue()
        measured_light_level_short_term = WeatherHelper.getLightLevelStableItemState(30).doubleValue()
        measured_light_level_long_term = WeatherHelper.getLightLevelStableItemState(60).doubleValue()

        _is_night_mode = Registry.getItemState("pGF_Utilityroom_Heatpump_HK_Night_Mode") == scope.ON
        _current_hk2_demand = Registry.getItemState("pGF_Utilityroom_Heatpump_HK2_Demand") == scope.ON
        cr, cr4, cr8 = heating.calculate(_is_night_mode, _current_hk2_demand, measured_radiation_short_term)

        # **** DEBUG ****
        HeatingLogHelper.logCoolingAndRadiations(self.logger, "FC8     ", cr8)
        HeatingLogHelper.logCoolingAndRadiations(self.logger, "FC4     ", cr4)
        HeatingLogHelper.logCoolingAndRadiations(self.logger, "Current ", cr, measured_radiation_long_term, measured_light_level_long_term)

        HeatingLogHelper.logHeatingStates(self.logger, heating, cr)
        # ***************

        self.logger.info("        : ---" )

        mode = Registry.getItemState("pGF_Utilityroom_Heatpump_Mode").intValue()
        if mode == HeatingHelper.STATE_MODE_MANUAL:
            self.logger.info("Demand  : SKIPPED • MANUAL MODE ACTIVE")
            self.setHeatingCircuitControlStates(scope.OFF, scope.OFF, scope.OFF)
        elif mode == HeatingHelper.STATE_MODE_SUSPENDED:
            self.logger.info("Demand  : SKIPPED • SUSPENDED MODE ACTIVE")
            self.setHeatingCircuitControlStates(scope.ON, scope.ON, scope.ON)
        elif mode == HeatingHelper.STATE_MODE_HEATING: # heating
            # *** CHECK OPEN WINDOWS AND NIGHT MODE ***
            longest_runtime = 0
            requested_volume = 0
            nightmode_volume = 0
            active_volume = 0
            for room in heating.getHeatedRooms():
                rs = cr.getRoomState(room.getName())
                hs = rs.getHeatingState()

                if rs.getNightMode():
                    nightmode_volume += room.getHeatingVolume()

                if rs.getActiveHeatingVolume() > 0:
                    active_volume += rs.getActiveHeatingVolume()

                _room_heating_demand = hs.isHeatingRequested()
                if _room_heating_demand:
                    requested_volume += rs.getPossibleHeatingVolume()
                    if hs.getDemandTime() > longest_runtime:
                        longest_runtime = hs.getDemandTime()

                # *** PERSIST HEATING CHARGE LEVEL ***
                Registry.getItem(heating.getHeatingBufferItemName(room)).postUpdateIfDifferent(rs.getHeatingChargedBuffer())

                # *** PERSIST HEATING TARGET TEMPERATURE ***
                Registry.getItem(heating.getHeatingTargetTemperatureItemName(room)).postUpdateIfDifferent(rs.getHeatingTargetTemperature() )

                # *** PERSIST HEATING DEMAND ***
                Registry.getItem(heating.getHeatingDemandItemName(room)).postUpdateIfDifferent(scope.ON if _room_heating_demand else scope.OFF)

                # *** CONTROL CIRCUITS AND HK ***
                circuit_item = heating.getHeatingCircuitItemName(room)
                if circuit_item not in Ventile.maintenanceMode:
                    if _room_heating_demand:
                        Registry.getItem(circuit_item).sendCommandIfDifferent(scope.ON)
                    else:
                        Registry.getItem(circuit_item).sendCommandIfDifferent(scope.OFF)

                if room.hasAdditionalRadiator():
                    circuit_item = heating.getHeatingHKItemName(room)
                    if circuit_item not in Ventile.maintenanceMode:
                        hk_on = _room_heating_demand and hs.getForcedInfo() == 'CF'
                        Registry.getItem(circuit_item).sendCommandIfDifferent(scope.ON if hk_on else scope.OFF)

            #night_mode_requested = _nightmode_volume > Heating.total_heating_volume * 0.8
            # *************************************************

            # ****************************
            hk2_demand, is_night_mode = self.setHeatingControl(now, requested_volume, active_volume, nightmode_volume)

            last_heating_demand_change = Registry.getItem("pGF_Utilityroom_Heatpump_HK_Night_Mode" if is_night_mode else "pGF_Utilityroom_Heatpump_HK2_Demand").getLastStateChange() # can be "getLastStateUpdate" datetime, because it is changed only from heating rule
            last_change_before_in_minutes = int((now - last_heating_demand_change).total_seconds() / 60)

            if last_change_before_in_minutes < 60 * 24:
                last_heating_change_formatted = last_heating_demand_change.strftime("%H:%M")

                hours, minutes = divmod(last_change_before_in_minutes, 60)
                last_change_before_formatted = f"{hours} hours and {minutes} minutes"
            else:
                last_heating_change_formatted = last_heating_demand_change.strftime("%d.%m. %H:%M")

                days, minutes = divmod(last_change_before_in_minutes, 60 * 24)
                hours, minutes = divmod(minutes, 60)
                last_change_before_formatted = f"{days} days and {hours} hours"

            if is_night_mode and not hk2_demand:
                self.logger.info(f"Demand  : Suspended mode since {last_change_before_formatted} ago ({last_heating_change_formatted})")
            else:
                endMsg = f" • {HeatingLogHelper.visualizeHeatingDemandTime(longest_runtime)} min. to go" if longest_runtime > 0 else ""
                self.logger.info(f"Demand  : {"ON" if hk2_demand else "OFF"} since {last_change_before_formatted} ago ({last_heating_change_formatted}){endMsg}")
            # ****************************

        self.calculateHeatingVolume(cr)

        self.setSunStates(now, cr, cr4, cr8, measured_radiation_long_term, measured_light_level_short_term, measured_light_level_long_term)

        self.logger.info(f"Headpump: HK reduced: {Registry.getItemState("pGF_Utilityroom_Heatpump_HK_Reduced")} • HK blocked: {Registry.getItemState("pGF_Utilityroom_Heatpump_HK_Blocked")} • HK heating blocked: {Registry.getItemState("pGF_Utilityroom_Heatpump_HK_Heating_Blocked")} • WW blocked: {Registry.getItemState("pGF_Utilityroom_Heatpump_WW_Reduced")}")

        self.logger.info("--------: <<<" )

    def setSunStates(self, now, cr, cr4, cr8, measured_radiation_long_term, measured_light_level_short_term, measured_light_level_long_term):
        cloud_cover = cr.getCloudCover()

        measured_radiation_short_term = cr.getSunRadiation()

        _, _sun_south_radiation, _sun_west_radiation, _sun_radiation, _sun_debug_info = SunRadiation.getSunPowerPerHour(now, cloud_cover, measured_radiation_short_term)
        effective_south_radiation_short_term = _sun_south_radiation / 60.0
        effective_west_radiation_short_term = _sun_west_radiation / 60.0
        #self.logger.info("Gemessen Avg 10 min until {}: {} {}".format(offset,effective_south_radiation_short_term, effective_west_radiation_short_term))

        _, _sun_south_radiation, _sun_west_radiation, _sun_radiation, _sun_debug_info = SunRadiation.getSunPowerPerHour(now, cloud_cover, measured_radiation_long_term)
        effective_south_radiation_long_term = _sun_south_radiation / 60.0
        effective_west_radiation_long_term = _sun_west_radiation / 60.0
        #self.logger.info("Gemessen Avg 30 min until {}: {} {}".format(offset,effective_south_radiation_long_term, effective_west_radiation_long_term))

        effective_south_radiation_max = cr.getSunSouthRadiationMax() / 60.0
        effective_west_radiation_max = cr.getSunWestRadiationMax() / 60.0
        #self.logger.info("Max: {} {}".format(effective_south_radiation_max, effective_west_radiation_max))

        current_outdoor_temperature = cr.getReferenceTemperature()
        current_outdoor_temperature4 = cr4.getReferenceTemperature()
        current_outdoor_temperature8 = cr8.getReferenceTemperature()

        fallback_target_temperature = cr.getRoomState("lGF_Livingroom").getHeatingTargetTemperature()

        #self.logger.info("{} {}".format(measured_radiation_short_term,measured_radiation_long_term))

        # terrace radiation
        effective_radiation_short_term = measured_radiation_short_term / 60.0
        effective_radiation_long_term = measured_radiation_long_term / 60.0

        # use same azimut and elevation as heating calculation
        azimut, elevation, min_elevation, _ = SunRadiation.getSunData( now )
        if elevation >= min_elevation:
            if azimut >= 120:
                # glare protection during workdays
                needed_sunprotection = azimut >= 180 \
                    and measured_light_level_short_term > 15000 and measured_light_level_long_term > 15000 \
                    and now.weekday() <= 4 and Registry.getItemState("pOther_Presence_Sandra_State") == scope.ON
                if not needed_sunprotection:
                    # hot stone protection
                    needed_sunprotection = effective_radiation_long_term > 8.0 and (current_outdoor_temperature > 26 or current_outdoor_temperature4 > 26)
                    if not needed_sunprotection:
                        # hot room protection (only above 18°C)
                        target_room_temperature = fallback_target_temperature
                        current_room_temperature = cr.getRoomState("lGF_Livingroom").getCurrentTemperature()
                        needed_sunprotection = self.isTooWarm(effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature )

                if needed_sunprotection:
                    if Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdateIfDifferent(SunProtectionHelper.STATE_TERRACE_CLOSED):
                        self.logger.info(f"DEBUG: SP switching 2 • Terrace • {effective_radiation_short_term:<0.1f} ({effective_radiation_long_term:<0.1f}) W/m² • {int(measured_light_level_short_term)} ({int(measured_light_level_long_term)}) lux")
                elif Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_OPEN:
                    Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdate(SunProtectionHelper.STATE_TERRACE_MAYBE_CLOSED)
                    self.logger.info(f"DEBUG: SP switching 1 • Terrace • {effective_radiation_short_term:<0.1f} ({effective_radiation_long_term:<0.1f}) W/m² • {int(measured_light_level_short_term)} ({int(measured_light_level_long_term)}) lux")
        elif azimut > 260.00:
            #if Registry.getItemState("pOther_Automatic_State_Sunprotection_Terrace").intValue() == SunProtectionHelper.STATE_TERRACE_OPEN:
            if Registry.getItem("pOther_Automatic_State_Sunprotection_Terrace").postUpdateIfDifferent(SunProtectionHelper.STATE_TERRACE_OPEN):
                self.logger.info("DEBUG: SP switching 0 • Terrace")

        for room in heating.getRooms():
            rs = cr.getRoomState(room.getName())

            target_room_temperature = fallback_target_temperature if room.getHeatingVolume() == None else rs.getHeatingTargetTemperature()

            for transition in room.transitions:
                if not transition.isWindow() or transition.getRadiationArea() == None or transition.getSunProtectionItem() == None:
                    continue

                #if current_outdoor_temperature < target_room_temperature and current_outdoor_temperature4 < target_room_temperature and current_outdoor_temperature8 < target_room_temperature:
                #    Registry.getItem(transition.getSunProtectionItem()).postUpdateIfDifferent(scope.OFF )
                #    continue

                current_room_temperature = rs.getCurrentTemperature()

                effective_radiation_short_term = effective_south_radiation_short_term if transition.getDirection() == 'south' else effective_west_radiation_short_term
                effective_radiation_long_term = effective_south_radiation_long_term if transition.getDirection() == 'south' else effective_west_radiation_long_term
                effective_radiation_max = effective_south_radiation_max if transition.getDirection() == 'south' else effective_west_radiation_max

                if Registry.getItemState(transition.getSunProtectionItem()) == scope.ON:
                    radiationTooLow = (effective_radiation_short_term < 2.0 and ( effective_radiation_max < 2.0 or effective_radiation_long_term < 2.0 ))

                    roomTemperatureTooCold = current_room_temperature < target_room_temperature - 0.7

                    radiationNotWayTooHigh = (effective_radiation_short_term < 12.0 and ( effective_radiation_max < 12.0 or effective_radiation_long_term < 12.0 ))
                    itsGettingColderAndRoomIsNotWarmEnoughForIt = ( \
                        current_outdoor_temperature < target_room_temperature - 0.2 \
                        and \
                        current_outdoor_temperature4 < target_room_temperature - 0.2 \
                        and \
                        current_room_temperature < target_room_temperature + ( 1.8 if radiationNotWayTooHigh else 0.8 ) \
                    )

                    if radiationTooLow or roomTemperatureTooCold or itsGettingColderAndRoomIsNotWarmEnoughForIt:
                        if Registry.getItem(transition.getSunProtectionItem()).getLastStateUpdate() < now - timedelta(minutes=60):
                            Registry.getItem(transition.getSunProtectionItem()).postUpdate(scope.OFF)
                            self.logger.info(f"DEBUG: SP switching OFF • {room.getName()} {effective_radiation_short_term} {effective_radiation_long_term} {effective_radiation_max}")
                        else:
                            self.logger.info(f"DEBUG: SP skipped OFF • {room.getName()} {effective_radiation_short_term} {effective_radiation_long_term} {effective_radiation_max}")
                else:
                    #self.logger.info("{} {}".format(room.getName(),effective_radiation_short_term))
                    #self.logger.info("{} {}".format(radiation_too_high,room_temperature_too_warm))
                    #self.logger.info("{} {}".format(current_room_temperature,target_room_temperature))
                    #self.logger.info("{} {}".format(current_outdoor_temperature,current_outdoor_temperature4))

                    tooWarm = self.isTooWarm(effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature )
                    if tooWarm:
                        if Registry.getItem(transition.getSunProtectionItem()).getLastStateUpdate() < now - timedelta(minutes=30):
                            Registry.getItem(transition.getSunProtectionItem()).postUpdate(scope.ON)
                            self.logger.info(f"DEBUG: SP switching ON • {room.getName()} {effective_radiation_short_term} {effective_radiation_long_term} {effective_radiation_max}")
                        else:
                            self.logger.info(f"DEBUG: SP skipped ON • {room.getName()} {effective_radiation_short_term} {effective_radiation_long_term} {effective_radiation_max}")

    def isTooWarm( self, effective_radiation_short_term, current_outdoor_temperature, current_outdoor_temperature4, current_room_temperature, target_room_temperature ):
        if current_outdoor_temperature <= 18 and current_outdoor_temperature4 <= 18:
            return False

        radiation_too_high = effective_radiation_short_term > 5.0

        room_temperature_too_warm = current_room_temperature > target_room_temperature - 0.5

        radiation_way_too_high = effective_radiation_short_term > 15.0
        its_getting_warmer_or_room_is_way_too_warm = ( \
            current_outdoor_temperature > target_room_temperature \
            or \
            current_outdoor_temperature4 > target_room_temperature \
            or \
            current_room_temperature > target_room_temperature + ( 2.0 if not radiation_way_too_high else 1.0 ) \
        )
        return radiation_too_high and room_temperature_too_warm and its_getting_warmer_or_room_is_way_too_warm
