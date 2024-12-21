import datetime
import random
import pandas as pd
from src.config import *
from src.models import *
from src.functions import *
from src.algoritms import *
import sys
sys.dont_write_bytecode = True



def main():
    nbuses = int(input("Кол-во автобусов: "))
    na = int(input("Кол-во водителей A: "))
    nb = int(input("Кол-во водителей B: "))
    print("Введите дату (год месяц день):")
    y, m, d = map(int, input().split())
    cdate = datetime.date(y, m, d)


    straight_schedule = create_straight_schedule(nbuses, na, nb, cdate)
    best_genetic = genetic_algorithm(nbuses, na, nb, cdate)

    export_straight_schedule(straight_schedule, "tables\straight.xlsx")
    export_genetic_schedule(best_genetic, "tables\genetic.xlsx")
    export_comparison_schedule(straight_schedule, best_genetic, "tables\comparison.xlsx")

    print("Готово. Файлы созданы.")

if __name__ == "__main__":
    main()
