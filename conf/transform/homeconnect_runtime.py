def calc(input):
    if input is None or not input.isnumeric():
        return "0 min."

    return "{} min.".format(round(int(input) / 60))
calc(input)
