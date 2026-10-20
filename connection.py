import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# =====================================================================
# 1. ENVIRONMENT & PATH INITIALIZATION
# =====================================================================
# Force Python to look in the TRUE project root directory for the .env file
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# 2. WINDOWS DLL FIX: Force Python & Windows to find the Firebird Client Library
dll_dir = root_dir / "config"
dll_path = dll_dir / "fbclient.dll"

# Inject the folder path straight into the Windows runtime execution paths
os.environ["PATH"] = str(dll_dir) + os.path.pathsep + os.environ.get("PATH", "")
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(str(dll_dir))
    except Exception:
        pass

# =====================================================================
# 3. GET ENVIRONMENT VARIABLES WITH GUARANTEED FALLBACKS
# =====================================================================
# Firebird Configuration
FIREBIRD_USER = os.getenv("FIREBIRD_USER")
FIREBIRD_PASSWORD = os.getenv("FIREBIRD_PASSWORD")
FIREBIRD_HOST = os.getenv("FIREBIRD_HOST")
FIREBIRD_PORT = os.getenv("FIREBIRD_PORT")
DATABASE_PATH = os.getenv("DATABASE_PATH")

# PostgreSQL Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")


# =====================================================================
# 4. ENGINE CREATION FUNCTIONS
# =====================================================================
def get_firebird_engine():
    """Creates and returns a SQLAlchemy engine for Firebird."""
    clean_path = DATABASE_PATH.strip("'\"") if DATABASE_PATH else ""

    # Format: firebird+firebird://user:pass@host:port/database_path
    connection_string = (
        # f"firebird+fdb://{FIREBIRD_USER}:{FIREBIRD_PASSWORD}@"
        # f"{FIREBIRD_HOST}:{FIREBIRD_PORT}/{clean_path}?charset=UTF8"
        f"firebird://{FIREBIRD_USER}:{FIREBIRD_PASSWORD}@{FIREBIRD_HOST}:{FIREBIRD_PORT}/{clean_path}?charset=UTF8"
    )
    return create_engine(connection_string, pool_pre_ping=True)


def get_postgres_engine():
    """Creates and returns a SQLAlchemy engine for PostgreSQL."""
    # Format: postgresql+psycopg2://user:pass@host:port/database_name
    connection_string = (
        # f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        # f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=prefer"
    )
    return create_engine(connection_string, pool_pre_ping=True)


def test_connection(engine, name="Database"):
    """Helper utility to safely test database connection vitality."""
    try:
        with engine.connect() as conn:
            print(f"✅ successfully connected to {name}!")
            return True
    except Exception as e:
        print(f"❌ Failed to connect to {name}: {e}")
        return False


# =====================================================================
# 5. INITIALIZE INDEPENDENT ECOSYSTEMS
# =====================================================================
# Firebird Ecosystem Setup
fb_engine = get_firebird_engine()
FbSession = sessionmaker(bind=fb_engine)

# PostgreSQL Ecosystem Setup
pg_engine = get_postgres_engine()
PgSession = sessionmaker(bind=pg_engine)

# Shared Declarative Base for ORM Mapping Models
Base = declarative_base()
