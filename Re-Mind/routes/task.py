from datetime import datetime

from flask import Blueprint, redirect, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import Task

task_bp = Blueprint("task", __name__)


@task_bp.route("/tasks")
@login_required
def task_list():

    tasks = Task.query.filter(Task.deleted_flag == False).order_by(Task.priority.desc())

    return render_template("task_list.html", tasks=tasks)


@task_bp.route("/tasks/create", methods=["GET", "POST"])
@login_required
def create_task():

    if request.method == "POST":
        task = Task(
            title=request.form["title"],
            description=request.form["description"],
            start_date=datetime.strptime(request.form["start_date"], "%Y-%m-%d"),
            end_date=datetime.strptime(request.form["end_date"], "%Y-%m-%d"),
            assigned_user=current_user.id,
            created_by=current_user.id,
        )

        db.session.add(task)
        db.session.commit()

        return redirect("/tasks")

    return render_template("task_create.html")
