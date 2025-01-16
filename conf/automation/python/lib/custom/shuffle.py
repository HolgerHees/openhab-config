import random
import json

from openhab import logger, Registry
from openhab.actions import HTTP

from configuration import customConfigs


class ShuffleHelper:
    history = None

    _synonyms = {
        "Gute Nacht": [
            "Gute Nacht",
            "Schlaf gut",
            "Schlaf schön",
            "Träume was schönes",
            "Träume was süsses",
            "Schöne Träume",
            "Süsse Traeume",
            "Schlummer gut",
            "Angenehme Nachtruhe",
            "Wünsche dir behagliche Träume",
            "Wünsche dir einen erholsamen Schlaf",
            "Wünsche dir entspanntes Einschlafen",
            "Wünsche dir ruhige Träume",
            "Wünsche dir süsse Traeume",
            "Wünsche dir behagliche Traeume",
            "Wünsche dir eine sanfte Nachtruhe",
            "Wünsche dir einen ruhigen Schlaf"
        ],
        "Willkommen zu Hause": [
            [
                "Willkommen zu Hause",
                "Willkommen zurück",
                "Herzlich willkommen daheim",
                { False: "Schön, dass du wieder zu Hause bist", True: "Schön, dass ihr wieder zu Hause seid" },
                { False: "Schön das du wieder da bist", True: "Schön, dass ihr wieder da seid" },
                { False: "Schön das du zurück bist", True: "Schön, dass ihr wieder zurück seid" },
                { False: "Schön dich zu sehen", True: "Schön, euch zu sehen" }
            ],
            [
                "",
                "",
                "",
                "",
                "Ich hab mich schon gelangweilt",
                { False: "War ganzschön langweilig ohne dich", True: "War ganzschön langweilig ohne euch" },
                { False: "Ich hoffe du hattest einen angenehmen Tag", True: "Ich hoffe ihr hattet einen angenehmen Tag" }
            ]
        ]
    }

    @staticmethod
    def getRandomSynonym2(words, flag = None):
        if ShuffleHelper.history is None:
            history = Registry.getItemState("VoiceAnswerHistory").toString()
            try:
                ShuffleHelper.history = json.loads(history)
            except:
                ShuffleHelper.history = {}

        if words not in ShuffleHelper.history:
            ShuffleHelper.history[words] = []

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={}".format(customConfigs['gemini_token'])
        data = { "contents": [ {"parts" : [ { "text" : "{}".format( words ) } ] } ], "generation_config": { "temperature": 0.1, "candidate_count": 1 } }
        #data = { "contents": [ {"parts" : [ { "text" : "Sag mir {} mit anderen Worten ausser {}".format( words, ",".join(ShuffleHelper.history[words]) ) } ] } ] }

        result = HTTP.sendHttpPostRequest(url, "application/json", json.dumps(data), {}, 5000)
        answer = json.loads(result)
        text = answer['candidates'][0]['content']['parts'][0]['text'].strip()

        logging.info(str(answer))

        ShuffleHelper.history[words].append(text)
        if len(ShuffleHelper.history[words]) > 50:
            ShuffleHelper.history[words] = ShuffleHelper.history[words][-50:]
        choice = random.choice(ShuffleHelper.history[words])

        Registry.getItem("VoiceAnswerHistory").postUpdate(json.dumps(ShuffleHelper.history))

        #logging.info(text + " " + choice)

        return choice

    @staticmethod
    def getRandomSynonym(words, flag = None):
        #if words == "Gute Nacht":
        #    return ShuffleHelper.getRandomSynonym(words, flag)

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
                return "{}.".format( ". ".join(parts) )
            else:
                return "{}.".format( random.choice(ShuffleHelper._synonyms[words]) )
        return words

