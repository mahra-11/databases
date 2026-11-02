"""Application settings. Override any of them with environment variables."""
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "air_ticket")

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-air-ticket-secret")

# Booking agents earn a fixed commission of 10% of the ticket price.
COMMISSION_RATE = 0.10

# Values staff can choose from when changing a flight's status.
FLIGHT_STATUSES = ["Upcoming", "In Progress", "Delayed", "Arrived", "Cancelled"]

STAFF_PERMISSIONS = ["Admin", "Operator"]
