def calc(input):
    if input is None or not input.isnumeric() or input == "-2147483648":
        return 0.0

    return float(input) / 100.0
calc(input)
