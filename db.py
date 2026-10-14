import logging
import re
import time

import oracledb

import config

log = logging.getLogger("cibil.db")
oracledb.defaults.fetch_lobs = False

CUSTOMER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
MOBILE_RE = re.compile(r"^\+?\d{10,15}$")
MAX_SUMMARY_CHARS = 2000

_pool = None

_BASE_SQL = """
SELECT * FROM (
    SELECT c.CUSTOMER_ID, c.CUSTOMER_NAME, c.MOBILE_NUMBER, c.MONTHLY_INCOME,
           r.REPORT_ID, r.CIBIL_SCORE, r.CC_UTILIZATION_RATE,
           r.RECENT_INQUIRIES_30_DAYS, r.HAS_SERIOUS_DELINQUENCY,
           r.RAW_BUREAU_SUMMARY, r.LAST_UPDATED_DATE
      FROM VAG_CUSTOMER_MASTER c
      LEFT JOIN VAG_CIBIL_REPORTS r ON r.CUSTOMER_ID = c.CUSTOMER_ID
     WHERE {where}
     ORDER BY r.LAST_UPDATED_DATE DESC NULLS LAST
) WHERE ROWNUM = 1
"""


def _get_pool():
    global _pool
    if _pool is None:
        log.info("Creating Oracle connection pool for user %s", config.ORACLE_USER)
        _pool = oracledb.create_pool(
            user=config.ORACLE_USER,
            password=config.ORACLE_PASSWORD,
            dsn=config.ORACLE_DSN,
            min=1,
            max=4,
            increment=1,
        )
    return _pool


def _fetch_one(where: str, binds: dict) -> dict | None:
    start = time.perf_counter()
    with _get_pool().acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(_BASE_SQL.format(where=where), binds)
            row = cur.fetchone()
            log.info("Query [%s] found=%s in %.0f ms", where, row is not None, (time.perf_counter() - start) * 1000)
            if row is None:
                return None
            cols = [d[0] for d in cur.description]
    record = dict(zip(cols, row))
    summary = record.get("RAW_BUREAU_SUMMARY")
    if summary and len(summary) > MAX_SUMMARY_CHARS:
        record["RAW_BUREAU_SUMMARY"] = summary[:MAX_SUMMARY_CHARS] + "..."
    if record.get("LAST_UPDATED_DATE"):
        record["LAST_UPDATED_DATE"] = record["LAST_UPDATED_DATE"].strftime("%Y-%m-%d")
    return record


def fetch_by_customer_id(customer_id: str) -> dict | None:
    customer_id = customer_id.strip()
    if not CUSTOMER_ID_RE.fullmatch(customer_id):
        raise ValueError("Invalid customer ID format.")
    return _fetch_one("c.CUSTOMER_ID = :cid", {"cid": customer_id})


def fetch_by_mobile(mobile: str) -> dict | None:
    mobile = re.sub(r"[\s-]", "", mobile)
    if not MOBILE_RE.fullmatch(mobile):
        raise ValueError("Invalid mobile number format.")
    return _fetch_one("c.MOBILE_NUMBER = :mobile", {"mobile": mobile})


def check_connection() -> bool:
    try:
        with _get_pool().acquire() as conn:
            conn.ping()
        return True
    except Exception:
        log.exception("Oracle connection check failed")
        return False


if __name__ == "__main__":
    import sys

    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    print("Connected:", check_connection())
    if arg:
        print(fetch_by_mobile(arg) if arg.lstrip("+").isdigit() and len(arg) >= 10 else fetch_by_customer_id(arg))
