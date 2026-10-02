from flask import Blueprint

from auth.decorators import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@admin_required
def user_list():

    return "管理者専用画面"
