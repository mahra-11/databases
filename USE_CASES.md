# Use cases and their queries

`%s` marks a value passed as a query parameter (prepared-statement style).
`me` is the logged-in user's username/email, taken from the session.
`my_airline` is the staff member's airline, read from the database:

```sql
SELECT airline_name FROM airline_staff WHERE username = %s
```

Many pages show flights using one shared query (`FLIGHT_SELECT` in `queries.py`). It joins the two
airports to get city names, the airplane to get the seat count, and counts the tickets already sold:

```sql
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
```

A "source"/"destination" filter matches **either** the airport code **or** the city, e.g.
`AND (f.departure_airport = %s OR da.city = %s)`, so both "PVG" and "Shanghai" work.

---

## Public (no login needed) — `routes/public.py`

### 1a. Search upcoming flights — `GET /search`
Source, destination and date are all optional:
```sql
FLIGHT_SELECT
WHERE f.departure_time > NOW()
  AND (f.departure_airport = %s OR da.city = %s)     -- if source given
  AND (f.arrival_airport   = %s OR aa.city = %s)     -- if destination given
  AND DATE(f.departure_time) = %s                    -- if date given
ORDER BY f.departure_time
```

### 1b. Flight status — `GET /status`
Uses the flight number, plus an optional airline and an optional date. The date can be the departure date or the arrival date:
```sql
FLIGHT_SELECT
WHERE f.flight_num = %s
  AND f.airline_name = %s                  -- optional
  AND DATE(f.departure_time) = %s          -- or DATE(f.arrival_time), optional
ORDER BY f.departure_time
```

## Register — `routes/auth.py`, `GET/POST /register?user_type=customer|agent|staff`
Before inserting, the app checks that all fields are filled in, the email looks valid, the dates are valid and the two passwords match. Passwords are stored as `md5(password)`.

* **Customer**
  ```sql
  SELECT 1 FROM customer WHERE email = %s;          -- duplicate check
  INSERT INTO customer (email, name, password, building_number, street, city, state, phone_number,
                        passport_number, passport_expiration, passport_country, date_of_birth)
  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
  ```
* **Booking agent**: `booking_agent_id` is set to the next free number.
  ```sql
  SELECT 1 FROM booking_agent WHERE email = %s;
  INSERT INTO booking_agent (email, password, booking_agent_id)
  SELECT %s, %s, COALESCE(MAX(booking_agent_id), 1000) + 1 FROM booking_agent;
  ```
* **Airline staff**: the airline must exist. New staff get no permissions.
  ```sql
  SELECT name FROM airline ORDER BY name;           -- airline drop-down + validation
  SELECT 1 FROM airline_staff WHERE username = %s;
  INSERT INTO airline_staff (username, password, first_name, last_name, date_of_birth, airline_name)
  VALUES (%s, %s, %s, %s, %s, %s);
  ```

## Login — `POST /login`
The user picks an account type. The type selects the table and key column: `customer.email`,
`booking_agent.email` or `airline_staff.username`.
```sql
SELECT email FROM customer WHERE email = %s AND password = %s        -- password = md5(input)
```
If a row matches, the app stores `username` and `user_type` in the session and redirects to that user's home page.
If not, it shows an error message on the login page.

Every protected page also checks that the logged-in account still exists:
`SELECT 1 FROM <table> WHERE <key> = %s`.

## Logout — `GET /logout`
Clears the session (no query) and shows a goodbye page.

---

## Customer — `routes/customer.py`

Customer ticket lists use `FLIGHT_SELECT` with the `ticket` table joined in:
`FROM ticket tk JOIN flight f ON f.airline_name = tk.airline_name AND f.flight_num = tk.flight_num …`,
which also adds `tk.ticket_id`, `tk.purchase_date` and `tk.booking_agent_email`.

### Home — `GET /customer/`
```sql
SELECT name FROM customer WHERE email = %s;
... WHERE tk.customer_email = %s AND f.departure_time > NOW() ORDER BY f.departure_time   -- upcoming flights
```

### 1. View my flights — `GET /customer/flights`
Shows upcoming flights by default. Filters: upcoming/past/all, departure date range, source, destination.
```sql
... WHERE tk.customer_email = %s
      AND f.departure_time > NOW()                  -- 'upcoming' (or <= NOW() for 'past')
      AND f.departure_time >= %s AND f.departure_time < %s   -- optional date range
      AND (f.departure_airport = %s OR da.city = %s)         -- optional
      AND (f.arrival_airport = %s OR aa.city = %s)           -- optional
ORDER BY f.departure_time
```

### 2 & 3. Search for flights and purchase tickets — `GET /customer/search`, `POST /customer/purchase`
The search uses the same query as the public search. Each result row has a **Buy** button.
The purchase runs as one transaction (`purchase_ticket` in `queries.py`):
```sql
SELECT f.status, f.departure_time > NOW() AS in_future, ap.seats
FROM flight f JOIN airplane ap ON ap.id = f.airplane_id AND ap.airline_name = f.airline_name
WHERE f.airline_name = %s AND f.flight_num = %s
FOR UPDATE;                                   -- lock the flight row

SELECT COUNT(*) AS sold FROM ticket WHERE airline_name = %s AND flight_num = %s;

INSERT INTO ticket (airline_name, flight_num, customer_email, booking_agent_email, purchase_date)
VALUES (%s, %s, %s, NULL, NOW());
COMMIT;
```
The purchase is rejected, and the transaction rolled back, if the flight doesn't exist, has already departed, is cancelled or is full.

### 4. Track my spending — `GET /customer/spending`
By default the page shows the total for the past year and a bar chart of the last 6 months.
If the user enters a date range, both the total and the chart use that range.
```sql
SELECT COALESCE(SUM(f.price), 0) AS total, COUNT(*) AS tickets
FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
WHERE t.customer_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s;

SELECT DATE_FORMAT(t.purchase_date, '%Y-%m') AS ym, SUM(f.price) AS spent
FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
WHERE t.customer_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s
GROUP BY ym ORDER BY ym;
```
Python fills in 0 for months with no spending.

### 5. Logout — see above.

---

## Booking agent — `routes/agent.py`

Commission is `price × 0.10` (`COMMISSION_RATE`).

### Home — `GET /agent/`
```sql
SELECT booking_agent_id FROM booking_agent WHERE email = %s;
SELECT airline_name FROM booking_agent_works_for WHERE agent_email = %s ORDER BY airline_name;
... WHERE tk.booking_agent_email = %s AND f.departure_time > NOW()   -- upcoming flights I booked
```

### 1. View my flights — `GET /agent/flights`
This is the same as the customer version, but filtered by `tk.booking_agent_email = %s`. It also has an optional customer email filter (`AND tk.customer_email = %s`).

### 2 & 3. Search and purchase for a customer — `GET /agent/search`, `POST /agent/purchase`
The search only shows airlines the agent works for:
```sql
FLIGHT_SELECT WHERE f.departure_time > NOW() ... AND f.airline_name IN (%s, %s, ...)
```
When the agent buys, the server checks again:
```sql
SELECT airline_name FROM booking_agent_works_for WHERE agent_email = %s;   -- must include the flight's airline
SELECT 1 FROM customer WHERE email = %s;                                   -- customer must exist
```
Then it runs the same purchase transaction as for customers, with `booking_agent_email = me`.

### 4. View my commission — `GET /agent/commission`
Shows the past 30 days by default, or a date range the user enters.
```sql
SELECT COUNT(*) AS tickets, COALESCE(SUM(f.price), 0) * 0.10 AS commission
FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
WHERE t.booking_agent_email = %s AND t.purchase_date >= %s AND t.purchase_date < %s
```
Average commission per ticket = commission / tickets (computed in Python).

### 5. View top customers — `GET /agent/top-customers`
```sql
-- top 5 by tickets, past 6 months
SELECT t.customer_email, c.name, COUNT(*) AS tickets
FROM ticket t JOIN customer c ON c.email = t.customer_email
WHERE t.booking_agent_email = %s AND t.purchase_date >= NOW() - INTERVAL 6 MONTH
GROUP BY t.customer_email, c.name ORDER BY tickets DESC LIMIT 5;

-- top 5 by commission, past year
SELECT t.customer_email, c.name, SUM(f.price) * 0.10 AS commission
FROM ticket t
JOIN flight f   ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
JOIN customer c ON c.email = t.customer_email
WHERE t.booking_agent_email = %s AND t.purchase_date >= NOW() - INTERVAL 1 YEAR
GROUP BY t.customer_email, c.name ORDER BY commission DESC LIMIT 5;
```
Each list is shown as a bar chart and a table.

### 6. Logout — see above.

---

## Airline staff — `routes/staff.py`

Permission checks run on every request, including POSTs:
```sql
SELECT 1 FROM staff_permission WHERE username = %s AND permission = %s   -- 'Admin' or 'Operator'
```

### Home — `GET /staff/`
```sql
SELECT username, first_name, last_name, airline_name FROM airline_staff WHERE username = %s;
SELECT permission FROM staff_permission WHERE username = %s ORDER BY permission;
```
Links to Admin-only pages are only shown to Admins. The server checks the permission again on each request.

### 1. View my flights — `GET /staff/flights`, `GET /staff/flights/<num>/customers`
By default the page shows the next 30 days:
```sql
FLIGHT_SELECT WHERE f.airline_name = %s
  AND f.departure_time BETWEEN NOW() AND NOW() + INTERVAL 30 DAY ORDER BY f.departure_time
```
With filters it can show past, current and future flights: `WHERE f.airline_name = %s` plus an optional date range, source and destination (the same conditions as above).

Customers on a flight (the flight must belong to `my_airline`):
```sql
SELECT t.ticket_id, c.email, c.name, c.phone_number, t.booking_agent_email, t.purchase_date
FROM ticket t JOIN customer c ON c.email = t.customer_email
WHERE t.airline_name = %s AND t.flight_num = %s ORDER BY c.name
```

### 2. Create new flights (Admin) — `GET/POST /staff/flights/create`
Validation: arrival is after departure, the two airports differ, the airplane belongs to `my_airline`, the airports exist and the flight number is not already used.
```sql
SELECT 1 FROM airplane WHERE id = %s AND airline_name = %s;
SELECT 1 FROM airport WHERE name = %s;
SELECT 1 FROM flight WHERE airline_name = %s AND flight_num = %s;
INSERT INTO flight (flight_num, airline_name, departure_time, arrival_time, price, status,
                    airplane_id, departure_airport, arrival_airport)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
```
The page also lists the next 30 days of flights (same query as use case 1) and fills the drop-downs from `airport` and `airplane WHERE airline_name = my_airline`.

### 3. Change status of flights (Operator) — `GET/POST /staff/flights/status`
```sql
UPDATE flight SET status = %s WHERE airline_name = %s AND flight_num = %s
```
`airline_name` is always `my_airline`, so staff cannot change another airline's flights. The status must be one of `Upcoming`, `In Progress`, `Delayed`, `Arrived` or `Cancelled`.
The drop-down lists flights departing from 7 days ago onward.

### 4. Add airplane (Admin) — `GET/POST /staff/airplanes`
```sql
SELECT 1 FROM airplane WHERE id = %s AND airline_name = %s;          -- duplicate check
INSERT INTO airplane (id, airline_name, seats) VALUES (%s, %s, %s);
SELECT id, seats FROM airplane WHERE airline_name = %s ORDER BY id;  -- confirmation: all my airline's airplanes
```

### 5. Add new airport (Admin) — `GET/POST /staff/airports`
```sql
SELECT 1 FROM airport WHERE name = %s;
INSERT INTO airport (name, city) VALUES (%s, %s);
SELECT name, city FROM airport ORDER BY city, name;
```

### 6. View all the booking agents — `GET /staff/agents`
This only counts tickets for `my_airline`.
```sql
-- top 5 by tickets, past month (and again with INTERVAL 1 YEAR for the past year)
SELECT t.booking_agent_email AS email, b.booking_agent_id, COUNT(*) AS tickets
FROM ticket t JOIN booking_agent b ON b.email = t.booking_agent_email
WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL 1 MONTH
GROUP BY t.booking_agent_email, b.booking_agent_id ORDER BY tickets DESC LIMIT 5;

-- top 5 by commission, past year
SELECT t.booking_agent_email AS email, b.booking_agent_id, SUM(f.price) * 0.10 AS commission
FROM ticket t
JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
JOIN booking_agent b ON b.email = t.booking_agent_email
WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL 1 YEAR
GROUP BY t.booking_agent_email, b.booking_agent_id ORDER BY commission DESC LIMIT 5;
```

### 7. View frequent customers — `GET /staff/customers`
Most frequent customer = most flights taken on `my_airline` that departed in the last year. If several customers tie, all of them are shown. The page also shows the top 5.
```sql
SELECT c.email, c.name, COUNT(*) AS flights
FROM ticket t
JOIN flight f   ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
JOIN customer c ON c.email = t.customer_email
WHERE t.airline_name = %s AND f.departure_time BETWEEN NOW() - INTERVAL 1 YEAR AND NOW()
GROUP BY c.email, c.name ORDER BY flights DESC LIMIT 5;
```
All flights a particular customer has taken on this airline (`?email=`):
```sql
FLIGHT_SELECT (joined with ticket t) WHERE t.airline_name = %s AND t.customer_email = %s ORDER BY f.departure_time
```

### 8. View reports — `GET /staff/reports`
Tickets sold to `my_airline` customers in a date range. The default is the last year. There are quick buttons for "Last month" and "Last year", and the page has a month-by-month bar chart.
```sql
SELECT COUNT(*) AS tickets FROM ticket
WHERE airline_name = %s AND purchase_date >= %s AND purchase_date < %s;

SELECT DATE_FORMAT(purchase_date, '%Y-%m') AS ym, COUNT(*) AS tickets
FROM ticket WHERE airline_name = %s AND purchase_date >= %s AND purchase_date < %s
GROUP BY ym ORDER BY ym;
```

### 9. Comparison of revenue earned — `GET /staff/revenue`
Direct sales have `booking_agent_email IS NULL`. Indirect sales were made through an agent. The query runs once for the last month and once for the last year, and each result is shown as a pie chart.
```sql
SELECT COALESCE(SUM(CASE WHEN t.booking_agent_email IS NULL     THEN f.price END), 0) AS direct,
       COALESCE(SUM(CASE WHEN t.booking_agent_email IS NOT NULL THEN f.price END), 0) AS indirect
FROM ticket t JOIN flight f ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
WHERE t.airline_name = %s AND t.purchase_date >= NOW() - INTERVAL 1 MONTH   -- or 1 YEAR
```

### 10. View top destinations — `GET /staff/destinations`
The top 3 arrival cities, ranked by tickets on `my_airline` flights that departed in the last 3 months, and again for the last year:
```sql
SELECT aa.city, COUNT(*) AS tickets
FROM ticket t
JOIN flight f   ON f.airline_name = t.airline_name AND f.flight_num = t.flight_num
JOIN airport aa ON aa.name = f.arrival_airport
WHERE t.airline_name = %s AND f.departure_time BETWEEN NOW() - INTERVAL 3 MONTH AND NOW()
GROUP BY aa.city ORDER BY tickets DESC LIMIT 3
```

### 11. Grant new permissions (Admin) — `GET/POST /staff/permissions`
The target must be on the same airline, and duplicate grants are rejected.
```sql
SELECT airline_name FROM airline_staff WHERE username = %s;   -- must equal my_airline
SELECT 1 FROM staff_permission WHERE username = %s AND permission = %s;
INSERT INTO staff_permission (username, permission) VALUES (%s, %s);

-- staff list with their current permissions
SELECT s.username, s.first_name, s.last_name,
       GROUP_CONCAT(p.permission ORDER BY p.permission SEPARATOR ', ') AS permissions
FROM airline_staff s LEFT JOIN staff_permission p ON p.username = s.username
WHERE s.airline_name = %s GROUP BY s.username, s.first_name, s.last_name ORDER BY s.username;
```

### 12. Add booking agents (Admin) — `GET/POST /staff/agents/add`
```sql
SELECT 1 FROM booking_agent WHERE email = %s;                                         -- must be registered
SELECT 1 FROM booking_agent_works_for WHERE agent_email = %s AND airline_name = %s;   -- not already added
INSERT INTO booking_agent_works_for (agent_email, airline_name) VALUES (%s, %s);

SELECT b.email, b.booking_agent_id FROM booking_agent_works_for w
JOIN booking_agent b ON b.email = w.agent_email WHERE w.airline_name = %s ORDER BY b.email;
```

### 13. Logout — see above.
