#!/usr/bin/env python3
"""
A module for converting between the settlement periods used by GB electricity industry, Unix
timestamps and Python datetime objects.

- Jamie Taylor <jamie.taylor@sheffield.ac.uk>
- First Authored: 2020-03-31

"""

from typing import Optional, Tuple
from datetime import datetime, date, time, timedelta
import argparse
import pytz
import numpy as np

TRANSITION_DATES_TS = [
    (954028800, 972777600), (985478400, 1004227200), (1017532800, 1035676800),
    (1048982400, 1067126400), (1080432000, 1099180800), (1111881600, 1130630400),
    (1143331200, 1162080000), (1174780800, 1193529600), (1206835200, 1224979200),
    (1238284800, 1256428800), (1269734400, 1288483200), (1301184000, 1319932800),
    (1332633600, 1351382400), (1364688000, 1382832000), (1396137600, 1414281600),
    (1427587200, 1445731200), (1459036800, 1477785600), (1490486400, 1509235200),
    (1521936000, 1540684800), (1553990400, 1572134400), (1585440000, 1603584000),
    (1616889600, 1635638400), (1648339200, 1667088000), (1679788800, 1698537600),
    (1711843200, 1729987200), (1743292800, 1761436800), (1774742400, 1792886400),
    (1806192000, 1824940800), (1837641600, 1856390400), (1869091200, 1887840000)
]

def to_unixtime(datetime_: datetime, timezone_: Optional[str] = None) -> int:
    """
    Convert a python datetime object, *datetime_*, into unixtime int

    Parameters
    ----------
    `datetime_` : datetime.datetime
        Datetime to be converted
    `timezone_` : string
        The timezone of the input date from Olson timezone database. If *datetime_* is timezone
        aware then this can be ignored.
    Returns
    -------
    int
        Unixtime i.e. seconds since epoch
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    See Also
    --------
    `Python module pytz docs <http://pythonhosted.org/pytz/>`_
    """
    _validate_datetime("datetime_", datetime_)
    _validate_timezone("timezone_", timezone_)
    if not timezone_ and not datetime_.tzinfo:
        raise Exception("EITHER datetime_ must contain tzinfo OR timezone_ must be passed.")
    if timezone_ and not datetime_.tzinfo:
        utc_datetime = pytz.timezone(timezone_).localize(datetime_).astimezone(pytz.utc)
    else:
        utc_datetime = datetime_.astimezone(pytz.utc)
    unixtime = int((utc_datetime - datetime(1970, 1, 1, 0, 0, 0, 0, pytz.utc)).total_seconds())
    return unixtime

def from_unixtime(timestamp_: int, timezone_: str = "UTC") -> datetime:
    """
    Convert a unixtime int, *timestamp_*, into python datetime object

    Parameters
    ----------
    `timestamp_` : int
        Unixtime i.e. seconds since epoch
    `timezone_` : string
        The timezone of the output date from Olson timezone database. Defaults to utc.
    Returns
    -------
    datetime.datetime
        Python datetime object (timezone aware)
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    pytz http://pythonhosted.org/pytz/\n
    """
    _validate_timestamp("timestamp_", timestamp_)
    _validate_timezone("timezone_", timezone_)
    return datetime.fromtimestamp(timestamp_, tz=pytz.timezone(timezone_))

def sp2ts(date_: date, sp_: int, closed: str = "right") -> int:
    """
    Convert a date and settlement period into a unix timestamp for the start or end of the
    settlement period.

    Parameters
    ----------
    `date_` : datetime.date
        Python date object.
    `sp_` : int
        Integer in the range [1..50].
    `closed` : str
        Set to 'right' to return the timestamp at the end of the settlement period, 'middle' to
        return the timestamp at the centre of the settlement period, or 'left' to return the
        timestamp at the start of the settlement period.
    Returns
    -------
    int
        Unix timestamp.
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    """
    _validate_date("date_", date_)
    _validate_sp("sp_", sp_, date_)
    _validate_closed("closed", closed)
    min_date = from_unixtime(TRANSITION_DATES_TS[0][0]).date()
    max_date = from_unixtime(TRANSITION_DATES_TS[-1][1]).date()
    if date_ < min_date or date_ > max_date:
        raise ValueError(f"`date_` is outside supported range: {date_.isoformat()} (supported "
                         f"range is {min_date.isoformat()} <= date_ <= {max_date.isoformat()}")
    date_ts = to_unixtime(datetime.combine(date_, time()), "UTC")
    ts_raw = date_ts + 30 * 60 * int(sp_)
    if any(x[0] < date_ts <= x[1] for x in TRANSITION_DATES_TS):
        timestamp_ = ts_raw - 3600
    else:
        timestamp_ = ts_raw
    if closed.lower() == "left":
        timestamp_ -= 1800
    elif closed.lower() == "middle":
        timestamp_ -= 900
    return timestamp_

def sp2dt(date_: date, sp_: int, closed: str = "right") -> datetime:
    """
    Convert a date and settlement period into a timezone-aware Python datetime object for the
    start or end of the settlement period.

    Parameters
    ----------
    `date_` : datetime.date
        Python date object.
    `sp_` : int
        Integer in the range [1..50].
    `closed` : str
        Set to 'right' to return the timestamp at the end of the settlement period, 'middle' to
        return the timestamp at the centre of the settlement period, or 'left' to return the
        timestamp at the start of the settlement period.
    Returns
    -------
    datetime.datetime
        Timezone-aware Python datetime object in UTC.
    """
    return from_unixtime(sp2ts(date_, sp_, closed))

def ts2sp(timestamp_: int) -> Tuple[date, int]:
    """
    Convert a unix timestamp into a date and settlement period. Settlent periods are considered to
    be "closed right" i.e. SP 1 refers to the interval 00:00:00 < t <= 00:30:00.

    Parameters
    ----------
    `timestamp_` : int
        Unix timestamp.
    Returns
    -------
    tuple
        A tuple containing (date, sp) where date is a Python date object and sp is an int.
    Notes
    -----
    This logic is horrible! Hopefully it can be refined and made more performant in a future
    release.
    """
    _validate_timestamp("timestamp_", timestamp_)
    if timestamp_ < TRANSITION_DATES_TS[0][0] or timestamp_ > TRANSITION_DATES_TS[-1][1]:
        raise ValueError(f"`timestamp_` is outside supported range: {timestamp_} (supported range "
                         f"is {TRANSITION_DATES_TS[0][0]} <= timestamp_ <= "
                         f"{TRANSITION_DATES_TS[-1][1]}")
    if timestamp_ % 1800 != 0:
        raise ValueError(f"`timestamp_` does not fall on settlement period boundary: {timestamp_}")
    # if timestamp_ == 1635724800:
        # import pdb; pdb.set_trace()
    d_ts = (timestamp_ // 86400) * 86400
    date_ = from_unixtime(timestamp_).date()
    hours = (timestamp_ % 86400) / 3600.
    sp_ = int(hours / 0.5)
    if any(x[0] < d_ts <= x[1] for x in TRANSITION_DATES_TS):
        # Add an hour for BST
        sp_ += 2
    if sp_ == 0:
        # If it's 00:00:00+00:00, sp_ will be 0 - need to subtract a day from date_ and
        # set SP to max_sp for day-1
        date_ -= timedelta(days=1)
        sp_ = _max_sp(date_)
    # If our SP exceeds the max SP for the date, add 1 day and reset SP to 1 or 2
    max_sp = _max_sp(date_)
    if sp_ > max_sp:
        date_ += timedelta(days=1)
        sp_ -= max_sp
    return (date_, sp_)

def dt2sp(datetime_: datetime, timezone_: Optional[str] = None) -> Tuple[date, int]:
    """
    Convert a Python datetime object into a date and settlement period. Settlent periods are
    considered to be "closed right" i.e. SP 1 refers to the interval 00:00:00 < t <= 00:30:00.

    Parameters
    ----------
    `datetime_` : datetime.datetime
        Python datetime object. If `datetime_` is timezone-aware, the tzinfo will be used, otherwise
        you must also specify `timezone_` parameter.
    `timezone_` : str
        Specify the timezone of `datetime_` as an Olsen timezone string. `datetime_` must be
        timezone-naive, otherwise this parameter will be ignored.
    Returns
    -------
    tuple
        A tuple containing (date, sp) where d is a Python date object and sp is an int.
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    """
    if not timezone_ and not datetime_.tzinfo:
        raise Exception("EITHER datetime_ must contain tzinfo OR timezone_ must be passed.")
    return ts2sp(to_unixtime(datetime_, timezone_))

def _validate_datetime(name, datetime_, require_tzinfo=False):
    if not isinstance(datetime_, datetime):
        raise TypeError(f"`{name}` must be of type datetime.datetime")
    if require_tzinfo:
        if not datetime_.tzinfo:
            raise ValueError(f"`{name}` is missing tzinfo")

def _validate_date(name, date_):
    if not isinstance(date_, date):
        raise TypeError(f"`{name}` must be of type datetime.date")

def _validate_timezone(name, timezone_):
    if timezone_ is not None and not isinstance(timezone_, str):
        raise TypeError(f"`{name}` must be of type string")
    # try:
        # tzinfo = pytz.timezone(timezone_)
    # except pytz.exceptions.UnknownTimeZoneError:
        # raise ValueError(f"Unknown timezone '{timezone_}'")

def _validate_timestamp(name, timestamp_):
    if not isinstance(timestamp_, (int, np.int32, np.int64)):
        raise TypeError(f"`{name}` must be of type int")
    if timestamp_ < 0:
        raise ValueError("Inavalid value for `{name}`, Unix timestamps cannot be negative")

def _validate_closed(name, closed):
    if not isinstance(closed, str):
        raise TypeError(f"`{name}` must be of type string")
    if closed.lower() not in ("right", "left", "middle"):
        raise ValueError("The `closed` parameter should be either 'right', 'left' or 'middle'")

def _max_sp(date_):
    date_ts = to_unixtime(datetime.combine(date_, time()), "UTC")
    if date_ts in [x[0] for x in TRANSITION_DATES_TS]:
        max_sp = 46
    elif date_ts in [x[1] for x in TRANSITION_DATES_TS]:
        max_sp = 50
    else:
        max_sp = 48
    return max_sp

def _validate_sp(name, sp_, date_):
    if not isinstance(sp_, int):
        raise TypeError(f"`{name}` must be of type string")
    max_sp = _max_sp(date_)
    if not 1 <= sp_ <= max_sp:
        raise ValueError(f"`{name}` must be in the interval 1 <= {name} <= {max_sp} on date "
                         f"{date_.isoformat()}, got {sp_}")

def parse_options():
    """Parse command line options."""
    parser = argparse.ArgumentParser(description=("This is a command line interface (CLI) for "
                                                  "the sp2ts module."),
                                     epilog="Jamie Taylor, 2020-03-31")
    parser.add_argument("-d", "--date", dest="date_", action="store", required=False, type=str,
                        metavar="<yyyy-mm-dd>", help="Specify a date (use only in conjuction with "
                                                     "-sp/--settlement-period).")
    parser.add_argument("-sp", "--settlement-period", dest="sp_", action="store", required=False,
                        type=int, metavar="<[1..50]>", help="Specify a settlement period (use only "
                                                            "in conjuction with -d/--date).")
    parser.add_argument("-ts", "--timestamp", dest="timestamp_", action="store", required=False,
                        type=int, metavar="<seconds since epoch>",
                        help="Specify a timestamp (all other options will be ignored).")
    parser.add_argument("-dt", "--datetime", dest="dt", action="store", required=False, type=str,
                        metavar="<yyyy-mm-ddTHH:MM:SS>", help="Specify a datetime (optionally also "
                                                              "specify -tz/--timezone).")
    parser.add_argument("-tz", "--timezone", dest="tz", action="store", required=False,
                        type=str, metavar="<Olson timezone string>", default="UTC",
                        help="Specify a timezone (used only in conjunction with -dt/--datetime, "
                             "default is 'UTC').")
    options = parser.parse_args()
    if options.date_:
        try:
            options.date_ = datetime.strptime(options.date_, "%Y-%m-%d").date()
        except Exception as err:
            raise Exception("Failed to parse date, make sure you use <yyyy-mm-dd> format.") from err
    if options.dt:
        try:
            options.dt = options.dt.replace(" ", "T")
            options.dt = datetime.strptime(options.dt, "%Y-%m-%dT%H:%M:%S")
        except Exception as err:
            raise Exception("Failed to parse dt, make sure you use <yyyy-mm-ddTHH:MM:SS> format.") \
                  from err
    if options.tz:
        if options.tz not in pytz.all_timezones:
            supported_timezones = ", ".join([f"'{tz}'" for tz in pytz.all_timezones])
            print(f"The specified timezone (-tz/--timezone) '{options.tz}' was not recognised. "
                  f"Here's a full list of supported time zones: \n{supported_timezones}")
    return options

def main():
    """Run the Command Line Interface."""
    options = parse_options()
    if options.timestamp_ is not None:
        ts_str = from_unixtime(options.timestamp_)
        date_, sp_ = ts2sp(options.timestamp_)
        print(f"{options.timestamp_} ({ts_str})  ->  {date_} SP{sp_}")
    elif options.date_ is not None and options.sp_ is not None:
        timestamp_ = sp2ts(options.date_, options.sp_)
        ts_str = from_unixtime(timestamp_)
        print(f"{options.date_} SP{options.sp_}  ->  {timestamp_} ({ts_str})")
    elif options.dt is not None:
        date_, sp_ = dt2sp(options.dt, options.tz)
        print(f"{options.dt} ({options.tz})  ->  {date_} SP{sp_}")

if __name__ == "__main__":
    main()
