"""Review sets and CAT time helpers shared by all question runners."""
from datetime import datetime
from zoneinfo import ZoneInfo

CAT = ZoneInfo("Africa/Kigali")

# set: (review account, destination, September date)
SETS = {
    "A": (998,    24755,  6),
    "B": (147228, 186823, 13),
    "C": (206978, 6573,   8),
    "D": (237998, 21755,  6),
    "E": (144228, 183823, 13),
    "F": (203978, 3573,   8),
}


def hour_window(day, hour=9, minute=45):
    """Epoch seconds for [day hh:mm CAT, +1 hour) in September 2026."""
    start = int(datetime(2026, 9, day, hour, minute, tzinfo=CAT).timestamp())
    return start, start + 3600


def cat_text(epoch):
    return datetime.fromtimestamp(epoch, CAT).strftime("%Y-%m-%d %H:%M:%S")
