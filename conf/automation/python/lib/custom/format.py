import locale

class FormatHelper:
    @staticmethod
    def format(number, ndigits):
        return "{}".format(round(number, ndigits)).replace(".", "|").replace(",", ".").replace("|", ",")
