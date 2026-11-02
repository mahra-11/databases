"""Queries and helpers shared by several components (flight search, ticket
purchase, monthly bar-chart data, form date parsing)."""
from datetime import date, datetime, timedelta

from db import get_db, query_all

# Common SELECT for showing flights: joins the airports (for city names) and
# the airplane (for capacity) and counts the tickets already sold.
FLIGHT_SELECT = """
    SELECT f.airline_name, f.flight_num,
           f.departure_airport, da.city AS departure_city, f.departure_time,
           f.arrival_airport,   aa.city AS arrival_city,   f.arrival_time,
           f.price, f.status, f.airplane_id, ap.seats,
           (SELECT COUNT(*) FROM ticket t
             WHERE t.airline_name = f.airline_name AND t.flight_num = f.flight_num) AS sold
    FROM flight f
    JOIN airport da  ON da.name = f.departure_airport
    JOIN airport aa  ON aa.name = f.arrival_airport
    JOIN airplane ap ON ap.id = f.airplane_id AND ap.airline_name = f.airline_name
"""


class InputError(ValueError):
    """Raised when a form value is invalid; the message is shown to the user."""


# ---------- form parsing ----------

def parse_date(value, field="date", required=False):
    value = (value or "").strip()
    if not value:
        if required:
            raise InputError("Please enter the %s." % field)
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise InputError("Invalid %s: use the format YYYY-MM-DD." % field)


def parse_datetime(value, field):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise InputError("Invalid %s: please give a date and time." % field)


def parse_int(value, field, minimum=None):
    try:
        n = int((value or "").strip())
    except ValueError:
        raise InputError("%s must be a whole number." % field)
    if minimum is not None and n < minimum:
        raise InputError("%s must be at least %d." % (field, minimum))
    return n


def parse_date_range(args, default_start=None, default_end=None):
    """Read 'start'/'end' from a form. Returns (start_date, end_date) inclusive."""
    start = parse_date(args.get("start"), "start date") or default_start
    end = parse_date(args.get("end"), "end date") or default_end
    if start and end and start > end:
        raise InputError("The start date must be before the end date.")
    return start, end


def end_exclusive(d):
    """Inclusive end date -> exclusive upper bound for a DATETIME comparison."""
    return d + timedelta(days=1)


# ---------- flight search ----------

def location_condition(column_airport, column_city, value, args):
    """'Shanghai' matches the city, 'PVG' matches the airport name."""
    args.extend([value, value])
    return " AND ({} = %s OR {} = %s)".format(column_airport, column_city)


def search_upcoming_flights(source=None, destination=None, on_date=None, airlines=None):
    """Upcoming flights (departure in the future) matching the optional filters.

    airlines: optional list of airline names to restrict to (used for agents).
    """
    sql = FLIGHT_SELECT + " WHERE f.departure_time > NOW()"
    args = []
    if source:
        sql += location_condition("f.departure_airport", "da.city", source, args)
    if destination:
        sql += location_condition("f.arrival_airport", "aa.city", destination, args)
    if on_date:
        sql += " AND DATE(f.departure_time) = %s"
        args.append(on_date)
    if airlines is not None:
        if not airlines:
            return []
        sql += " AND f.airline_name IN ({})".format(", ".join(["%s"] * len(airlines)))
        args.extend(airlines)
    sql += " ORDER BY f.departure_time"
    return query_all(sql, args)


# ---------- ticket purchase ----------

def purchase_ticket(airline_name, flight_num, customer_email, agent_email=None):
    """Create a ticket in a single transaction. Raises InputError on failure.

    The flight row is locked (SELECT ... FOR UPDATE) so two buyers cannot take
    the last seat at the same time.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT f.status, f.departure_time > NOW() AS in_future, ap.seats
                   FROM flight f
                   JOIN airplane ap ON ap.id = f.airplane_id AND ap.airline_name = f.airline_name
                   WHERE f.airline_name = %s AND f.flight_num = %s
                   FOR UPDATE""",
                (airline_name, flight_num),
            )
            flight = cur.fetchone()
            if flight is None:
                raise InputError("That flight does not exist.")
            if not flight["in_future"]:
                raise InputError("That flight has already departed.")
            if flight["status"] == "Cancelled":
                raise InputError("That flight has been cancelled.")
            cur.execute(
                "SELECT COUNT(*) AS sold FROM ticket WHERE airline_name = %s AND flight_num = %s",
                (airline_name, flight_num),
            )
            if cur.fetchone()["sold"] >= flight["seats"]:
                raise InputError("Sorry, that flight is sold out.")
            cur.execute(
                """INSERT INTO ticket (airline_name, flight_num, customer_email,
                                       booking_agent_email, purchase_date)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (airline_name, flight_num, customer_email, agent_email),
            )
            ticket_id = cur.lastrowid
        conn.commit()
        return ticket_id
    except Exception:
        conn.rollback()
        raise


# ---------- monthly series for bar charts ----------

def month_labels(start, end):
    """All 'YYYY-MM' strings from start's month to end's month, inclusive."""
    labels = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        labels.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return labels


def monthly_series(rows, start, end, value_key):
    """Turn rows of {'ym': 'YYYY-MM', value_key: n} into chart labels/values,
    filling months with no data with 0."""
    by_month = {r["ym"]: float(r[value_key] or 0) for r in rows}
    labels = month_labels(start, end)
    return labels, [by_month.get(label, 0) for label in labels]


def first_of_month_n_ago(n, today=None):
    """First day of the month n months before today's month (n=5 -> 6 months incl. this one)."""
    today = today or date.today()
    y, m = today.year, today.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)
