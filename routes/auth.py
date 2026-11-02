"""Use cases: Register (3 user types), Login (3 user types), Logout."""
import re

import pymysql
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from auth_utils import USER_TABLES, md5
from db import execute, get_db, query_all, query_one
from queries import InputError, parse_date

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_type = request.form.get("user_type", "")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if user_type not in USER_TABLES:
            flash("Please choose an account type.", "error")
            return render_template("login.html", form=request.form)
        table, key = USER_TABLES[user_type]
        # table/key come from the fixed USER_TABLES dict, never from user input.
        user = query_one(
            "SELECT {key} FROM {table} WHERE {key} = %s AND password = %s".format(key=key, table=table),
            (username, md5(password)),
        )
        if user is None:
            flash("Login failed: wrong username/email, password or account type.", "error")
            return render_template("login.html", form=request.form)
        session.clear()
        session["username"] = user[key]
        session["user_type"] = user_type
        flash("Welcome, %s!" % user[key], "success")
        return redirect(url_for("public.home"))
    return render_template("login.html", form={})


@bp.route("/logout")
def logout():
    session.clear()
    return render_template("goodbye.html")


def required(form, *fields):
    values = {}
    for f in fields:
        v = form.get(f, "").strip()
        if not v:
            raise InputError("Please fill in every field (%s is missing)." % f.replace("_", " "))
        values[f] = v
    return values


def check_password(form):
    pw = form.get("password", "")
    if len(pw) < 4:
        raise InputError("Password must be at least 4 characters.")
    if pw != form.get("confirm_password", ""):
        raise InputError("The two passwords do not match.")
    return md5(pw)


def check_email(email):
    if not EMAIL_RE.match(email):
        raise InputError("Please enter a valid email address.")


@bp.route("/register", methods=["GET", "POST"])
def register():
    user_type = request.values.get("user_type", "customer")
    if user_type not in USER_TABLES:
        user_type = "customer"
    airlines = [r["name"] for r in query_all("SELECT name FROM airline ORDER BY name")]

    if request.method == "POST":
        f = request.form
        try:
            if user_type == "customer":
                register_customer(f)
            elif user_type == "agent":
                register_agent(f)
            else:
                register_staff(f, airlines)
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except InputError as e:
            flash(str(e), "error")
        except pymysql.err.IntegrityError:
            get_db().rollback()
            flash("An account with that email/username already exists.", "error")
    return render_template("register.html", user_type=user_type, airlines=airlines, form=request.form)


def register_customer(f):
    v = required(f, "email", "name", "building_number", "street", "city", "state",
                 "phone_number", "passport_number", "passport_expiration",
                 "passport_country", "date_of_birth")
    check_email(v["email"])
    pw = check_password(f)
    passport_exp = parse_date(v["passport_expiration"], "passport expiration date", True)
    dob = parse_date(v["date_of_birth"], "date of birth", True)
    if query_one("SELECT 1 FROM customer WHERE email = %s", (v["email"],)):
        raise InputError("A customer with that email already exists.")
    execute(
        """INSERT INTO customer (email, name, password, building_number, street, city, state,
                                 phone_number, passport_number, passport_expiration,
                                 passport_country, date_of_birth)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (v["email"], v["name"], pw, v["building_number"], v["street"], v["city"], v["state"],
         v["phone_number"], v["passport_number"], passport_exp, v["passport_country"], dob),
    )


def register_agent(f):
    v = required(f, "email")
    check_email(v["email"])
    pw = check_password(f)
    if query_one("SELECT 1 FROM booking_agent WHERE email = %s", (v["email"],)):
        raise InputError("A booking agent with that email already exists.")
    # booking_agent_id is assigned automatically (next free number).
    execute(
        """INSERT INTO booking_agent (email, password, booking_agent_id)
           SELECT %s, %s, COALESCE(MAX(booking_agent_id), 1000) + 1 FROM booking_agent""",
        (v["email"], pw),
    )


def register_staff(f, airlines):
    v = required(f, "username", "first_name", "last_name", "date_of_birth", "airline_name")
    pw = check_password(f)
    dob = parse_date(v["date_of_birth"], "date of birth", True)
    if v["airline_name"] not in airlines:
        raise InputError("Please choose an existing airline.")
    if query_one("SELECT 1 FROM airline_staff WHERE username = %s", (v["username"],)):
        raise InputError("That username is already taken.")
    # New staff start with no permissions.
    execute(
        """INSERT INTO airline_staff (username, password, first_name, last_name, date_of_birth, airline_name)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (v["username"], pw, v["first_name"], v["last_name"], dob, v["airline_name"]),
    )
