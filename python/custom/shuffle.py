import random

class ShuffleHelper:
    _synonyms = {
        "Gute Nacht": [
            "Gute Nacht",
            "Schlaf gut",
            "Schlaf schoen",
            "Traum was schoenes",
            "Traum was suesses",
            "Schoene Traeume",
            "Suesse Traeume",
            "Schlummer gut",
            "Angenehme Nachtruhe",
            "Wuensche dir behagliche Traeume",
            "Wuensche dir eine sanfte Nachtruhe",
            "Wuensche dir einen ruhigen Schlaf"
        ],
        "Willkommen zu Hause": [
            [
                "Willkommen zu Hause",
                "Willkommen zurueck",
                "Herzlich willkommen daheim",
                "Schoen, dass du wieder zu Hause bist",
                "Schoen das du wieder da bist",
                "Schoen das du zurueck bist",
                "Schoen dich zu sehen"
            ],
            [
                "",
                "",
                "",
                "",
                "Ich hab mich schon gelangweilt",
                "War ganzschoen langweilig ohne dich",
                "Ich hoffe du hattest einen angenehmen Tag"
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
