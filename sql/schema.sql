-- Air Ticket Reservation System - table definitions
-- Based on the posted Part 2 relational schema.
-- Additions (allowed by the Part 3 handout for additional features):
--   * ticket.purchase_date   - needed for spending / commission / report use cases
--   * ticket.ticket_id is AUTO_INCREMENT so the application can create tickets
--   * booking_agent.booking_agent_id is UNIQUE
--   * CHECK constraints on a few columns (permission values, seats, price)

CREATE DATABASE IF NOT EXISTS air_ticket;
USE air_ticket;

DROP TABLE IF EXISTS ticket;
DROP TABLE IF EXISTS booking_agent_works_for;
DROP TABLE IF EXISTS flight;
DROP TABLE IF EXISTS airplane;
DROP TABLE IF EXISTS staff_permission;
DROP TABLE IF EXISTS airline_staff;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS booking_agent;
DROP TABLE IF EXISTS airport;
DROP TABLE IF EXISTS airline;

CREATE TABLE airline (
    name VARCHAR(50) NOT NULL,
    PRIMARY KEY (name)
);

CREATE TABLE airport (
    name VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    PRIMARY KEY (name)
);

CREATE TABLE airline_staff (
    username      VARCHAR(50)  NOT NULL,
    password      VARCHAR(50)  NOT NULL,   -- md5 hex digest
    first_name    VARCHAR(50)  NOT NULL,
    last_name     VARCHAR(50)  NOT NULL,
    date_of_birth DATE         NOT NULL,
    airline_name  VARCHAR(50)  NOT NULL,
    PRIMARY KEY (username),
    FOREIGN KEY (airline_name) REFERENCES airline(name)
);

CREATE TABLE staff_permission (
    username   VARCHAR(50) NOT NULL,
    permission VARCHAR(20) NOT NULL,
    PRIMARY KEY (username, permission),
    FOREIGN KEY (username) REFERENCES airline_staff(username) ON DELETE CASCADE,
    CHECK (permission IN ('Admin', 'Operator'))
);

CREATE TABLE airplane (
    id           INT         NOT NULL,
    airline_name VARCHAR(50) NOT NULL,
    seats        INT         NOT NULL,
    PRIMARY KEY (id, airline_name),
    FOREIGN KEY (airline_name) REFERENCES airline(name),
    CHECK (seats > 0)
);

CREATE TABLE flight (
    flight_num        INT            NOT NULL,
    airline_name      VARCHAR(50)    NOT NULL,
    departure_time    DATETIME       NOT NULL,
    arrival_time      DATETIME       NOT NULL,
    price             DECIMAL(10, 2) NOT NULL,
    status            VARCHAR(20)    NOT NULL DEFAULT 'Upcoming',
    airplane_id       INT            NOT NULL,
    departure_airport VARCHAR(50)    NOT NULL,
    arrival_airport   VARCHAR(50)    NOT NULL,
    PRIMARY KEY (flight_num, airline_name),
    FOREIGN KEY (airline_name) REFERENCES airline(name),
    FOREIGN KEY (airplane_id, airline_name) REFERENCES airplane(id, airline_name),
    FOREIGN KEY (departure_airport) REFERENCES airport(name),
    FOREIGN KEY (arrival_airport) REFERENCES airport(name),
    CHECK (price >= 0)
);

CREATE TABLE booking_agent (
    email            VARCHAR(100) NOT NULL,
    password         VARCHAR(50)  NOT NULL,   -- md5 hex digest
    booking_agent_id INT          NOT NULL,
    PRIMARY KEY (email),
    UNIQUE (booking_agent_id)
);

CREATE TABLE booking_agent_works_for (
    agent_email  VARCHAR(100) NOT NULL,
    airline_name VARCHAR(50)  NOT NULL,
    PRIMARY KEY (agent_email, airline_name),
    FOREIGN KEY (agent_email) REFERENCES booking_agent(email),
    FOREIGN KEY (airline_name) REFERENCES airline(name)
);

CREATE TABLE customer (
    email               VARCHAR(100) NOT NULL,
    name                VARCHAR(100) NOT NULL,
    password            VARCHAR(50)  NOT NULL,   -- md5 hex digest
    building_number     VARCHAR(30)  NOT NULL,
    street              VARCHAR(50)  NOT NULL,
    city                VARCHAR(50)  NOT NULL,
    state               VARCHAR(50)  NOT NULL,
    phone_number        VARCHAR(20)  NOT NULL,
    passport_number     VARCHAR(30)  NOT NULL,
    passport_expiration DATE         NOT NULL,
    passport_country    VARCHAR(50)  NOT NULL,
    date_of_birth       DATE         NOT NULL,
    PRIMARY KEY (email)
);

CREATE TABLE ticket (
    ticket_id           INT          NOT NULL AUTO_INCREMENT,
    airline_name        VARCHAR(50)  NOT NULL,
    flight_num          INT          NOT NULL,
    customer_email      VARCHAR(100) NOT NULL,
    booking_agent_email VARCHAR(100) NULL,      -- NULL = bought directly by the customer
    purchase_date       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticket_id),
    FOREIGN KEY (flight_num, airline_name) REFERENCES flight(flight_num, airline_name),
    FOREIGN KEY (customer_email) REFERENCES customer(email),
    FOREIGN KEY (booking_agent_email) REFERENCES booking_agent(email)
);
