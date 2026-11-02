"""Booking agent use cases: view my flights, search & purchase for customers,
view my commission, view top customers."""
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import config
from auth_utils import agent_airlines, login_required
from db import query_all, query_one
from queries import (FLIGHT_SELECT, InputError, end_exclusive, location_condition,
                     parse_date, parse_date_range, parse_int, purchase_ticket,
                     search_upcoming_flights)

bp = Blueprint("agent", __name__, url_prefix="/agent")

AGENT_TICKETS_SELECT = FLIGHT_SELECT.replace(
    "SELECT f.airline_name",
    "SELECT tk.ticket_id, tk.purchase_date, tk.customer_email, f.airline_name",
).replace(
    "FROM flight f",
    "FROM ticket tk JOIN flight f ON f.airline_name = tk.airline_name AND f.flight_num = tk.flight_num",
)

RATE = config.COMMISSION_RATE


@bp.route("/")
@login_required("agent")
def home():
    me = session["username"]
    info = query_one("SELECT booking_agent_id FROM booking_agent WHERE email = %s", (me,))
    upcoming = query_all(
        AGENT_TICKETS_SELECT + " WHERE tk.booking_agent_email = %s AND f.departure_time > NOW() ORDER BY f.departure_time",
        (me,),
    )
    return render_template("agent/home.html", info=info, airlines=agent_airlines(me), flights=upcoming)


@bp.route("/flights")
@login_required("agent")
def my_flights():
    me = session["username"]
    sql = AGENT_TICKETS_SELECT + " WHERE tk.booking_agent_email = %s"
    args = [me]
    try:
        start, end = parse_date_range(request.args)
        source = request.args.get("source", "").strip()
        destination = request.args.get("destination", "").strip()
        customer = request.args.get("customer", "").strip()
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
        if customer:
            sql += " AND tk.customer_email = %s"
            args.append(customer)
        flights = query_all(sql + " ORDER BY f.departure_time", args)
    except InputError as e:
        flash(str(e), "error")
        flights = []
    return render_template("agent/flights.html", flights=flights, args=request.args)


@bp.route("/search")
@login_required("agent")
def search():
    me = session["username"]
    airlines = agent_airlines(me)
    flights = None
    try:
        on_date = parse_date(request.args.get("date"), "date")
        if "source" in request.args:
            # Only flights of airlines this agent works for can be bought.
            flights = search_upcoming_flights(
                request.args.get("source", "").strip(),
                request.args.get("destination", "").strip(),
                on_date,
                airlines=airlines,
            )
    except InputError as e:
        flash(str(e), "error")
    return render_template("agent/search.html", flights=flights, args=request.args, airlines=airlines)


@bp.route("/purchase", methods=["POST"])
@login_required("agent")
def purchase():
    me = session["username"]
    try:
        airline = request.form.get("airline_name", "")
        flight_num = parse_int(request.form.get("flight_num"), "Flight number")
        customer_email = request.form.get("customer_email", "").strip()
        if not customer_email:
            raise InputError("Please enter the customer's email.")
        # Server-side checks (do not trust the form):
        if airline not in agent_airlines(me):
            raise InputError("You do not work for %s, so you cannot sell its tickets." % airline)
        if query_one("SELECT 1 FROM customer WHERE email = %s", (customer_email,)) is None:
            raise InputError("No customer is registered with the email %s." % customer_email)
        ticket_id = purchase_ticket(airline, flight_num, customer_email, agent_email=me)
        flash("Ticket #%d purchased for %s on %s flight %d." % (ticket_id, customer_email, airline, flight_num),
              "success")
        return redirect(url_for("agent.my_flights"))
    except InputError as e:
        flash("Purchase failed: %s" % e, "error")
        return redirect(request.referrer or url_for("agent.search"))


@bp.route("/commission")
@login_required("agent")
def commission():
    """Default: last 30 days. Optional date range."""
    me = session["username"]
    today = date.today()
    custom = bool(request.args.get("start") or request.args.get("end"))
    try:
        if custom:
            start, end = parse_date_range(request.args, default_end=today)
            if start is None:
                raise InputError("Please enter a start date.")
        else:
            start, end = today - timedelta(days=30), today
    except InputError as e:
        flash(str(e), "error")
        return redirect(url_for("agent.commission"))

    row = query_one(
        """SELECT COUNT(*) AS tickets, COALESCE(SUM(f.price), 0) * %s AS commission
           FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           WHERE t.booking_agent_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s""",
        (RATE, me, start, end_exclusive(end)),
    )
    tickets = row["tickets"]
    total = float(row["commission"] or 0)
    average = total / tickets if tickets else 0
    return render_template("agent/commission.html", tickets=tickets, total=total, average=average,
                           start=start, end=end, custom=custom, rate=RATE)


@bp.route("/top-customers")
@login_required("agent")
def top_customers():
    me = session["username"]
    by_tickets = query_all(
        """SELECT t.customer_email, c.name, COUNT(*) AS tickets
           FROM ticket t JOIN customer c ON c.email = t.customer_email
           WHERE t.booking_agent_email = %s AND t.purchase_date >= NOW() - INTERVAL 6 MONTH
           GROUP BY t.customer_email, c.name
           ORDER BY tickets DESC, t.customer_email
           LIMIT 5""",
        (me,),
    )
    by_commission = query_all(
        """SELECT t.customer_email, c.name, SUM(f.price) * %s AS commission
           FROM ticket t
           JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           JOIN customer c ON c.email = t.customer_email
           WHERE t.booking_agent_email = %s AND t.purchase_date >= NOW() - INTERVAL 1 YEAR
           GROUP BY t.customer_email, c.name
           ORDER BY commission DESC, t.customer_email
           LIMIT 5""",
        (RATE, me),
    )
    return render_template("agent/top_customers.html", by_tickets=by_tickets, by_commission=by_commission)
