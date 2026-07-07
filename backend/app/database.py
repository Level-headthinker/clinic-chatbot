# Creates the connection to your PostgreSQL database and gives every
# part of the app a way to talk to it.
# Think of it as the bridge between your Python code and pgAdmin.
from urllib.parse import urlparse, parse_qs

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Make a hosted (Render/Supabase/etc.) Postgres URL safe to connect to.

    - SQLAlchemy 2.0 rejects the ``postgres://`` scheme some providers hand out;
      rewrite it to ``postgresql://``.
    - Managed Postgres requires SSL. If the host is remote and no sslmode is
      set, force ``sslmode=require`` — without it the server closes the TLS
      handshake ("SSL connection has been closed unexpectedly").
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    is_local = host in ("localhost", "127.0.0.1", "::1", "")
    has_sslmode = "sslmode" in parse_qs(parsed.query)
    if not is_local and not has_sslmode:
        sep = "&" if parsed.query else "?"
        url = f"{url}{sep}sslmode=require"
    return url


DATABASE_URL = _normalize_db_url(settings.DATABASE_URL)

# TCP keepalives keep the socket alive through Render's idle proxy so it doesn't
# get torn down mid-request; connect_timeout fails fast instead of hanging.
_is_remote = not any(h in DATABASE_URL for h in ("localhost", "127.0.0.1"))
_connect_args = {
    "connect_timeout": 10,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
} if _is_remote else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # probe connections before use — survives DB restarts/idle drops
    pool_recycle=1800,     # refresh connections older than 30 min (hosted PG idle timeouts)
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)# create session every api request get its own session


Base = declarative_base() #every database model (table) will inherit from this


def get_db(): #a function that opens a session, gives it to a route, then closes it automatically when done
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
