import datetime
from .config import *

def is_peak_hour(time: datetime.time) -> bool:
    return ((PEAK_HOURS_START_1 <= time < PEAK_HOURS_END_1) or
            (PEAK_HOURS_START_2 <= time < PEAK_HOURS_END_2))

def is_weekend(date: datetime.date) -> bool:
    return date.strftime('%A') in WEEKEND

def get_end_of_service(current_date: datetime.date) -> datetime.datetime:
    """
    Возвращает datetime, после которого автобусы НЕ ходят.
    Если SHIFT_END_TIME < SHIFT_START_TIME, значит конец - это +1 день.
    У нас SHIFT_END_TIME = 3:00, SHIFT_START_TIME=6:00 => +1 день.
    """
    base_end = datetime.datetime.combine(current_date, SHIFT_END_TIME)
    if SHIFT_END_TIME < SHIFT_START_TIME:
        base_end += datetime.timedelta(days=1)
    return base_end

def shift_to_end_of_last_event(driver, start_time):
    if driver.schedule:
        last_event_end = driver.schedule[-1][1]
        if start_time < last_event_end:
            return last_event_end
    return start_time


def deduplicate_and_recalc(schedule):

    for drv in schedule.drivers:
        unique_events = []
        seen = set()
        for (st, en, ttype) in drv.schedule:
            key = (st, en, ttype)
            if key not in seen:
                seen.add(key)
                unique_events.append((st, en, ttype))
        drv.schedule = unique_events
        total_work = datetime.timedelta()
        for (st, en, ttype) in drv.schedule:
            if ttype == 'route':
                total_work += (en - st)
        drv.total_work_time = total_work

    schedule.drivers = [x for x in schedule.drivers if len(x.schedule) > 0]