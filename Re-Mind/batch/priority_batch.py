from datetime import date

from extensions import db
from models import Task


def calculate_priority(days):

    if days < 0:
        return 10

    if days <= 1:
        return 5

    if days <= 3:
        return 4

    if days <= 7:
        return 3

    if days <= 14:
        return 2

    return 1


def update_priority():

    today = date.today()

    tasks = Task.query.all()

    for task in tasks:
        remain = (task.end_date - today).days

        task.priority = calculate_priority(remain)

    db.session.commit()
