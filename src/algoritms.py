import datetime
import random
import pandas as pd
from .config import *
from .models import *
from .functions import *

# === Прямой алгоритм ===
def create_straight_schedule(num_buses, num_drivers_a, num_drivers_b, current_date):
    schedule = Schedule()

    # Создаём водителей
    drivers_a = [Driver('A', f'A{i+1}') for i in range(num_drivers_a)]
    drivers_b = [Driver('B', f'B{i+1}') for i in range(num_drivers_b)]

    available_drivers_a = list(drivers_a)
    available_drivers_b = list(drivers_b)

    # Время
    current_time = datetime.datetime.combine(current_date, SHIFT_START_TIME)
    end_of_service = get_end_of_service(current_date)

    while current_time < end_of_service:
        # Выбираем случайную длину маршрута
        route_time = random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES)

        # Сколько автобусов на данном шаге
        if is_peak_hour(current_time.time()) and not is_weekend(current_date):
            needed_buses = int(num_buses * PEAK_PASSENGER_PERCENT)
        else:
            passenger_percent = (1 - PEAK_PASSENGER_PERCENT) if not is_weekend(current_date) else 1
            needed_buses = int(num_buses * passenger_percent)

        temp_times = []

        for _ in range(needed_buses):
            temp_time = current_time

            # Пытаемся взять водителя A
            if available_drivers_a:
                driver = available_drivers_a[0]

                if is_weekend(current_date):
                    available_drivers_a.pop(0)
                    pass
                else:
                    if not (SHIFT_START_TIME <= temp_time.time() <= datetime.time(10,0)):
                        available_drivers_a.pop(0)
                        pass
                    else:
                        temp_time = shift_to_end_of_last_event(driver, temp_time)

                        # Проверяем обед
                        if (driver.total_work_time >= datetime.timedelta(hours=DRIVER_A_OBED_HOURS)
                                and not any(x[2] == 'lunch' for x in driver.schedule)):
                            temp_time = shift_to_end_of_last_event(driver, temp_time)
                            lunch_start = temp_time
                            lunch_end   = lunch_start + datetime.timedelta(minutes=DRIVER_A_LUNCH_MINUTES)
                            if lunch_end > end_of_service:
                                available_drivers_a.pop(0)
                                continue
                            driver.schedule.append((lunch_start, lunch_end, 'lunch'))
                            driver.last_break = lunch_end
                            temp_time = lunch_end

                        # Снова выровняем temp_time
                        temp_time = shift_to_end_of_last_event(driver, temp_time)

                        # Проверяем лимиты
                        if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS):
                            end_of_this_route = temp_time + datetime.timedelta(minutes=route_time)
                            if end_of_this_route > end_of_service:
                                available_drivers_a.pop(0)
                                continue

                            # Создаём маршрут
                            r = Route(temp_time, route_time, driver.id)
                            schedule.add_route(r)
                            driver.schedule.append((r.start_time, r.end_time, 'route'))
                            driver.total_work_time += datetime.timedelta(minutes=route_time)

                            # Сдвигаем temp_time
                            temp_time = r.end_time + datetime.timedelta(minutes=random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))
                        else:
                            available_drivers_a.pop(0)
                            continue

                        temp_times.append(temp_time)
                        continue  

            # Если не вышло с A (или is_weekend, или условие времени), пробуем B
            if available_drivers_b:
                driver = available_drivers_b[0]
                temp_time = shift_to_end_of_last_event(driver, temp_time)

                # Перерыв B
                if (driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY)
                        and driver.last_break <= temp_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY)):
                    break_start = temp_time
                    break_end   = break_start + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                    if break_end > end_of_service:
                        available_drivers_b.pop(0)
                        continue
                    driver.schedule.append((break_start, break_end, 'break'))
                    driver.last_break = break_end
                    temp_time = break_end

                temp_time = shift_to_end_of_last_event(driver, temp_time)

                # Проверяем 12 часов B
                if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_B_WORK_HOURS):
                    end_of_this_route = temp_time + datetime.timedelta(minutes=route_time)
                    if end_of_this_route > end_of_service:
                        available_drivers_b.pop(0)
                        continue

                    r = Route(temp_time, route_time, driver.id)
                    schedule.add_route(r)
                    driver.schedule.append((r.start_time, r.end_time, 'route'))
                    driver.total_work_time += datetime.timedelta(minutes=route_time)

                    temp_time = r.end_time + datetime.timedelta(minutes=random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))
                else:
                    available_drivers_b.pop(0)
                    continue

                temp_times.append(temp_time)
            else:
                break

        if needed_buses > 0 and not temp_times:
            break

        if temp_times:
            current_time = max(temp_times)
        else:
            break

    # Собираем всех водителей
    schedule.drivers.extend(drivers_a)
    schedule.drivers.extend(drivers_b)

    # Удаляем дубли, пересчитываем work_time, удаляем пустых
    deduplicate_and_recalc(schedule)

    return schedule


# === Генератор (случайный) для генетики (с теми же ограничениями A) ===
def generate_random_schedule(num_buses, num_drivers_a, num_drivers_b, current_date):
    schedule = Schedule()

    drivers_a = [Driver('A', f'A{i+1}') for i in range(num_drivers_a)]
    drivers_b = [Driver('B', f'B{i+1}') for i in range(num_drivers_b)]
    available_drivers_a = list(drivers_a)
    available_drivers_b = list(drivers_b)

    current_time = datetime.datetime.combine(current_date, SHIFT_START_TIME)
    end_of_service = get_end_of_service(current_date)

    while current_time < end_of_service:
        route_time = random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES)

        if is_peak_hour(current_time.time()) and not is_weekend(current_date):
            needed_buses = int(num_buses * PEAK_PASSENGER_PERCENT)
        else:
            passenger_percent = (1 - PEAK_PASSENGER_PERCENT) if not is_weekend(current_date) else 1
            needed_buses = int(num_buses * passenger_percent)

        temp_times = []
        for _ in range(needed_buses):
            temp_time = current_time

            # Выбираем случайно "A" или "B"
            pool = []
            if available_drivers_a:
                pool.append("A")
            if available_drivers_b:
                pool.append("B")
            if not pool:
                break

            chosen_type = random.choice(pool)
            if chosen_type == "A":
                driver = available_drivers_a[0]

                # Но если сегодня выходной - skip A
                if is_weekend(current_date):
                    available_drivers_a.pop(0)
                else:
                    # Проверим, что время <= 10:00
                    if not (SHIFT_START_TIME <= temp_time.time() <= datetime.time(10, 0)):
                        available_drivers_a.pop(0)
                    else:
                        temp_time = shift_to_end_of_last_event(driver, temp_time)

                        # Обед
                        if (driver.total_work_time >= datetime.timedelta(hours=DRIVER_A_OBED_HOURS)
                                and not any(x[2] == 'lunch' for x in driver.schedule)):
                            lunch_start = temp_time
                            lunch_end   = lunch_start + datetime.timedelta(minutes=DRIVER_A_LUNCH_MINUTES)
                            if lunch_end > end_of_service:
                                available_drivers_a.pop(0)
                                continue
                            driver.schedule.append((lunch_start, lunch_end, 'lunch'))
                            driver.last_break = lunch_end
                            temp_time = lunch_end

                        temp_time = shift_to_end_of_last_event(driver, temp_time)

                        # 8ч лимит
                        if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_A_WORK_HOURS):
                            end_of_this_route = temp_time + datetime.timedelta(minutes=route_time)
                            if end_of_this_route > end_of_service:
                                available_drivers_a.pop(0)
                                continue

                            r = Route(temp_time, route_time, driver.id)
                            schedule.add_route(r)
                            driver.schedule.append((r.start_time, r.end_time, 'route'))
                            driver.total_work_time += datetime.timedelta(minutes=route_time)

                            temp_time = r.end_time + datetime.timedelta(minutes=random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))

                            temp_times.append(temp_time)
                            continue
                        else:
                            available_drivers_a.pop(0)
                            continue

            # Если не сработал A (или он закончился), пробуем B
            if available_drivers_b:
                driver = available_drivers_b[0]
                temp_time = shift_to_end_of_last_event(driver, temp_time)

                # Перерыв B
                if (driver.total_work_time >= datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY)
                        and driver.last_break <= temp_time - datetime.timedelta(minutes=DRIVER_B_BREAK_FREQUENCY)):
                    break_start = temp_time
                    break_end   = break_start + datetime.timedelta(minutes=DRIVER_B_LONG_BREAK_MINUTES)
                    if break_end > end_of_service:
                        available_drivers_b.pop(0)
                        continue
                    driver.schedule.append((break_start, break_end, 'break'))
                    driver.last_break = break_end
                    temp_time = break_end

                temp_time = shift_to_end_of_last_event(driver, temp_time)

                # 12ч лимит
                if driver.total_work_time + datetime.timedelta(minutes=route_time) <= datetime.timedelta(hours=DRIVER_B_WORK_HOURS):
                    end_of_this_route = temp_time + datetime.timedelta(minutes=route_time)
                    if end_of_this_route > end_of_service:
                        available_drivers_b.pop(0)
                        continue

                    r = Route(temp_time, route_time, driver.id)
                    schedule.add_route(r)
                    driver.schedule.append((r.start_time, r.end_time, 'route'))
                    driver.total_work_time += datetime.timedelta(minutes=route_time)

                    temp_time = r.end_time + datetime.timedelta(minutes=random.randint(SHIFT_CHANGE_TIME_MIN, SHIFT_CHANGE_TIME_MAX))

                    temp_times.append(temp_time)
                else:
                    available_drivers_b.pop(0)
                    continue

        if needed_buses > 0 and not temp_times:
            break

        if temp_times:
            current_time = max(temp_times)
        else:
            break

    # Добавляем всех водителей
    schedule.drivers.extend(drivers_a)
    schedule.drivers.extend(drivers_b)

    # Убираем дубли и пр.
    deduplicate_and_recalc(schedule)

    return schedule


# === Генетический алгоритм ===
def fitness(schedule):
    total_routes, peak_routes, unique_drivers = schedule.calculate_metrics()
    return total_routes - unique_drivers * 0.1

def crossover(schedule1, schedule2):
    child = Schedule()
    sp = random.randint(0, min(len(schedule1.routes), len(schedule2.routes)))
    child.routes = schedule1.routes[:sp] + schedule2.routes[sp:]
    sp_d = random.randint(0, min(len(schedule1.drivers), len(schedule2.drivers)))
    child.drivers = schedule1.drivers[:sp_d] + schedule2.drivers[sp_d:]
    return child

def mutate(schedule):
    if random.random() < MUTATION_RATE:
        # Сдвигаем время одного маршрута
        if schedule.routes:
            idx = random.randint(0, len(schedule.routes)-1)
            old_route = schedule.routes[idx]
            new_start = old_route.start_time + datetime.timedelta(minutes=random.randint(-30, 30))
            if new_start.time() >= SHIFT_START_TIME and new_start.time() <= datetime.time(23,59):
                new_rt = random.randint(ROUTE_TIME_MIN_MINUTES, ROUTE_TIME_MAX_MINUTES)
                schedule.routes[idx] = Route(new_start, new_rt, old_route.driver_id)

        if schedule.drivers:
            idx = random.randint(0, len(schedule.drivers)-1)
            schedule.drivers[idx].type = random.choice(["A","B"])

    return schedule

def genetic_algorithm(num_buses, num_drivers_a, num_drivers_b, current_date):
    population = [generate_random_schedule(num_buses, num_drivers_a, num_drivers_b, current_date)
                  for _ in range(POPULATION_SIZE)]
    for _ in range(GENERATIONS):
        population.sort(key=fitness, reverse=True)
        parents = population[:POPULATION_SIZE // 2]

        offspring = []
        for i in range(0, len(parents), 2):
            if i+1 < len(parents):
                ch1 = crossover(parents[i], parents[i+1])
                ch2 = crossover(parents[i+1], parents[i])
                offspring.append(mutate(ch1))
                offspring.append(mutate(ch2))
            else:
                offspring.append(mutate(parents[i]))

        population = parents + offspring
        population.sort(key=fitness, reverse=True)
        population = population[:POPULATION_SIZE]

    best = population[0]
    deduplicate_and_recalc(best)
    return best


def export_straight_schedule(straight_schedule, filename="straight.xlsx"):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for driver in straight_schedule.drivers:
            rows = []
            total_work = 0
            total_break = 0
            for (start, end, act_type) in driver.schedule:
                duration = int((end - start).total_seconds() // 60)
                if act_type == 'route':
                    row_type = "Маршрут"
                    total_work += duration
                elif act_type == 'break':
                    row_type = "Перерыв(B)"
                    total_break += duration
                elif act_type == 'lunch':
                    row_type = "Обед(A)"
                    total_break += duration
                else:
                    row_type = act_type

                rows.append({
                    "Type": row_type,
                    "Start Time": start.strftime('%Y-%m-%d %H:%M'),
                    "End Time":   end.strftime('%Y-%m-%d %H:%M'),
                    "Duration (min)": duration
                })

            df = pd.DataFrame(rows, columns=["Type", "Start Time", "End Time", "Duration (min)"])

            summary_row = {
                "Type": "ИТОГО",
                "Start Time": "",
                "End Time": "",
                "Duration (min)": f"Работа={total_work}, Перерыв={total_break}"
            }
            df.loc[len(df)] = summary_row

            df.to_excel(writer, sheet_name=driver.id, index=False)


def export_genetic_schedule(genetic_schedule, filename="genetic.xlsx"):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        for driver in genetic_schedule.drivers:
            rows = []
            total_work = 0
            total_break = 0
            for (start, end, act_type) in driver.schedule:
                duration = int((end - start).total_seconds() // 60)
                if act_type == 'route':
                    row_type = "Маршрут"
                    total_work += duration
                elif act_type == 'break':
                    row_type = "Перерыв(B)"
                    total_break += duration
                elif act_type == 'lunch':
                    row_type = "Обед(A)"
                    total_break += duration
                else:
                    row_type = act_type

                rows.append({
                    "Type": row_type,
                    "Start Time": start.strftime('%Y-%m-%d %H:%M'),
                    "End Time":   end.strftime('%Y-%m-%d %H:%M'),
                    "Duration (min)": duration
                })

            df = pd.DataFrame(rows, columns=["Type", "Start Time", "End Time", "Duration (min)"])

            summary_row = {
                "Type": "ИТОГО",
                "Start Time": "",
                "End Time": "",
                "Duration (min)": f"Работа={total_work}, Перерыв={total_break}"
            }
            df.loc[len(df)] = summary_row

            df.to_excel(writer, sheet_name=driver.id, index=False)


def export_comparison_schedule(straight_schedule, genetic_schedule, filename="comparison.xlsx"):
    st_total, st_peak, st_unique = straight_schedule.calculate_metrics()
    gn_total, gn_peak, gn_unique = genetic_schedule.calculate_metrics()

    data = [
        {
            "Algorithm": "Straight",
            "Total Routes": st_total,
            "Peak Routes": st_peak,
            "Unique Drivers": st_unique
        },
        {
            "Algorithm": "Genetic",
            "Total Routes": gn_total,
            "Peak Routes": gn_peak,
            "Unique Drivers": gn_unique
        }
    ]
    df = pd.DataFrame(data, columns=["Algorithm", "Total Routes", "Peak Routes", "Unique Drivers"])

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Comparison", index=False)