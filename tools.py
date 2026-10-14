import logging

from langchain_core.tools import tool

import db

log = logging.getLogger("cibil.tools")

LAST_RECORD: dict = {}


def format_record(record: dict | None) -> str:
    if record is None:
        return "No customer found for the given identifier."
    if record.get("REPORT_ID") is None:
        return (
            f"Customer found but no CIBIL report exists.\n"
            f"Customer ID: {record['CUSTOMER_ID']}\nName: {record['CUSTOMER_NAME']}\n"
            f"Mobile: {record['MOBILE_NUMBER']}\nMonthly Income: {record['MONTHLY_INCOME']}"
        )
    return "\n".join(f"{k}: {v}" for k, v in record.items())


def _lookup(fn, value: str) -> str:
    log.info("Tool %s called (value ends ...%s)", fn.__name__, value[-4:])
    try:
        record = fn(value)
    except ValueError as e:
        log.warning("Tool %s rejected input: %s", fn.__name__, e)
        return str(e)
    LAST_RECORD.clear()
    if record:
        LAST_RECORD.update(record)
    return format_record(record)


@tool
def get_cibil_by_customer_id(customer_id: str) -> str:
    """Fetch customer master and latest CIBIL report using the customer ID (e.g. C1001)."""
    return _lookup(db.fetch_by_customer_id, customer_id)


@tool
def get_cibil_by_mobile(mobile_number: str) -> str:
    """Fetch customer master and latest CIBIL report using the customer's mobile number (10-15 digits)."""
    return _lookup(db.fetch_by_mobile, mobile_number)


TOOLS = [get_cibil_by_customer_id, get_cibil_by_mobile]
