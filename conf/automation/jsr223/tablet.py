import time
import json

from shared.actions import HTTP
from shared.helper import rule, getItemState, postUpdate, sendCommandIfChanged, startTimer
from shared.triggers import ItemStateChangeTrigger, ItemCommandTrigger
from custom.presence import PresenceHelper

from custom_configuration import livingroom_api

BRIGHTNESS_LIMIT = 200
BRIGHTNESS_MAX = int(BRIGHTNESS_LIMIT * 1.00)
BRIGHTNESS_MID = int(BRIGHTNESS_LIMIT * 0.66)
BRIGHTNESS_MIN = int(BRIGHTNESS_LIMIT * 0.33)


@rule()
class TabletScreen:
    def __init__(self):
        self.triggers = [
            ItemStateChangeTrigger("pOther_Presence_State"),

            ItemStateChangeTrigger("pGF_Livingroom_Shutter_Terrace_Control"),
            ItemStateChangeTrigger("pGF_Livingroom_Shutter_Couch_Control"),
            ItemStateChangeTrigger("pGF_Kitchen_Shutter_Control"),
            ItemStateChangeTrigger("pGF_Livingroom_Light_Diningtable_Brightness"),
            ItemStateChangeTrigger("pGF_Livingroom_Light_Couchtable_Brightness"),
            ItemStateChangeTrigger("pGF_Kitchen_Light_Ceiling_Brightness"),

            ItemStateChangeTrigger("pOutdoor_WeatherStation_Light_Level")
        ]

        self.screenStateInProgress = False
        self.screenStateRequested = 'Off'
        self.screenStateActive = 'Off'

        self.screenBrightnessInProgress = False
        self.screenBrightnessRequested = 0
        self.screenBrightnessActive = 0
        self.screenBrightnessTimer = None

        self.initDeviceStateAndBrightness()

    def initDeviceStateAndBrightness(self):
        try:
            response_json = HTTP.sendHttpGetRequest(livingroom_api + "&cmd=deviceInfo")
            response = json.loads(response_json)

            self.screenStateRequested = self.screenStateActive = 'On' if response["screenOn"] else 'Off'
            self.screenBrightnessRequested = self.screenBrightnessActive = response["screenBrightness"]

            isTriggered = self.processScreenState(self.getRequestedScreenState())
            if not isTriggered and self.screenStateActive == 'On':
                self.processScreenBrightness(self.getRequestedScreenBrightness())
        except Exception as e:
            self.log.error("{}: {}".format(e.__class__, str(e)))
            self.log.error("Tablet: Can't reach tablet")

    def submitCmd(self, cmd, retry = 0):
        try:
            response_json = HTTP.sendHttpGetRequest(livingroom_api + "&cmd={}".format(cmd))
            response = json.loads(response_json)

            if response["status"] == 'OK':
                return True

            self.log.info(response_json)
            return False
        except Exception as e:
            if retry == 0:
                self.log.error("{}: {}".format(e.__class__, str(e)))
                self.log.error("Tablet: Can't reach tablet")
                return False
            else:
                self.log.warn("Tablet: retry in 1 seconds")
                time.sleep(1)
                return self.submitCmd(cmd, retry - 1)

    def getItemState(self, item, input = None):
        if input is not None and input["event"].getItemName() == item:
            return input["event"].getItemState()
        return getItemState(item)

    def getRequestedScreenState(self, input = None):
        return "Off" if self.getItemState("pOther_Presence_State", input).intValue() in [PresenceHelper.STATE_AWAY,PresenceHelper.STATE_SLEEPING] else "On"

    def getRequestedScreenBrightness(self, input = None):
        isRollershutterOpen = self.getItemState("pGF_Livingroom_Shutter_Terrace_Control", input).intValue() == 0 or self.getItemState("pGF_Livingroom_Shutter_Couch_Control", input).intValue() == 0 or self.getItemState("pGF_Kitchen_Shutter_Control", input).intValue() == 0
        isCeilingLightOn = self.getItemState("pGF_Livingroom_Light_Diningtable_Brightness", input).intValue() > 70 or self.getItemState("pGF_Livingroom_Light_Couchtable_Brightness", input).intValue() > 70 or self.getItemState("pGF_Kitchen_Light_Ceiling_Brightness", input).intValue() > 70
        currentLuxLevel = self.getItemState("pOutdoor_WeatherStation_Light_Level", input).intValue()

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
            self.log.info("Tablet: state change to '{}'".format(requested_action))
            self.screenStateActive = requested_action
        else:
            self.log.error("Tablet: state change not successful")
            self.screenStateRequested = self.screenStateActive

        # reapply skipped state change
        if self.screenStateRequested != self.screenStateActive:
            self.log.info("Tablet: skipped state change apply")
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
            self.log.info("Tablet: screen change in progress")
        else:
            self.log.info("Tablet: try switching to {}".format(requested_action))
            startTimer(self.log, 0, self._processScreenState, args=[requested_action])

        self.screenStateRequested = requested_action
        return True

    def _switchScreenBrightness(self, screenBrightness, mode, apply_check):
        self.log.info("Tablet: brightness {} change to '{}'".format(mode, screenBrightness))

        is_success = self.submitCmd("setStringSetting&key=screenBrightness&value={}".format(screenBrightness), 0)

        if is_success:
            self.log.info("Tablet: brightness change successful")
            self.screenBrightnessActive = screenBrightness
        else:
            self.log.error("Tablet: brightness change not successful")
            self.screenBrightnessRequested = self.screenBrightnessActive

        # reapply skipped brightness change
        if apply_check and self.screenBrightnessRequested != self.screenBrightnessActive:
            self.log.info("Tablet: skipped brightness change apply")
            self._switchScreenBrightness(self.screenBrightnessRequested, mode, apply_check)

    def _processScreenBrightness(self, screenBrightness, mode, apply_check):
        self.screenBrightnessInProgress = True
        self._switchScreenBrightness(screenBrightness, mode, apply_check)
        self.screenBrightnessInProgress = False

    def processScreenBrightness(self, screenBrightness):
        if screenBrightness == self.screenBrightnessRequested or self.screenStateInProgress:
            return

        if self.screenBrightnessInProgress:
            self.log.info("Tablet: brightness change in progress")
        else:
            if self.screenBrightnessTimer is not None:
                self.screenBrightnessTimer.cancel()
                self.screenBrightnessTimer = None

            if screenBrightness > self.screenBrightnessRequested:
                if screenBrightness != self.screenBrightnessActive:
                    self.screenBrightnessInProgress = True
                    startTimer(self.log, 0, self._processScreenBrightness, args=[screenBrightness, "immediately", True])

            elif screenBrightness < self.screenBrightnessRequested:
                # process already delayed brightness reduction
                if self.screenBrightnessRequested < self.screenBrightnessActive:
                    startTimer(self.log, 0, self._processScreenBrightness, args=[screenBrightness, "immediately", False])

                if screenBrightness != self.screenBrightnessActive:
                    self.screenBrightnessTimer = startTimer(self.log, 300,self._processScreenBrightness, args=[screenBrightness, "delayed", True])

        self.screenBrightnessRequested = screenBrightness

    def execute(self, module, input):
        if input["event"].getItemName() == "pOther_Presence_State":
            self.processScreenState(self.getRequestedScreenState(input))
        elif self.screenStateActive == 'On':
            self.processScreenBrightness(self.getRequestedScreenBrightness(input))
