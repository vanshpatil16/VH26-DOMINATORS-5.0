"""The word close is a dictionary key and a column name here."""

CANDLE = {"open": 101.5, "high": 104.0, "low": 100.2, "close": 103.7}


def spread(bar=CANDLE):
    return bar["high"] - bar["low"]


def summarise(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read(), CANDLE["close"]
