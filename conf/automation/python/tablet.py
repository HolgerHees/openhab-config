from openhab import rule, Registry, Timer
from openhab.actions import HTTP
from openhab.triggers import ItemStateChangeTrigger, ItemCommandTrigger, SystemStartlevelTrigger

from custom.presence import PresenceHelper
from custom.weather import WeatherHelper

from configuration import customConfigs

import time
import json


BRIGHTNESS_LIMIT = 200
BRIGHTNESS_MAX = int(BRIGHTNESS_LIMIT * 1.00)
BRIGHTNESS_MID = int(BRIGHTNESS_LIMIT * 0.66)
BRIGHTNESS_MIN = int(BRIGHTNESS_LIMIT * 0.33)


@rule(
    triggers = [
        SystemStartlevelTrigger(80),

        ItemStateChangeTrigger("pOther_Presence_State"),

        ItemStateChangeTrigger("pGF_Livingroom_Shutter_Terrace_Control"),
        ItemStateChangeTrigger("pGF_Livingroom_Shutter_Couch_Control"),
        ItemStateChangeTrigger("pGF_Kitchen_Shutter_Control"),
        ItemStateChangeTrigger("pGF_Livingroom_Light_Diningtable_Brightness"),
        ItemStateChangeTrigger("pGF_Livingroom_Light_Couchtable_Brightness"),
        ItemStateChangeTrigger("pGF_Kitchen_Light_Ceiling_Brightness"),

        ItemStateChangeTrigger("pOutdoor_WeatherStation_Light_Level")
    ]
)
class TabletScreen:
    def __init__(self):
        self.screenStateInProgress = False
        self.screenStateRequested = 'Off'
        self.screenStateActive = 'Off'

        self.screenBrightnessInProgress = False
        self.screenBrightnessRequested = 0
        self.screenBrightnessActive = 0
        self.screenBrightnessTimer = None

    def submitCmd(self, cmd, retry = 0):
        try:
            response_json = HTTP.sendHttpGetRequest(customConfigs['livingroom_api'] + "&cmd={}".format(cmd))
            response = json.loads(response_json)

            if response["status"] == 'OK':
                return True

            self.logger.info(response_json)
            return False
        except Exception as e:
            if retry == 0:
                self.logger.error("{}: {}".format(e.__class__, str(e)))
                self.logger.error("Tablet: Can't reach tablet")
                return False
            else:
                self.logger.warn("Tablet: retry in 1 seconds")
                time.sleep(1)
                return self.submitCmd(cmd, retry - 1)

    def getItemState(self, item, input = None):
        if input is not None and input["event"].getItemName() == item:
            return input["event"].getItemState()
        return Registry.getItemState(item)

    def getRequestedScreenState(self, input = None):
        return "Off" if self.getItemState("pOther_Presence_State", input).intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING] else "On"

    def getRequestedScreenBrightness(self, input = None):
        isRollershutterOpen = self.getItemState("pGF_Livingroom_Shutter_Terrace_Control", input).intValue() == 0 or self.getItemState("pGF_Livingroom_Shutter_Couch_Control", input).intValue() == 0 or self.getItemState("pGF_Kitchen_Shutter_Control", input).intValue() == 0
        isCeilingLightOn = self.getItemState("pGF_Livingroom_Light_Diningtable_Brightness", input).intValue() > 70 or self.getItemState("pGF_Livingroom_Light_Couchtable_Brightness", input).intValue() > 70 or self.getItemState("pGF_Kitchen_Light_Ceiling_Brightness", input).intValue() > 70
        currentLuxLevel = WeatherHelper.getLightLevelItemState().intValue()

        outdoorScreenBrightness = 0
        if isRollershutterOpen:
            if currentLuxLevel > 500 or (self.screenBrightnessRequested == BRIGHTNESS_MAX and currentLuxLevel > 100):
                outdoorScreenBrightness = BRIGHTNESS_MAX
            elif currentLuxLevel > 0 or self.screenBrightnessRequested == BRIGHTNESS_MID:
                outdoorScreenBrightness = BRIGHTNESS_MID

        indoorScreenBrightness = 0
        if isCeilingLightOn:
            indoorScreenBrightness = BRIGHTNESS_MID
        else:
            indoorScreenBrightness = BRIGHTNESS_MIN

        return outdoorScreenBrightness if outdoorScreenBrightness > indoorScreenBrightness else indoorScreenBrightness

    def _switchScreenState(self, requested_action):
        is_success = self.submitCmd("screen{}".format(requested_action), 5)

        if is_success:
            self.logger.info("Tablet: state change to '{}'".format(requested_action))
            self.screenStateActive = requested_action
        else:
            self.logger.error("Tablet: state change not successful")
            self.screenStateRequested = self.screenStateActive

        # reapply skipped state change
        if self.screenStateRequested != self.screenStateActive:
            self.logger.info("Tablet: skipped state change apply")
            return self._switchScreenState(self.screenStateRequested)

        return is_success

    def _processScreenState(self, requested_action):
        self.screenStateInProgress = True
        is_success = self._switchScreenState(requested_action)
        self.screenStateInProgress = False

        if is_success and self.screenStateActive == 'On':
            self.processScreenBrightness(self.getRequestedScreenBrightness())

    def processScreenState(self, requested_action):
        if requested_action == self.screenStateRequested:
            return False

        if self.screenStateInProgress:
            self.logger.info("Tablet: screen change in progress")
        else:
            self.logger.info("Tablet: try switching to {}".format(requested_action))
            Timer.createTimeout(0, self._processScreenState, args=[requested_action])

        self.screenStateRequested = requested_action
        return True

    def _switchScreenBrightness(self, screenBrightness, mode, apply_check):
        self.logger.info("Tablet: brightness {} change to '{}'".format(mode, screenBrightness))

        is_success = self.submitCmd("setStringSetting&key=screenBrightness&value={}".format(screenBrightness), 0)

        if is_success:
            self.logger.info("Tablet: brightness change successful")
            self.screenBrightnessActive = screenBrightness
        else:
            self.logger.error("Tablet: brightness change not successful")
            self.screenBrightnessRequested = self.screenBrightnessActive

        # reapply skipped brightness change
        if apply_check and self.screenBrightnessRequested != self.screenBrightnessActive:
            self.logger.info("Tablet: skipped brightness change apply")
            self._switchScreenBrightness(self.screenBrightnessRequested, mode, apply_check)

    def _processScreenBrightness(self, screenBrightness, mode, apply_check):
        self.screenBrightnessInProgress = True
        self._switchScreenBrightness(screenBrightness, mode, apply_check)
        self.screenBrightnessInProgress = False

    def processScreenBrightness(self, screenBrightness):
        if screenBrightness == self.screenBrightnessRequested or self.screenStateInProgress:
            return

        if self.screenBrightnessInProgress:
            self.logger.info("Tablet: brightness change in progress")
        else:
            if self.screenBrightnessTimer is not None:
                self.screenBrightnessTimer.cancel()
                self.screenBrightnessTimer = None

            if screenBrightness > self.screenBrightnessRequested:
                if screenBrightness != self.screenBrightnessActive:
                    self.screenBrightnessInProgress = True
                    Timer.createTimeout(0, self._processScreenBrightness, args=[screenBrightness, "immediately", True])

            elif screenBrightness < self.screenBrightnessRequested:
                # process already delayed brightness reduction
                if self.screenBrightnessRequested < self.screenBrightnessActive:
                    Timer.createTimeout(0, self._processScreenBrightness, args=[screenBrightness, "immediately", False])

                if screenBrightness != self.screenBrightnessActive:
                    self.screenBrightnessTimer = Timer.createTimeout(300,self._processScreenBrightness, args=[screenBrightness, "delayed", True])

        self.screenBrightnessRequested = screenBrightness

    def initDeviceStateAndBrightness(self):
        try:
            response_json = HTTP.sendHttpGetRequest(customConfigs['livingroom_api'] + "&cmd=deviceInfo")
            if response_json is not None:
                response = json.loads(response_json)
                self.screenStateRequested = self.screenStateActive = 'On' if response["screenOn"] else 'Off'
                self.screenBrightnessRequested = self.screenBrightnessActive = response["screenBrightness"]

                isTriggered = self.processScreenState(self.getRequestedScreenState())
                if not isTriggered and self.screenStateActive == 'On':
                    self.processScreenBrightness(self.getRequestedScreenBrightness())
            else:
                self.logger.error("Tablet: Got empty result. Retrigger in 15 seconds.")
                Timer.createTimeout(15, self.initDeviceStateAndBrightness)
        except Exception as e:
            self.logger.error("{}: {}".format(e.__class__, str(e)))
            self.logger.error("Tablet: Can't reach tablet")

    def execute(self, module, input):
        if input['event'].getType() == "StartlevelEvent":
            self.initDeviceStateAndBrightness()
        else:
            if input["event"].getItemName() == "pOther_Presence_State":
                self.processScreenState(self.getRequestedScreenState(input))
            elif self.screenStateActive == 'On':
                self.processScreenBrightness(self.getRequestedScreenBrightness(input))
