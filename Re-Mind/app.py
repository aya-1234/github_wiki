from flask import Flask

from extensions import db, login_manager, migrate

app = Flask(__name__)

app.config["SECRET_KEY"] = "change_me"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:password@localhost/reminder"
)

db.init_app(app)
login_manager.init_app(app)
migrate.init_app(app, db)

from routes.auth import auth_bp
from routes.task import task_bp

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)

if __name__ == "__main__":
    app.run(debug=True)
