def calc(input):
    if input is None or not input.isnumeric() or input == "-2147483648":
        return 0

    return int(input)
calc(input)
