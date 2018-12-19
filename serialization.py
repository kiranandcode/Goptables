from datetime import datetime

from timeparser import parse_duration, parse_time


def validate_json(loaded):
    if not loaded:
        return None
    if 'tasks' not in loaded or not isinstance(loaded['tasks'], list):
        return None
    if 'breaks' not in loaded or not isinstance(loaded['breaks'], list):
        return None
    if 'work_interval' not in loaded or not isinstance(loaded['work_interval'], str):
        return None
    if 'start_time' not in loaded or not isinstance(loaded['start_time'], str):
        return None
    if 'start_date' not in loaded or not isinstance(loaded['start_date'], str):
        return None
    if 'days' not in loaded or not isinstance(loaded['days'], int):
        return None
    if 'table' not in loaded or not isinstance(loaded['table'], list):
        return None
    result = {'tasks': []}
    for (name, score) in loaded['tasks']:
        result['tasks'].append((name, score))

    result['breaks'] = []
    for br in loaded['breaks']:
        br_dur = parse_duration(br)

        if br_dur is None:
            return None
        else:
            result['breaks'].append(br_dur)

    wk_dur = parse_duration(loaded['work_interval'])
    if not wk_dur:
        return None
    else:
        result['work_interval'] = wk_dur

    st_tm = parse_time(loaded['start_time'])
    if not st_tm:
        return None
    else:
        result['start_time'] = st_tm

    try:
        result['start_date'] = datetime.strptime(loaded['start_date'], "%d-%m-%Y")
    except ValueError:
        return None

    result['days'] = loaded['days']
    result['table'] = loaded['table']

    return result