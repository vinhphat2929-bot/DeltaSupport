import os

import pyodbc

DEFAULT_DRIVER = "ODBC Driver 17 for SQL Server"
DEFAULT_SERVER = "localhost"
DEFAULT_DATABASE = "DeltaSupport"
DEFAULT_USERNAME = "delta_user"
DEFAULT_PASSWORD = "Delta@123456"

DRIVER_ENV_VAR = "DELTA_DB_DRIVER"
SERVER_ENV_VAR = "DELTA_DB_SERVER"
DATABASE_ENV_VAR = "DELTA_DB_NAME"
USERNAME_ENV_VAR = "DELTA_DB_USER"
PASSWORD_ENV_VAR = "DELTA_DB_PASSWORD"
TRUSTED_CONNECTION_ENV_VAR = "DELTA_DB_TRUSTED_CONNECTION"


def _env_or_default(name, default_value):
    value = os.getenv(name)
    if value is None:
        return default_value
    normalized = str(value).strip()
    return normalized if normalized else default_value


def _env_flag(name):
    value = str(os.getenv(name, "") or "").strip().lower()
    return value in {"1", "true", "yes", "y", "on"}


def get_database_config():
    return {
        "driver": _env_or_default(DRIVER_ENV_VAR, DEFAULT_DRIVER),
        "server": _env_or_default(SERVER_ENV_VAR, DEFAULT_SERVER),
        "database": _env_or_default(DATABASE_ENV_VAR, DEFAULT_DATABASE),
        "username": _env_or_default(USERNAME_ENV_VAR, DEFAULT_USERNAME),
        "password": _env_or_default(PASSWORD_ENV_VAR, DEFAULT_PASSWORD),
        "trusted_connection": _env_flag(TRUSTED_CONNECTION_ENV_VAR),
    }


def get_connection():
    config = get_database_config()
    connection_string = (
        f"DRIVER={{{config['driver']}}};"
        f"SERVER={config['server']};"
        f"DATABASE={config['database']};"
        "TrustServerCertificate=yes;"
    )
    if config["trusted_connection"]:
        connection_string += "Trusted_Connection=yes;"
    else:
        connection_string += f"UID={config['username']};PWD={config['password']};"
    return pyodbc.connect(connection_string)
