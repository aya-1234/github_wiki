from datetime import datetime

from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    login_id = db.Column(db.String(100), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    user_name = db.Column(db.String(100), nullable=False)

    role = db.Column(db.String(20), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text)

    start_date = db.Column(db.Date, nullable=False)

    end_date = db.Column(db.Date, nullable=False)

    status_flag = db.Column(db.Integer, default=0)

    priority = db.Column(db.Integer, default=1)

    assigned_user = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    deleted_flag = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ReminderHistory(db.Model):
    __tablename__ = "reminder_histories"

    id = db.Column(db.Integer, primary_key=True)

    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"))

    notify_type = db.Column(db.String(50))

    notify_date = db.Column(db.DateTime)

    result = db.Column(db.String(20))
