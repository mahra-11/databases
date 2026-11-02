"""Use case: View Public Info (no login needed) - flight search and flight status."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import query_all
from queries import FLIGHT_SELECT, InputError, parse_date, parse_int, search_upcoming_flights

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/home")
def home():
    """Send a logged-in user to the home page for their account type."""
    user_type = session.get("user_type")
    if user_type == "customer":
        return redirect(url_for("customer.home"))
    if user_type == "agent":
        return redirect(url_for("agent.home"))
    if user_type == "staff":
        return redirect(url_for("staff.home"))
    return redirect(url_for("public.index"))


@bp.route("/search")
def search():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    flights = None
    try:
        on_date = parse_date(request.args.get("date"), "date")
        if "source" in request.args:
            flights = search_upcoming_flights(source, destination, on_date)
    except InputError as e:
        flash(str(e), "error")
    return render_template("search.html", flights=flights, args=request.args)


@bp.route("/status")
def status():
    flights = None
    if "flight_num" in request.args:
        try:
            flight_num = parse_int(request.args.get("flight_num"), "Flight number")
            the_date = parse_date(request.args.get("date"), "date")
            date_type = request.args.get("date_type", "departure")
            column = "f.arrival_time" if date_type == "arrival" else "f.departure_time"
            airline = request.args.get("airline", "").strip()

            sql = FLIGHT_SELECT + " WHERE f.flight_num = %s"
            args = [flight_num]
            if airline:
                sql += " AND f.airline_name = %s"
                args.append(airline)
            if the_date:
                sql += " AND DATE({}) = %s".format(column)  # column is one of two fixed names
                args.append(the_date)
            sql += " ORDER BY f.departure_time"
            flights = query_all(sql, args)
        except InputError as e:
            flash(str(e), "error")
    return render_template("status.html", flights=flights, args=request.args)
