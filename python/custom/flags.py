class FlagHelper:
    OFF = 0

    AUTO_ROLLERSHUTTER_TIME_DEPENDENT = 1
    AUTO_ROLLERSHUTTER_SHADING = 2

    NOTIFY_PUSH = 1
    NOTIFY_ALEXA = 2

    @staticmethod
    def hasFlag(flag, flags):
        if flag == 0:
            return flag == flags
        return flag & flags == flag
