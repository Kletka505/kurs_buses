import datetime
from .config import *

class Driver:
    def __init__(self, driver_type, id):
        self.type = driver_type
        self.id = id
        self.schedule = [] 
        self.total_work_time = datetime.timedelta()
        self.last_break = datetime.datetime.combine(datetime.date.min, SHIFT_START_TIME)

    def __repr__(self):
        return f"Driver(id={self.id}, type={self.type}, schedule={len(self.schedule)})"


class Route:
    def __init__(self, start_time, route_time, driver_id):
        self.start_time = start_time
        self.end_time = start_time + datetime.timedelta(minutes=route_time)
        self.driver_id = driver_id

    def __repr__(self):
        return (f"Route(start={self.start_time.strftime('%H:%M')}, "
                f"end={self.end_time.strftime('%H:%M')}, driver={self.driver_id})")


class Schedule:
    def __init__(self):
        self.routes = []
        self.drivers = []

    def add_route(self, route):
        self.routes.append(route)

    def add_driver(self, driver):
        self.drivers.append(driver)

    def calculate_metrics(self):

        peak_routes = 0
        for route in self.routes:
            t = route.start_time.time()
            if ((t >= PEAK_HOURS_START_1 and t < PEAK_HOURS_END_1)
                    or (t >= PEAK_HOURS_START_2 and t < PEAK_HOURS_END_2)):
                peak_routes += 1
        total_routes   = len(self.routes)
        unique_drivers = len(self.drivers)
        return (total_routes, peak_routes, unique_drivers)