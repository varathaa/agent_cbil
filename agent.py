import logging
import re
import time

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

import config
import db
from tools import LAST_RECORD, TOOLS, format_record

log = logging.getLogger("cibil.agent")

SYSTEM_PROMPT = """You are a credit analyst assistant for a bank.
Use the provided tools to look up a customer's CIBIL details by customer ID or mobile number.
Rules:
- Answer ONLY from the tool output. Never invent scores or data.
- If the user gives neither a customer ID nor a mobile number, ask for one.
- If no customer is found, say so clearly.
- When data is found, give: customer name, CIBIL score with band
  (750+ Excellent, 700-749 Good, 650-699 Fair, below 650 Poor),
  credit card utilization, inquiries in last 30 days, serious delinquency flag,
  key points from the bureau summary, and a short overall risk assessment.
- Keep the answer concise and use markdown."""

_llm = ChatOllama(model=config.OLLAMA_MODEL, base_url=config.OLLAMA_BASE_URL, temperature=0)
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent(model=_llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    return _agent


def _fallback(prompt: str) -> str:
    # Used when the model does not support tool calling.
    mobile = re.search(r"\+?\d{10,15}", prompt)
    cid = re.search(r"\b(?=[A-Za-z0-9_-]*\d)[A-Za-z][A-Za-z0-9_-]{1,19}\b", prompt)
    LAST_RECORD.clear()
    if mobile:
        record = db.fetch_by_mobile(mobile.group())
    elif cid:
        record = db.fetch_by_customer_id(cid.group())
    else:
        return "Please provide a customer ID or mobile number to check CIBIL details."
    if record:
        LAST_RECORD.update(record)
    messages = [
        SystemMessage(SYSTEM_PROMPT),
        HumanMessage(f"User request: {prompt}\n\nDatabase result:\n{format_record(record)}"),
    ]
    return _llm.invoke(messages).content


def run_agent(prompt: str) -> tuple[str, dict]:
    LAST_RECORD.clear()
    start = time.perf_counter()
    log.info("Prompt received (%d chars) using model %s", len(prompt), config.OLLAMA_MODEL)
    try:
        result = _get_agent().invoke({"messages": [{"role": "user", "content": prompt}]})
        answer = result["messages"][-1].content
    except Exception as e:
        if "does not support tools" not in str(e):
            log.exception("Agent failed")
            raise
        log.warning("Model does not support tools; using regex fallback")
        answer = _fallback(prompt)
    log.info("Answered in %.1f s, record_found=%s", time.perf_counter() - start, bool(LAST_RECORD))
    return answer, dict(LAST_RECORD)
