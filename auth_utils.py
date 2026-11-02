"""Session / authorization helpers shared by all components.

Every protected page checks the session *and* re-checks the database, so a
hand-crafted HTTP request cannot skip the checks that the UI performs.
"""
import hashlib
from functools import wraps

from flask import flash, redirect, session, url_for

from db import query_all, query_one

USER_TABLES = {
    # user_type: (table, key column)
    "customer": ("customer", "email"),
    "agent": ("booking_agent", "email"),
    "staff": ("airline_staff", "username"),
}


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def current_user():
    return session.get("username")


def login_required(user_type):
    """Allow the view only for a logged-in user of the given type."""
    table, key = USER_TABLES[user_type]

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            username = session.get("username")
            if not username or session.get("user_type") != user_type:
                flash("Please log in with a %s account to use that page." % user_type, "error")
                return redirect(url_for("auth.login"))
            # The account must still exist in the database.
            if query_one("SELECT 1 FROM {} WHERE {} = %s".format(table, key), (username,)) is None:
                session.clear()
                flash("Your account no longer exists. Please log in again.", "error")
                return redirect(url_for("auth.login"))
            return view(*args, **kwargs)

        return wrapper

    return decorator


# ---------- airline staff helpers ----------

def staff_airline(username):
    row = query_one("SELECT airline_name FROM airline_staff WHERE username = %s", (username,))
    return row["airline_name"] if row else None


def staff_has_permission(username, permission):
    row = query_one(
        "SELECT 1 FROM staff_permission WHERE username = %s AND permission = %s",
        (username, permission),
    )
    return row is not None


def permission_required(permission):
    """Use *after* @login_required('staff'). Checks staff_permission in the database."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not staff_has_permission(session["username"], permission):
                flash('You need the "%s" permission to do that.' % permission, "error")
                return redirect(url_for("staff.home"))
            return view(*args, **kwargs)

        return wrapper

    return decorator


# ---------- booking agent helpers ----------

def agent_airlines(email):
    rows = query_all(
        "SELECT airline_name FROM booking_agent_works_for WHERE agent_email = %s ORDER BY airline_name",
        (email,),
    )
    return [r["airline_name"] for r in rows]
