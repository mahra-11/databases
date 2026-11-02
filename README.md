# Air Ticket Reservation System (CSCI-SHU 213, Project Part 3)

A web application for the air ticket reservation system, built with **Python / Flask** and **MySQL**
on top of the posted Part 2 relational schema. It supports three types of users: customers,
booking agents and airline staff. Each one has their own home page and use cases.

* `USE_CASES.md` lists every use case and the SQL queries it runs.
* The file list is below.

## Setup

1. Install MySQL (or MariaDB) and Python 3.9 or newer.
2. Create the tables and load the sample data:
   ```bash
   mysql -u root -p < sql/schema.sql
   ```
   ```bash
   mysql -u root -p < sql/sample_data.sql
   ```
   `schema.sql` creates the `air_ticket` database. **It drops and recreates all tables.**
   Sample dates are relative to the moment you load them, so there are always past and upcoming flights.
   Reload `sample_data.sql` (after `schema.sql`) before a demo to get fresh dates.
3. Install the Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Tell the app how to reach the database. The defaults are `localhost:3306`, user `root`,
   an empty password and database `air_ticket`. Override them with environment variables if needed:
   ```bash
   export DB_USER=root DB_PASSWORD=yourpassword
   ```
5. Run the app and open http://127.0.0.1:5000:
   ```bash
   python app.py
   ```

### Sample accounts (password for every account: `password`)

| Type | Login | Notes |
|---|---|---|
| Airline staff | `ce_admin` | China Eastern, Admin + Operator |
| Airline staff | `ce_operator` | China Eastern, Operator only |
| Airline staff | `ce_staff` | China Eastern, no permissions |
| Airline staff | `ca_admin` / `dl_admin` | Air China / Delta, Admin + Operator |
| Booking agent | `agent1@example.com` | works for China Eastern and Air China |
| Booking agent | `agent2@example.com` | works for Delta |
| Booking agent | `agent3@example.com` | works for no airline (cannot buy until an Admin adds them) |
| Customer | `alice@example.com`, `bob@…`, `carol@…`, `david@…`, `emma@…`, `frank@…` | |

China Eastern flight 205 uses a 3-seat airplane that is already full, so you can test the "sold out" check.

## Changes to the posted schema

The handout allows small additions to support the features:

* `ticket.purchase_date` (DATETIME): needed for "track my spending", commission, reports, top agents and revenue.
* `ticket.ticket_id` is `AUTO_INCREMENT` so the app can create tickets.
* `booking_agent.booking_agent_id` is `UNIQUE`. It is assigned automatically at registration (next free number).
* CHECK constraints: permission is `Admin` or `Operator`, `seats > 0`, `price >= 0`.

Booking agents earn a fixed **10%** commission on the flight price (`COMMISSION_RATE` in `config.py`).

## Files

| File | What's in it |
|---|---|
| `app.py` | Creates the Flask app, registers the route modules, template filters and error pages. Run it to start the server. |
| `config.py` | Database connection settings (from environment variables), secret key, commission rate, flight statuses, permission names. |
| `db.py` | Opens one MySQL connection per request and provides `query_all`, `query_one` and `execute`. All SQL uses `%s` parameters. |
| `auth_utils.py` | MD5 password hashing, the `login_required(user_type)` and `permission_required(permission)` decorators, and helpers that look up a staff member's airline or an agent's airlines. |
| `queries.py` | Shared code: the common flight `SELECT`, upcoming-flight search, the ticket purchase transaction (capacity check), form parsing/validation and month-by-month chart data. |
| `routes/public.py` | Public pages: home page, flight search and flight status. A `/home` route sends logged-in users to their own home page. |
| `routes/auth.py` | Registration for all three user types, login and logout. |
| `routes/customer.py` | Customer use cases: home, view my flights, search and purchase, track my spending. |
| `routes/agent.py` | Booking agent use cases: home, view my flights, search and purchase for a customer, commission, top customers. |
| `routes/staff.py` | Airline staff use cases 1–12 (flights, create flight, change status, airplanes, airports, top agents, frequent customers, reports, revenue, destinations, permissions, add agents). |
| `templates/base.html` | Shared page layout: navigation bar (changes by user type) and error/success messages. |
| `templates/_macros.html` | Reusable pieces: flight table (with optional Buy buttons), search form, date range form, bar and pie charts. |
| `templates/index.html`, `search.html`, `status.html` | Public home page, flight search results, flight status. |
| `templates/login.html`, `register.html`, `goodbye.html`, `error.html` | Login, registration (one form per user type), logout page, error page. |
| `templates/customer/*.html` | Customer pages: `home`, `flights`, `search`, `spending`. |
| `templates/agent/*.html` | Agent pages: `home`, `flights`, `search`, `commission`, `top_customers`. |
| `templates/staff/*.html` | Staff pages: `home`, `flights`, `flight_customers`, `create_flight`, `change_status`, `add_airplane`, `add_airport`, `booking_agents`, `frequent_customers`, `reports`, `revenue`, `destinations`, `permissions`, `add_agent`. |
| `static/style.css` | Page styling. |
| `static/chart.umd.js` | Chart.js 4.4.1 (MIT license), bundled so the charts also work without internet access. |
| `sql/schema.sql` | `CREATE TABLE` statements. |
| `sql/sample_data.sql` | Sample airlines, airports, airplanes, users, flights and tickets. |
| `requirements.txt` | Python packages: Flask and PyMySQL. |

## Security

* **Passwords** are stored as MD5 hashes. Login compares `md5(input)` with the stored value.
* **SQL injection:** every query passes user input as `%s` parameters to PyMySQL, which escapes them.
  User input is never pasted into SQL text. The only formatted SQL pieces are fixed values chosen in
  the code (table names for login, `INTERVAL 1 MONTH` / `1 YEAR`).
* **Sessions:** login stores `username` and `user_type` in the session. Every protected page checks the
  session and that the account still exists in the database, and logout clears the session.
* **Server-side checks:** the server checks every rule again, even if the page already hides the option.
  It never trusts form values:
  * Staff permissions (`Admin` / `Operator`) are read from `staff_permission` on every request.
  * A staff member's airline is always read from the database. Staff can only view or change their own airline's flights, airplanes, staff and agents.
  * Agents can only buy tickets for airlines listed in `booking_agent_works_for`, and only for registered customers.
  * Purchases are rejected for flights that are full, already departed, cancelled or missing. The flight row is locked during the purchase (`SELECT … FOR UPDATE`), so two people cannot buy the last seat at the same time.

## Team

_Fill in for team projects: who did what._
