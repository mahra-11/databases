"""Airline staff use cases. Every query is limited to the staff member's own
airline, which is always read from the database (never from the form)."""
from datetime import date, timedelta

import pymysql
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import config
from auth_utils import login_required, permission_required, staff_airline
from db import execute, get_db, query_all, query_one
from queries import (FLIGHT_SELECT, InputError, end_exclusive,
                     location_condition, monthly_series, parse_date_range, parse_datetime,
                     parse_int)

bp = Blueprint("staff", __name__, url_prefix="/staff")

RATE = config.COMMISSION_RATE


def my_airline():
    return staff_airline(session["username"])


def my_permissions():
    rows = query_all("SELECT permission FROM staff_permission WHERE username = %s ORDER BY permission",
                     (session["username"],))
    return [r["permission"] for r in rows]


def next_30_days_flights(airline):
    return query_all(
        FLIGHT_SELECT + """ WHERE f.airline_name = %s
                            AND f.departure_time BETWEEN NOW() AND NOW() + INTERVAL 30 DAY
                            ORDER BY f.departure_time""",
        (airline,),
    )


@bp.route("/")
@login_required("staff")
def home():
    staff = query_one(
        "SELECT username, first_name, last_name, airline_name FROM airline_staff WHERE username = %s",
        (session["username"],),
    )
    return render_template("staff/home.html", staff=staff, permissions=my_permissions())


# ---------- 1. View my flights ----------

@bp.route("/flights")
@login_required("staff")
def flights():
    """Default: upcoming flights in the next 30 days. Filters: date range, source, destination."""
    airline = my_airline()
    filtered = any(request.args.get(k) for k in ("start", "end", "source", "destination"))
    try:
        if not filtered:
            rows = next_30_days_flights(airline)
        else:
            start, end = parse_date_range(request.args)
            sql = FLIGHT_SELECT + " WHERE f.airline_name = %s"
            args = [airline]
            if start:
                sql += " AND f.departure_time >= %s"
                args.append(start)
            if end:
                sql += " AND f.departure_time < %s"
                args.append(end_exclusive(end))
            source = request.args.get("source", "").strip()
            destination = request.args.get("destination", "").strip()
            if source:
                sql += location_condition("f.departure_airport", "da.city", source, args)
            if destination:
                sql += location_condition("f.arrival_airport", "aa.city", destination, args)
            rows = query_all(sql + " ORDER BY f.departure_time", args)
    except InputError as e:
        flash(str(e), "error")
        rows = []
    return render_template("staff/flights.html", flights=rows, airline=airline,
                           args=request.args, filtered=filtered)


@bp.route("/flights/<int:flight_num>/customers")
@login_required("staff")
def flight_customers(flight_num):
    airline = my_airline()
    flight = query_one(FLIGHT_SELECT + " WHERE f.airline_name = %s AND f.flight_num = %s",
                       (airline, flight_num))
    if flight is None:
        flash("Your airline has no flight %d." % flight_num, "error")
        return redirect(url_for("staff.flights"))
    customers = query_all(
        """SELECT t.ticket_id, c.email, c.name, c.phone_number, t.booking_agent_email, t.purchase_date
           FROM ticket t JOIN customer c ON c.email = t.customer_email
           WHERE t.airline_name = %s AND t.flight_num = %s
           ORDER BY c.name""",
        (airline, flight_num),
    )
    return render_template("staff/flight_customers.html", flight=flight, customers=customers)


# ---------- 2. Create new flights (Admin) ----------

@bp.route("/flights/create", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Admin")
def create_flight():
    airline = my_airline()
    if request.method == "POST":
        f = request.form
        try:
            flight_num = parse_int(f.get("flight_num"), "Flight number", 1)
            departure = parse_datetime(f.get("departure_time"), "departure time")
            arrival = parse_datetime(f.get("arrival_time"), "arrival time")
            if arrival <= departure:
                raise InputError("Arrival time must be after departure time.")
            try:
                price = float(f.get("price", ""))
            except ValueError:
                raise InputError("Price must be a number.")
            if price < 0:
                raise InputError("Price cannot be negative.")
            airplane_id = parse_int(f.get("airplane_id"), "Airplane")
            dep_airport = f.get("departure_airport", "")
            arr_airport = f.get("arrival_airport", "")
            if dep_airport == arr_airport:
                raise InputError("Departure and arrival airports must be different.")
            status = f.get("status", "Upcoming")
            if status not in config.FLIGHT_STATUSES:
                raise InputError("Invalid status.")
            if not query_one("SELECT 1 FROM airplane WHERE id = %s AND airline_name = %s", (airplane_id, airline)):
                raise InputError("Your airline has no airplane %d." % airplane_id)
            for code in (dep_airport, arr_airport):
                if not query_one("SELECT 1 FROM airport WHERE name = %s", (code,)):
                    raise InputError("Unknown airport %s." % code)
            if query_one("SELECT 1 FROM flight WHERE airline_name = %s AND flight_num = %s", (airline, flight_num)):
                raise InputError("Flight %d already exists for %s." % (flight_num, airline))
            execute(
                """INSERT INTO flight (flight_num, airline_name, departure_time, arrival_time, price,
                                       status, airplane_id, departure_airport, arrival_airport)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (flight_num, airline, departure, arrival, price, status, airplane_id, dep_airport, arr_airport),
            )
            flash("Flight %d created." % flight_num, "success")
            return redirect(url_for("staff.create_flight"))
        except InputError as e:
            flash(str(e), "error")
    airports = query_all("SELECT name, city FROM airport ORDER BY city, name")
    airplanes = query_all("SELECT id, seats FROM airplane WHERE airline_name = %s ORDER BY id", (airline,))
    return render_template("staff/create_flight.html", airline=airline, airports=airports,
                           airplanes=airplanes, statuses=config.FLIGHT_STATUSES,
                           flights=next_30_days_flights(airline), form=request.form)


# ---------- 3. Change status of flights (Operator) ----------

@bp.route("/flights/status", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Operator")
def change_status():
    airline = my_airline()
    if request.method == "POST":
        try:
            flight_num = parse_int(request.form.get("flight_num"), "Flight number")
            status = request.form.get("status", "")
            if status not in config.FLIGHT_STATUSES:
                raise InputError("Invalid status.")
            conn = get_db()
            with conn.cursor() as cur:
                n = cur.execute("UPDATE flight SET status = %s WHERE airline_name = %s AND flight_num = %s",
                                (status, airline, flight_num))
            conn.commit()
            exists = n or query_one("SELECT 1 FROM flight WHERE airline_name = %s AND flight_num = %s",
                                    (airline, flight_num))
            if not exists:
                raise InputError("Your airline has no flight %d." % flight_num)
            flash("Flight %d is now \"%s\"." % (flight_num, status), "success")
            return redirect(url_for("staff.change_status"))
        except InputError as e:
            flash(str(e), "error")
    # Flights that are not finished yet (departing from a week ago onward).
    flights = query_all(
        FLIGHT_SELECT + " WHERE f.airline_name = %s AND f.departure_time >= NOW() - INTERVAL 7 DAY ORDER BY f.departure_time",
        (airline,),
    )
    return render_template("staff/change_status.html", flights=flights, statuses=config.FLIGHT_STATUSES,
                           selected=request.args.get("flight_num", ""))


# ---------- 4. Add airplane (Admin) ----------

@bp.route("/airplanes", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Admin")
def add_airplane():
    airline = my_airline()
    added = None
    if request.method == "POST":
        try:
            airplane_id = parse_int(request.form.get("id"), "Airplane ID", 1)
            seats = parse_int(request.form.get("seats"), "Number of seats", 1)
            if query_one("SELECT 1 FROM airplane WHERE id = %s AND airline_name = %s", (airplane_id, airline)):
                raise InputError("Your airline already has an airplane with ID %d." % airplane_id)
            execute("INSERT INTO airplane (id, airline_name, seats) VALUES (%s, %s, %s)",
                    (airplane_id, airline, seats))
            added = airplane_id
            flash("Airplane %d added." % airplane_id, "success")
        except InputError as e:
            flash(str(e), "error")
    # Confirmation page: all airplanes owned by the airline.
    airplanes = query_all("SELECT id, seats FROM airplane WHERE airline_name = %s ORDER BY id", (airline,))
    return render_template("staff/add_airplane.html", airline=airline, airplanes=airplanes, added=added)


# ---------- 5. Add new airport (Admin) ----------

@bp.route("/airports", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Admin")
def add_airport():
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip().upper()
            city = request.form.get("city", "").strip()
            if not name or not city:
                raise InputError("Please enter both the airport name and the city.")
            if len(name) > 50 or len(city) > 50:
                raise InputError("Name and city must be at most 50 characters.")
            if query_one("SELECT 1 FROM airport WHERE name = %s", (name,)):
                raise InputError("Airport %s already exists." % name)
            execute("INSERT INTO airport (name, city) VALUES (%s, %s)", (name, city))
            flash("Airport %s (%s) added." % (name, city), "success")
            return redirect(url_for("staff.add_airport"))
        except InputError as e:
            flash(str(e), "error")
    airports = query_all("SELECT name, city FROM airport ORDER BY city, name")
    return render_template("staff/add_airport.html", airports=airports)


# ---------- 6. View all the booking agents ----------

@bp.route("/agents")
@login_required("staff")
def booking_agents():
    airline = my_airline()

    def top_by_tickets(interval):
        # interval is one of two fixed strings below, never user input.
        return query_all(
            """SELECT t.booking_agent_email AS email, b.booking_agent_id, COUNT(*) AS tickets
               FROM ticket t JOIN booking_agent b ON b.email = t.booking_agent_email
               WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL {}
               GROUP BY t.booking_agent_email, b.booking_agent_id
               ORDER BY tickets DESC, email LIMIT 5""".format(interval),
            (airline,),
        )

    by_commission = query_all(
        """SELECT t.booking_agent_email AS email, b.booking_agent_id, SUM(f.price) * %s AS commission
           FROM ticket t
           JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           JOIN booking_agent b ON b.email = t.booking_agent_email
           WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL 1 YEAR
           GROUP BY t.booking_agent_email, b.booking_agent_id
           ORDER BY commission DESC, email LIMIT 5""",
        (RATE, airline),
    )
    return render_template("staff/booking_agents.html", airline=airline,
                           month=top_by_tickets("1 MONTH"), year=top_by_tickets("1 YEAR"),
                           by_commission=by_commission)


# ---------- 7. View frequent customers ----------

@bp.route("/customers")
@login_required("staff")
def frequent_customers():
    airline = my_airline()
    # Customers ranked by number of flights taken on this airline in the last year.
    ranking = query_all(
        """SELECT c.email, c.name, COUNT(*) AS flights
           FROM ticket t
           JOIN flight f   ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
           JOIN customer c ON c.email = t.customer_email
           WHERE t.airline_name = %s
             AND f.departure_time BETWEEN NOW() - INTERVAL 1 YEAR AND NOW()
           GROUP BY c.email, c.name
           ORDER BY flights DESC, c.email
           LIMIT 5""",
        (airline,),
    )
    top_count = ranking[0]["flights"] if ranking else 0
    most_frequent = [r for r in ranking if r["flights"] == top_count]

    email = request.args.get("email", "").strip()
    customer_flights = None
    if email:
        customer_flights = query_all(
            FLIGHT_SELECT.replace("SELECT f.airline_name", "SELECT t.ticket_id, f.airline_name")
                         .replace("FROM flight f", "FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num")
            + " WHERE t.airline_name = %s AND t.customer_email = %s ORDER BY f.departure_time",
            (airline, email),
        )
    return render_template("staff/frequent_customers.html", airline=airline, ranking=ranking,
                           most_frequent=most_frequent, email=email, customer_flights=customer_flights)


# ---------- 8. View reports ----------

@bp.route("/reports")
@login_required("staff")
def reports():
    """Tickets sold in a date range (default last year) + month-wise bar chart.
    Quick ranges: ?range=month or ?range=year."""
    airline = my_airline()
    today = date.today()
    quick = request.args.get("range", "")
    try:
        if quick == "month":
            start, end = today - timedelta(days=30), today
        elif request.args.get("start") or request.args.get("end"):
            start, end = parse_date_range(request.args, default_end=today)
            if start is None:
                raise InputError("Please enter a start date.")
        else:
            quick = "year"
            start, end = today - timedelta(days=365), today
    except InputError as e:
        flash(str(e), "error")
        return redirect(url_for("staff.reports"))

    total = query_one(
        """SELECT COUNT(*) AS tickets FROM ticket
           WHERE airline_name = %s AND purchase_date >= %s AND purchase_date < %s""",
        (airline, start, end_exclusive(end)),
    )["tickets"]
    rows = query_all(
        """SELECT DATE_FORMAT(purchase_date, '%%Y-%%m') AS ym, COUNT(*) AS tickets
           FROM ticket
           WHERE airline_name = %s AND purchase_date >= %s AND purchase_date < %s
           GROUP BY ym ORDER BY ym""",
        (airline, start, end_exclusive(end)),
    )
    labels, values = monthly_series(rows, start, end, "tickets")
    return render_template("staff/reports.html", airline=airline, total=total, start=start, end=end,
                           labels=labels, values=values, quick=quick)


# ---------- 9. Comparison of revenue earned ----------

@bp.route("/revenue")
@login_required("staff")
def revenue():
    airline = my_airline()

    def split(interval):
        row = query_one(
            """SELECT COALESCE(SUM(CASE WHEN t.booking_agent_email IS NULL THEN f.price END), 0) AS direct,
                      COALESCE(SUM(CASE WHEN t.booking_agent_email IS NOT NULL THEN f.price END), 0) AS indirect
               FROM ticket t
               JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
               WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL {}""".format(interval),
            (airline,),
        )
        return {"direct": float(row["direct"]), "indirect": float(row["indirect"])}

    return render_template("staff/revenue.html", airline=airline,
                           month=split("1 MONTH"), year=split("1 YEAR"))


# ---------- 10. View top destinations ----------

@bp.route("/destinations")
@login_required("staff")
def destinations():
    """Top 3 arrival cities by tickets, for this airline's flights that departed
    in the last 3 months / last year."""
    airline = my_airline()

    def top(interval):
        return query_all(
            """SELECT aa.city, COUNT(*) AS tickets
               FROM ticket t
               JOIN flight f   ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
               JOIN airport aa ON aa.name = f.arrival_airport
               WHERE t.airline_name = %s
                 AND f.departure_time BETWEEN NOW() - INTERVAL {} AND NOW()
               GROUP BY aa.city
               ORDER BY tickets DESC, aa.city LIMIT 3""".format(interval),
            (airline,),
        )

    return render_template("staff/destinations.html", airline=airline,
                           three_months=top("3 MONTH"), year=top("1 YEAR"))


# ---------- 11. Grant new permissions (Admin) ----------

@bp.route("/permissions", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Admin")
def permissions():
    airline = my_airline()
    if request.method == "POST":
        try:
            target = request.form.get("username", "").strip()
            permission = request.form.get("permission", "")
            if permission not in config.STAFF_PERMISSIONS:
                raise InputError("Invalid permission.")
            if staff_airline(target) != airline:
                raise InputError("%s is not a staff member of %s." % (target or "That user", airline))
            if query_one("SELECT 1 FROM staff_permission WHERE username = %s AND permission = %s",
                         (target, permission)):
                raise InputError("%s already has the %s permission." % (target, permission))
            execute("INSERT INTO staff_permission (username, permission) VALUES (%s, %s)", (target, permission))
            flash("Granted %s permission to %s." % (permission, target), "success")
            return redirect(url_for("staff.permissions"))
        except InputError as e:
            flash(str(e), "error")
    staff = query_all(
        """SELECT s.username, s.first_name, s.last_name,
                  GROUP_CONCAT(p.permission ORDER BY p.permission SEPARATOR ', ') AS permissions
           FROM airline_staff s LEFT JOIN staff_permission p ON p.username = s.username
           WHERE s.airline_name = %s
           GROUP BY s.username, s.first_name, s.last_name
           ORDER BY s.username""",
        (airline,),
    )
    return render_template("staff/permissions.html", airline=airline, staff=staff,
                           choices=config.STAFF_PERMISSIONS)


# ---------- 12. Add booking agents (Admin) ----------

@bp.route("/agents/add", methods=["GET", "POST"])
@login_required("staff")
@permission_required("Admin")
def add_agent():
    airline = my_airline()
    if request.method == "POST":
        try:
            email = request.form.get("email", "").strip()
            if not email:
                raise InputError("Please enter the booking agent's email.")
            if query_one("SELECT 1 FROM booking_agent WHERE email = %s", (email,)) is None:
                raise InputError("No booking agent is registered with the email %s." % email)
            if query_one("SELECT 1 FROM booking_agent_works_for WHERE agent_email = %s AND airline_name = %s",
                         (email, airline)):
                raise InputError("%s already works for %s." % (email, airline))
            execute("INSERT INTO booking_agent_works_for (agent_email, airline_name) VALUES (%s, %s)",
                    (email, airline))
            flash("%s can now sell tickets for %s." % (email, airline), "success")
            return redirect(url_for("staff.add_agent"))
        except InputError as e:
            flash(str(e), "error")
        except pymysql.err.IntegrityError:
            get_db().rollback()
            flash("Could not add that booking agent.", "error")
    agents = query_all(
        """SELECT b.email, b.booking_agent_id FROM booking_agent_works_for w
           JOIN booking_agent b ON b.email = w.agent_email
           WHERE w.airline_name = %s ORDER BY b.email""",
        (airline,),
    )
    return render_template("staff/add_agent.html", airline=airline, agents=agents)
