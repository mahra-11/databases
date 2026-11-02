"""Customer use cases: view my flights, search & purchase tickets, track spending."""
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from auth_utils import login_required
from db import query_all, query_one
from queries import (FLIGHT_SELECT, InputError, end_exclusive, first_of_month_n_ago,
                     location_condition, monthly_series, parse_date, parse_date_range,
                     parse_int, purchase_ticket, search_upcoming_flights)

bp = Blueprint("customer", __name__, url_prefix="/customer")

# Flights the customer holds tickets for (one row per ticket).
MY_TICKETS_SELECT = FLIGHT_SELECT.replace(
    "SELECT f.airline_name",
    "SELECT tk.ticket_id, tk.purchase_date, tk.booking_agent_email, f.airline_name",
).replace(
    "FROM flight f",
    "FROM ticket tk JOIN flight f ON f.airline_name = tk.airline_name AND f.flight_num = tk.flight_num",
)


@bp.route("/")
@login_required("customer")
def home():
    me = session["username"]
    customer = query_one("SELECT name FROM customer WHERE email = %s", (me,))
    upcoming = query_all(
        MY_TICKETS_SELECT + " WHERE tk.customer_email = %s AND f.departure_time > NOW() ORDER BY f.departure_time",
        (me,),
    )
    return render_template("customer/home.html", customer=customer, flights=upcoming)


@bp.route("/flights")
@login_required("customer")
def my_flights():
    """Default: upcoming flights. Optional filters: date range, source, destination, past flights."""
    me = session["username"]
    sql = MY_TICKETS_SELECT + " WHERE tk.customer_email = %s"
    args = [me]
    try:
        start, end = parse_date_range(request.args)
        source = request.args.get("source", "").strip()
        destination = request.args.get("destination", "").strip()
        show = request.args.get("show", "upcoming")
        if show == "upcoming":
            sql += " AND f.departure_time > NOW()"
        elif show == "past":
            sql += " AND f.departure_time <= NOW()"
        if start:
            sql += " AND f.departure_time >= %s"
            args.append(start)
        if end:
            sql += " AND f.departure_time < %s"
            args.append(end_exclusive(end))
        if source:
            sql += location_condition("f.departure_airport", "da.city", source, args)
        if destination:
            sql += location_condition("f.arrival_airport", "aa.city", destination, args)
        flights = query_all(sql + " ORDER BY f.departure_time", args)
    except InputError as e:
        flash(str(e), "error")
        flights = []
    return render_template("customer/flights.html", flights=flights, args=request.args)


@bp.route("/search")
@login_required("customer")
def search():
    flights = None
    try:
        on_date = parse_date(request.args.get("date"), "date")
        if "source" in request.args:
            flights = search_upcoming_flights(
                request.args.get("source", "").strip(),
                request.args.get("destination", "").strip(),
                on_date,
            )
    except InputError as e:
        flash(str(e), "error")
    return render_template("customer/search.html", flights=flights, args=request.args)


@bp.route("/purchase", methods=["POST"])
@login_required("customer")
def purchase():
    try:
        airline = request.form.get("airline_name", "")
        flight_num = parse_int(request.form.get("flight_num"), "Flight number")
        ticket_id = purchase_ticket(airline, flight_num, session["username"])
        flash("Ticket #%d purchased for %s flight %d." % (ticket_id, airline, flight_num), "success")
        return redirect(url_for("customer.my_flights"))
    except InputError as e:
        flash("Purchase failed: %s" % e, "error")
        return redirect(request.referrer or url_for("customer.search"))


@bp.route("/spending")
@login_required("customer")
def spending():
    """Default: total spent in the past year + month-wise bars for the last 6 months.
    With a date range: total and month-wise bars for that range."""
    me = session["username"]
    today = date.today()
    custom = bool(request.args.get("start") or request.args.get("end"))
    try:
        if custom:
            start, end = parse_date_range(request.args, default_end=today)
            if start is None:
                raise InputError("Please enter a start date.")
            chart_start = start
        else:
            start, end = today - timedelta(days=365), today
            chart_start = first_of_month_n_ago(5, today)
    except InputError as e:
        flash(str(e), "error")
        return redirect(url_for("customer.spending"))

    total = query_one(
        """SELECT COALESCE(SUM(f.price), 0) AS total, COUNT(*) AS tickets
           FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           WHERE t.customer_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s""",
        (me, start, end_exclusive(end)),
    )
    rows = query_all(
        """SELECT DATE_FORMAT(t.purchase_date, '%%Y-%%m') AS ym, SUM(f.price) AS spent
           FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           WHERE t.customer_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s
           GROUP BY ym ORDER BY ym""",
        (me, chart_start, end_exclusive(end)),
    )
    labels, values = monthly_series(rows, chart_start, end, "spent")
    return render_template("customer/spending.html", total=total, start=start, end=end,
                           chart_start=chart_start, labels=labels, values=values, custom=custom)
