# -*- coding: utf-8 -*-

import random

class ShuffleHelper:
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
                u"Schön, dass du wieder zu Hause bist",
                u"Schön das du wieder da bist",
                u"Schön das du zurück bist",
                u"Schön dich zu sehen"
            ],
            [
                u"",
                u"",
                u"",
                u"",
                u"Ich hab mich schon gelangweilt",
                u"War ganzschön langweilig ohne dich",
                u"Ich hoffe du hattest einen angenehmen Tag"
            ]
        ]
    }

    @staticmethod
    def getRandomSynonym(input):
        if input in ShuffleHelper._synonyms:
            values = ShuffleHelper._synonyms[input]
            if type(values[0]) is list:
                parts = []
                for _values in values:
                    parts.append(random.choice(_values))
                return ". ".join(parts)
            else:
                return random.choice(ShuffleHelper._synonyms[input])
        return input

