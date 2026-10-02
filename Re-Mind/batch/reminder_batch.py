from datetime import date

from models import Task

REMIND_DAYS = [7, 3, 1, 0]


def execute():

    today = date.today()

    tasks = Task.query.all()

    for task in tasks:
        remain = (task.end_date - today).days

        if remain in REMIND_DAYS:
            print(f"通知: {task.title}")

            # メール送信
            # Teams送信
            # DB履歴保存
