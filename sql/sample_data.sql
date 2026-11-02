-- Sample data for the Air Ticket Reservation System.
-- All dates are relative to the moment the script is run (NOW()/CURDATE()),
-- so there are always past flights (for reports) and upcoming flights (for searching/buying).
--
-- Every account's password is:  password   (stored as MD5)
--
--   Airline staff:   ce_admin    (China Eastern, Admin + Operator)
--                    ce_operator (China Eastern, Operator)
--                    ce_staff    (China Eastern, no permissions)
--                    ca_admin    (Air China, Admin + Operator)
--                    dl_admin    (Delta, Admin + Operator)
--   Booking agents:  agent1@example.com (works for China Eastern, Air China)
--                    agent2@example.com (works for Delta)
--                    agent3@example.com (works for no airline yet)
--   Customers:       alice@example.com, bob@example.com, carol@example.com,
--                    david@example.com, emma@example.com, frank@example.com
--
-- China Eastern flight 205 uses airplane 3, which only has 3 seats and is already full
-- (handy for testing the "sold out" check).

USE air_ticket;

INSERT INTO airline (name) VALUES ('China Eastern'), ('Air China'), ('Delta');

INSERT INTO airport (name, city) VALUES
    ('PVG', 'Shanghai'), ('SHA', 'Shanghai'), ('PEK', 'Beijing'),
    ('CAN', 'Guangzhou'), ('JFK', 'New York'), ('LAX', 'Los Angeles');

INSERT INTO airline_staff (username, password, first_name, last_name, date_of_birth, airline_name) VALUES
    ('ce_admin',    MD5('password'), 'Li',    'Wei',    '1985-03-14', 'China Eastern'),
    ('ce_operator', MD5('password'), 'Zhang', 'Min',    '1990-07-02', 'China Eastern'),
    ('ce_staff',    MD5('password'), 'Chen',  'Jing',   '1995-11-20', 'China Eastern'),
    ('ca_admin',    MD5('password'), 'Wang',  'Fang',   '1982-01-30', 'Air China'),
    ('dl_admin',    MD5('password'), 'John',  'Smith',  '1979-05-09', 'Delta');

INSERT INTO staff_permission (username, permission) VALUES
    ('ce_admin', 'Admin'), ('ce_admin', 'Operator'),
    ('ce_operator', 'Operator'),
    ('ca_admin', 'Admin'), ('ca_admin', 'Operator'),
    ('dl_admin', 'Admin'), ('dl_admin', 'Operator');

INSERT INTO airplane (id, airline_name, seats) VALUES
    (1, 'China Eastern', 180), (2, 'China Eastern', 250), (3, 'China Eastern', 3),
    (1, 'Air China', 200), (2, 'Air China', 300),
    (1, 'Delta', 220);

INSERT INTO booking_agent (email, password, booking_agent_id) VALUES
    ('agent1@example.com', MD5('password'), 1001),
    ('agent2@example.com', MD5('password'), 1002),
    ('agent3@example.com', MD5('password'), 1003);

INSERT INTO booking_agent_works_for (agent_email, airline_name) VALUES
    ('agent1@example.com', 'China Eastern'),
    ('agent1@example.com', 'Air China'),
    ('agent2@example.com', 'Delta');

INSERT INTO customer (email, name, password, building_number, street, city, state, phone_number,
                      passport_number, passport_expiration, passport_country, date_of_birth) VALUES
    ('alice@example.com', 'Alice Wang',   MD5('password'), '1555', 'Century Ave',   'Shanghai',  'Shanghai', '13800000001', 'E10000001', '2030-06-30', 'China',  '1998-04-12'),
    ('bob@example.com',   'Bob Lee',      MD5('password'), '20',   'Nanjing Rd',    'Shanghai',  'Shanghai', '13800000002', 'E10000002', '2029-01-15', 'China',  '1996-09-03'),
    ('carol@example.com', 'Carol Zhou',   MD5('password'), '8',    'Chang An Ave',  'Beijing',   'Beijing',  '13800000003', 'E10000003', '2031-03-01', 'China',  '2000-12-25'),
    ('david@example.com', 'David Brown',  MD5('password'), '370',  'Jay St',        'Brooklyn',  'NY',       '2125550104',  'P20000004', '2028-08-08', 'USA',    '1992-02-29'),
    ('emma@example.com',  'Emma Garcia',  MD5('password'), '45',   'Sunset Blvd',   'Los Angeles','CA',      '3105550105',  'P20000005', '2032-10-10', 'USA',    '1999-06-18'),
    ('frank@example.com', 'Frank Liu',    MD5('password'), '99',   'Tianhe Rd',     'Guangzhou', 'Guangdong','13800000006', 'E10000006', '2027-12-31', 'China',  '1988-03-07');

INSERT INTO flight (airline_name, flight_num, departure_time, arrival_time, price, status, airplane_id, departure_airport, arrival_airport) VALUES
    ('China Eastern', 101, TIMESTAMP(CURDATE() + INTERVAL -300 DAY, '08:30:00'), TIMESTAMP(CURDATE() + INTERVAL -300 DAY, '08:30:00') + INTERVAL 2 HOUR, 800, 'Arrived', 1, 'PVG', 'PEK'),
    ('China Eastern', 102, TIMESTAMP(CURDATE() + INTERVAL -200 DAY, '14:00:00'), TIMESTAMP(CURDATE() + INTERVAL -200 DAY, '14:00:00') + INTERVAL 2 HOUR, 900, 'Arrived', 1, 'PEK', 'PVG'),
    ('China Eastern', 103, TIMESTAMP(CURDATE() + INTERVAL -150 DAY, '10:15:00'), TIMESTAMP(CURDATE() + INTERVAL -150 DAY, '10:15:00') + INTERVAL 14 HOUR, 6000, 'Arrived', 2, 'PVG', 'JFK'),
    ('China Eastern', 104, TIMESTAMP(CURDATE() + INTERVAL -100 DAY, '07:45:00'), TIMESTAMP(CURDATE() + INTERVAL -100 DAY, '07:45:00') + INTERVAL 3 HOUR, 700, 'Arrived', 1, 'PVG', 'CAN'),
    ('China Eastern', 105, TIMESTAMP(CURDATE() + INTERVAL -60 DAY, '18:20:00'), TIMESTAMP(CURDATE() + INTERVAL -60 DAY, '18:20:00') + INTERVAL 2 HOUR, 750, 'Arrived', 1, 'SHA', 'PEK'),
    ('China Eastern', 106, TIMESTAMP(CURDATE() + INTERVAL -20 DAY, '13:00:00'), TIMESTAMP(CURDATE() + INTERVAL -20 DAY, '13:00:00') + INTERVAL 12 HOUR, 5500, 'Arrived', 2, 'PVG', 'LAX'),
    ('China Eastern', 107, TIMESTAMP(CURDATE() + INTERVAL -5 DAY, '09:10:00'), TIMESTAMP(CURDATE() + INTERVAL -5 DAY, '09:10:00') + INTERVAL 2 HOUR, 820, 'Arrived', 1, 'PVG', 'PEK'),
    ('China Eastern', 201, TIMESTAMP(CURDATE() + INTERVAL 3 DAY, '08:30:00'), TIMESTAMP(CURDATE() + INTERVAL 3 DAY, '08:30:00') + INTERVAL 2 HOUR, 850, 'Upcoming', 1, 'PVG', 'PEK'),
    ('China Eastern', 202, TIMESTAMP(CURDATE() + INTERVAL 10 DAY, '16:40:00'), TIMESTAMP(CURDATE() + INTERVAL 10 DAY, '16:40:00') + INTERVAL 2 HOUR, 880, 'Delayed', 1, 'PEK', 'PVG'),
    ('China Eastern', 203, TIMESTAMP(CURDATE() + INTERVAL 20 DAY, '11:00:00'), TIMESTAMP(CURDATE() + INTERVAL 20 DAY, '11:00:00') + INTERVAL 14 HOUR, 6200, 'Upcoming', 2, 'PVG', 'JFK'),
    ('China Eastern', 204, TIMESTAMP(CURDATE() + INTERVAL 45 DAY, '12:30:00'), TIMESTAMP(CURDATE() + INTERVAL 45 DAY, '12:30:00') + INTERVAL 3 HOUR, 650, 'Upcoming', 1, 'SHA', 'CAN'),
    ('China Eastern', 205, TIMESTAMP(CURDATE() + INTERVAL 2 DAY, '22:00:00'), TIMESTAMP(CURDATE() + INTERVAL 2 DAY, '22:00:00') + INTERVAL 12 HOUR, 5000, 'Upcoming', 3, 'PVG', 'LAX'),
    ('Air China', 301, TIMESTAMP(CURDATE() + INTERVAL -120 DAY, '09:00:00'), TIMESTAMP(CURDATE() + INTERVAL -120 DAY, '09:00:00') + INTERVAL 13 HOUR, 5800, 'Arrived', 1, 'PEK', 'JFK'),
    ('Air China', 302, TIMESTAMP(CURDATE() + INTERVAL -40 DAY, '15:30:00'), TIMESTAMP(CURDATE() + INTERVAL -40 DAY, '15:30:00') + INTERVAL 2 HOUR, 780, 'Arrived', 1, 'PEK', 'PVG'),
    ('Air China', 401, TIMESTAMP(CURDATE() + INTERVAL 5 DAY, '07:00:00'), TIMESTAMP(CURDATE() + INTERVAL 5 DAY, '07:00:00') + INTERVAL 2 HOUR, 800, 'Upcoming', 1, 'PEK', 'PVG'),
    ('Air China', 402, TIMESTAMP(CURDATE() + INTERVAL 15 DAY, '13:45:00'), TIMESTAMP(CURDATE() + INTERVAL 15 DAY, '13:45:00') + INTERVAL 12 HOUR, 5300, 'Upcoming', 2, 'PEK', 'LAX'),
    ('Air China', 403, TIMESTAMP(CURDATE() + INTERVAL 60 DAY, '10:20:00'), TIMESTAMP(CURDATE() + INTERVAL 60 DAY, '10:20:00') + INTERVAL 3 HOUR, 690, 'Upcoming', 1, 'PVG', 'CAN'),
    ('Delta', 501, TIMESTAMP(CURDATE() + INTERVAL -90 DAY, '12:00:00'), TIMESTAMP(CURDATE() + INTERVAL -90 DAY, '12:00:00') + INTERVAL 15 HOUR, 6100, 'Arrived', 1, 'JFK', 'PVG'),
    ('Delta', 502, TIMESTAMP(CURDATE() + INTERVAL -10 DAY, '23:30:00'), TIMESTAMP(CURDATE() + INTERVAL -10 DAY, '23:30:00') + INTERVAL 13 HOUR, 5400, 'Arrived', 1, 'LAX', 'PEK'),
    ('Delta', 601, TIMESTAMP(CURDATE() + INTERVAL 7 DAY, '12:00:00'), TIMESTAMP(CURDATE() + INTERVAL 7 DAY, '12:00:00') + INTERVAL 15 HOUR, 6300, 'Upcoming', 1, 'JFK', 'PVG'),
    ('Delta', 602, TIMESTAMP(CURDATE() + INTERVAL 25 DAY, '08:00:00'), TIMESTAMP(CURDATE() + INTERVAL 25 DAY, '08:00:00') + INTERVAL 6 HOUR, 450, 'Upcoming', 1, 'JFK', 'LAX');

INSERT INTO ticket (airline_name, flight_num, customer_email, booking_agent_email, purchase_date) VALUES
    ('China Eastern', 101, 'alice@example.com', NULL, NOW() - INTERVAL 310 DAY - INTERVAL 0 MINUTE),
    ('China Eastern', 101, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 320 DAY - INTERVAL 37 MINUTE),
    ('China Eastern', 101, 'carol@example.com', 'agent1@example.com', NOW() - INTERVAL 305 DAY - INTERVAL 74 MINUTE),
    ('China Eastern', 102, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 210 DAY - INTERVAL 111 MINUTE),
    ('China Eastern', 102, 'david@example.com', NULL, NOW() - INTERVAL 205 DAY - INTERVAL 148 MINUTE),
    ('China Eastern', 103, 'alice@example.com', NULL, NOW() - INTERVAL 160 DAY - INTERVAL 185 MINUTE),
    ('China Eastern', 103, 'emma@example.com', 'agent1@example.com', NOW() - INTERVAL 170 DAY - INTERVAL 222 MINUTE),
    ('China Eastern', 103, 'frank@example.com', 'agent1@example.com', NOW() - INTERVAL 155 DAY - INTERVAL 259 MINUTE),
    ('China Eastern', 103, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 152 DAY - INTERVAL 296 MINUTE),
    ('China Eastern', 104, 'carol@example.com', NULL, NOW() - INTERVAL 110 DAY - INTERVAL 333 MINUTE),
    ('China Eastern', 104, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 105 DAY - INTERVAL 370 MINUTE),
    ('China Eastern', 105, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 70 DAY - INTERVAL 407 MINUTE),
    ('China Eastern', 105, 'david@example.com', 'agent1@example.com', NOW() - INTERVAL 65 DAY - INTERVAL 444 MINUTE),
    ('China Eastern', 105, 'alice@example.com', NULL, NOW() - INTERVAL 62 DAY - INTERVAL 481 MINUTE),
    ('China Eastern', 106, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 29 DAY - INTERVAL 518 MINUTE),
    ('China Eastern', 106, 'emma@example.com', NULL, NOW() - INTERVAL 25 DAY - INTERVAL 555 MINUTE),
    ('China Eastern', 106, 'carol@example.com', 'agent1@example.com', NOW() - INTERVAL 22 DAY - INTERVAL 592 MINUTE),
    ('China Eastern', 107, 'bob@example.com', NULL, NOW() - INTERVAL 12 DAY - INTERVAL 29 MINUTE),
    ('China Eastern', 107, 'frank@example.com', 'agent1@example.com', NOW() - INTERVAL 8 DAY - INTERVAL 66 MINUTE),
    ('China Eastern', 107, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 6 DAY - INTERVAL 103 MINUTE),
    ('China Eastern', 201, 'alice@example.com', NULL, NOW() - INTERVAL 2 DAY - INTERVAL 140 MINUTE),
    ('China Eastern', 201, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 1 DAY - INTERVAL 177 MINUTE),
    ('China Eastern', 201, 'carol@example.com', 'agent1@example.com', NOW() - INTERVAL 3 DAY - INTERVAL 214 MINUTE),
    ('China Eastern', 202, 'david@example.com', 'agent1@example.com', NOW() - INTERVAL 4 DAY - INTERVAL 251 MINUTE),
    ('China Eastern', 202, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 10 DAY - INTERVAL 288 MINUTE),
    ('China Eastern', 203, 'emma@example.com', NULL, NOW() - INTERVAL 7 DAY - INTERVAL 325 MINUTE),
    ('China Eastern', 205, 'alice@example.com', NULL, NOW() - INTERVAL 1 DAY - INTERVAL 362 MINUTE),
    ('China Eastern', 205, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 1 DAY - INTERVAL 399 MINUTE),
    ('China Eastern', 205, 'carol@example.com', 'agent1@example.com', NOW() - INTERVAL 2 DAY - INTERVAL 436 MINUTE),
    ('Air China', 301, 'alice@example.com', 'agent1@example.com', NOW() - INTERVAL 130 DAY - INTERVAL 473 MINUTE),
    ('Air China', 301, 'frank@example.com', NULL, NOW() - INTERVAL 125 DAY - INTERVAL 510 MINUTE),
    ('Air China', 302, 'bob@example.com', 'agent1@example.com', NOW() - INTERVAL 45 DAY - INTERVAL 547 MINUTE),
    ('Air China', 302, 'emma@example.com', 'agent1@example.com', NOW() - INTERVAL 42 DAY - INTERVAL 584 MINUTE),
    ('Air China', 401, 'carol@example.com', 'agent1@example.com', NOW() - INTERVAL 9 DAY - INTERVAL 21 MINUTE),
    ('Air China', 401, 'alice@example.com', NULL, NOW() - INTERVAL 3 DAY - INTERVAL 58 MINUTE),
    ('Air China', 402, 'david@example.com', NULL, NOW() - INTERVAL 14 DAY - INTERVAL 95 MINUTE),
    ('Delta', 501, 'alice@example.com', 'agent2@example.com', NOW() - INTERVAL 95 DAY - INTERVAL 132 MINUTE),
    ('Delta', 501, 'bob@example.com', NULL, NOW() - INTERVAL 100 DAY - INTERVAL 169 MINUTE),
    ('Delta', 502, 'emma@example.com', 'agent2@example.com', NOW() - INTERVAL 15 DAY - INTERVAL 206 MINUTE),
    ('Delta', 502, 'frank@example.com', 'agent2@example.com', NOW() - INTERVAL 14 DAY - INTERVAL 243 MINUTE),
    ('Delta', 601, 'carol@example.com', 'agent2@example.com', NOW() - INTERVAL 5 DAY - INTERVAL 280 MINUTE);
