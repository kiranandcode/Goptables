import re
from datetime import timedelta, time

duration_regex = re.compile(r'^(((?P<hours2>\d{1,2}):)?(?P<minutes2>\d{2})|((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?)$')
time_regex = re.compile(r'^(?P<hour>\d{1,2}):(?P<minute>\d{2})$')


def parse_duration(time_str):
    if time_str.strip() == "":
        return None
    parts = duration_regex.match(time_str)
    if not parts:
        return None
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            name = ''.join(c for c in name if c.isalpha())
            time_val = None
            try:
                time_val = int(param)
            except ValueError:
                return None
            time_params[name] = time_val

    return timedelta(**time_params)


def parse_time(time_str):
    parts = time_regex.match(time_str)
    if not parts:
        return None
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_val = None
            try:
                time_val = int(param)
            except ValueError:
                return None
            time_params[name] = time_val

    return time(**time_params)


def timedelta_to_str(dt):
    minutes = dt.seconds // 60
    hours = minutes // 60
    minutes = minutes - 60 * hours

    result = ""
    if hours > 0:
        result += "%02d:" % int(hours)
    result += "%02d" % int(minutes)

    return result


def time_to_str(t):
    return time.strftime(t, "%H:%M")
