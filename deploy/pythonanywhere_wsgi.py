# WSGI file for hosting on PythonAnywhere.
#
# Copy this into the WSGI file PythonAnywhere creates for your web app
# (Web tab -> "WSGI configuration file"), then replace YOUR_USERNAME,
# YOUR_MYSQL_PASSWORD and the secret key. Do NOT commit the real values.
import os
import sys

USERNAME = "YOUR_USERNAME"
PROJECT_DIR = "/home/%s/databases" % USERNAME

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ["DB_HOST"] = "%s.mysql.pythonanywhere-services.com" % USERNAME
os.environ["DB_USER"] = USERNAME
os.environ["DB_PASSWORD"] = "YOUR_MYSQL_PASSWORD"
os.environ["DB_NAME"] = "%s$air_ticket" % USERNAME
# Any long random string; it signs the login cookies.
os.environ["SECRET_KEY"] = "REPLACE_WITH_A_LONG_RANDOM_STRING"

from app import app as application  # noqa: E402
