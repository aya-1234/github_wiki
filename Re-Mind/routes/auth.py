from flask import Blueprint, redirect, render_template, request
from flask_login import login_user
from werkzeug.security import check_password_hash

from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def login():

    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():

    user = User.query.filter_by(login_id=request.form["login_id"]).first()

    if user and check_password_hash(user.password_hash, request.form["password"]):
        login_user(user)

        return redirect("/tasks")

    return "Login Failed"
