import threading
import java
import json
import time

from openhab import rule, Registry, logger, services
from openhab.triggers import ItemStateChangeTrigger
from openhab.actions import Voice, HTTP

import http.client

import scope


from org.openhab.core.voice import DialogContext
#from org.openhab.core.audio import AudioManager;
#from org.openhab.core.audio import AudioSink;
#from org.openhab.core.audio import AudioSource;
from org.openhab.core.audio import AudioFormat;
from org.openhab.core.audio import URLAudioStream;
from openhab.triggers import GenericCronTrigger, ItemStateUpdateTrigger

class VoiceAssistent(threading.Thread):
    voice_assistant = None

    @staticmethod
    def stopListening():
        if VoiceAssistent.voice_assistant is None:
            return
        VoiceAssistent.voice_assistant.isRunning = False
        VoiceAssistent.voice_assistant = None

    @staticmethod
    def startListening():
        if VoiceAssistent.voice_assistant is not None:
            return
        VoiceAssistent.voice_assistant = VoiceAssistent()
        VoiceAssistent.voice_assistant.start()

    def __init__(self):
      threading.Thread.__init__(self)

      audio = services.getService("org.openhab.core.audio.AudioManager")
      self.source = audio.getSource("esphome:device:home-speaker-1:source:voice_assistant")

      self.sink = audio.getSink("esphome:device:home-speaker-1:sink:")
      self.sink.process(None)

      self.voice = services.getService("org.openhab.core.voice.VoiceManager")
      self.locale = services.getService("org.openhab.core.i18n.LocaleProvider")

      self.isRunning = True

    def run(self):
        while self.isRunning:
            logger.info("Start listening ...")
            start = time.time()
            message = self.voice.transcribe("esphome:device:home-speaker-1:source:voice_assistant", "whisperstt", self.locale.getLocale())
            end = time.time()
            logger.info("Listing ends after {}".format(end - start))

            if not self.isRunning:
                break

            logger.info("Start interpreting ...")
            start = time.time()
            answer = Voice.interpret(message, "gemini", "voice-assistent", "get-date-time,item-get-state,item-send-command")
            end = time.time()
            logger.info("Interpreting ends after {}".format(end - start))

            if not self.isRunning:
                break

            logger.info("Start answering ...")
            start = time.time()
            self.say(answer)
            end = time.time()
            logger.info("Answering ends after {}".format(end - start))

            break

        logger.info("Stop listening ...")

    def say(self, message):
        headers = {}
        content = {
            "model": "speaches-ai/piper-de_DE-eva_k-x_low",
            "input": message,
            "voice": "eva_k",
            "response_format": "flac",
            "speed": "1"
        }
        connection = http.client.HTTPConnection("speaches", "8000")
        connection.request("POST", "/v1/audio/speech", json.dumps(content), headers)
        response = connection.getresponse()
        with open('/openhab/conf/html/voice/response.flac', 'wb') as fw:
            fw.write(response.read())

        self.sink.process(URLAudioStream("http://192.168.0.50:10115/static/voice/response.flac"))

voice_assistant = VoiceAssistent()
#voice_assistant.start()




#voice_assistant = VoiceAssistent()
#voice_assistant.say("22°C")


#@rule(
#    triggers = [
#        ItemStateUpdateTrigger("pGF_Workroom_SmartSpeaker_Activated")
#    ]
#)
#class MainSmartSpeaker:
#    def execute(self, module, input):
#        if input['event'].getItemState() == scope.ON:
#            VoiceAssistent.startListening()
#        else:
#            VoiceAssistent.stopListening()

#scope.lifecycleTracker.addDisposeHook(VoiceAssistent.stopListening)


#Voice.stopDialog("esphome:device:home-speaker-1:source:voice_assistant")
#Voice.startDialog("rustpotterks", "whisperstt", "openaitts", "openaitts:jarvis", "rulehli", "esphome:device:home-speaker-1:source:voice_assistant", "esphome:device:home-speaker-1:sink:", "de-DE", "Hey Marvin", "pOther_SmartSpeaker_VoiceCommand")










# TTS
# uv tool run speaches-cli registry ls --task text-to-speech | grep "id\":"
# uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX-int8
