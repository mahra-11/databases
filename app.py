"""Air Ticket Reservation System - Flask entry point.

Run:  python app.py      (then open http://127.0.0.1:5000)
"""
from flask import Flask, render_template, session

import config
from db import close_db
from routes.agent import bp as agent_bp
from routes.auth import bp as auth_bp
from routes.customer import bp as customer_bp
from routes.public import bp as public_bp
from routes.staff import bp as staff_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.teardown_appcontext(close_db)

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(staff_bp)

    @app.context_processor
    def inject_user():
        return {"session_user": session.get("username"), "session_type": session.get("user_type")}

    @app.template_filter("dt")
    def format_datetime(value):
        return value.strftime("%Y-%m-%d %H:%M") if value else ""

    @app.template_filter("money")
    def format_money(value):
        return "{:,.2f}".format(float(value or 0))

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", message="Something went wrong on the server."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
