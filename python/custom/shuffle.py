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
    def getRandomSynonym(input, flag = None):
        if input in ShuffleHelper._synonyms:
            values = ShuffleHelper._synonyms[input]
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
                return u"{}.".format( random.choice(ShuffleHelper._synonyms[input]) )
        return input

