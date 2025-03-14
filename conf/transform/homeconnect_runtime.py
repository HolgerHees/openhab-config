def calc(input):
    if input is None or input == "0":
        return "0 min."

    return "{} min.".format(round(int(input) / 60))
calc(input)
