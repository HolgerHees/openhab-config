# -*- coding: utf-8 -*-

import random
from shared.actions import HTTP
import json

from configuration import customConfigs
from shared.helper import getItemState, postUpdate



class ShuffleHelper:
    history = None

    _synonyms = {
        u"Gute Nacht": [
            u"Gute Nacht",
            u"Schlaf gut",
            u"Schlaf schön",
            u"Träume was schönes",
            u"Träume was süsses",
            u"Schöne Träume",
            u"Süsse Traeume",
            u"Schlummer gut",
            u"Angenehme Nachtruhe",
            u"Wünsche dir behagliche Träume",
            u"Wünsche dir einen erholsamen Schlaf",
            u"Wünsche dir entspanntes Einschlafen",
            u"Wünsche dir ruhige Träume",
            u"Wünsche dir süsse Traeume",
            u"Wünsche dir behagliche Traeume",
            u"Wünsche dir eine sanfte Nachtruhe",
            u"Wünsche dir einen ruhigen Schlaf"
        ],
        u"Willkommen zu Hause": [
            [
                u"Willkommen zu Hause",
                u"Willkommen zurück",
                u"Herzlich willkommen daheim",
                { False: u"Schön, dass du wieder zu Hause bist", True: u"Schön, dass ihr wieder zu Hause seid" },
                { False: u"Schön das du wieder da bist", True: u"Schön, dass ihr wieder da seid" },
                { False: u"Schön das du zurück bist", True: u"Schön, dass ihr wieder zurück seid" },
                { False: u"Schön dich zu sehen", True: u"Schön, euch zu sehen" }
            ],
            [
                u"",
                u"",
                u"",
                u"",
                u"Ich hab mich schon gelangweilt",
                { False: u"War ganzschön langweilig ohne dich", True: u"War ganzschön langweilig ohne euch" },
                { False: u"Ich hoffe du hattest einen angenehmen Tag", True: u"Ich hoffe ihr hattet einen angenehmen Tag" }
            ]
        ]
    }

    @staticmethod
    def getRandomSynonym2(logging, words, flag = None):
        if ShuffleHelper.history is None:
            history = getItemState("VoiceAnswerHistory").toString()
            try:
                ShuffleHelper.history = json.loads(history)
            except:
                ShuffleHelper.history = {}

        if words not in ShuffleHelper.history:
            ShuffleHelper.history[words] = []

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={}".format(customConfigs['gemini_token'])
        data = { "contents": [ {"parts" : [ { "text" : u"{}".format( words ) } ] } ], "generation_config": { "temperature": 0.1, "candidate_count": 1 } }
        #data = { "contents": [ {"parts" : [ { "text" : u"Sag mir {} mit anderen Worten ausser {}".format( words, ",".join(ShuffleHelper.history[words]) ) } ] } ] }

        result = HTTP.sendHttpPostRequest(url, "application/json", json.dumps(data), {}, 5000)
        answer = json.loads(result)
        text = answer['candidates'][0]['content']['parts'][0]['text'].strip()

        logging.info(str(answer))

        ShuffleHelper.history[words].append(text)
        if len(ShuffleHelper.history[words]) > 50:
            ShuffleHelper.history[words] = ShuffleHelper.history[words][-50:]
        choice = random.choice(ShuffleHelper.history[words])

        postUpdate("VoiceAnswerHistory",json.dumps(ShuffleHelper.history))

        #logging.info(text + " " + choice)

        return choice

    @staticmethod
    def getRandomSynonym(logging, words, flag = None):
        #if words == "Gute Nacht":
        #    return ShuffleHelper.getRandomSynonym(logging, words, flag)

        if words in ShuffleHelper._synonyms:
            values = ShuffleHelper._synonyms[words]
            if type(values[0]) is list:
                parts = []
                for _values in values:
                    choice = random.choice(_values)
                    if type(choice) is dict:
                        parts.append(choice[flag])
                    elif len(choice) > 0:
                        parts.append(choice)
                return u"{}.".format( u". ".join(parts) )
            else:
                return u"{}.".format( random.choice(ShuffleHelper._synonyms[words]) )
        return words

