"""A domain object with its own open() that acquires nothing."""


class Valve:
    def __init__(self):
        self.state = "shut"

    def open(self):
        self.state = "open"
        return self.state


def cycle(valve):
    valve.open()
    return valve.state
