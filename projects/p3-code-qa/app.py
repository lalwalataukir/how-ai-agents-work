"""The codebase assistant as a web app: answers stream in as the agent works, with limits so a
public link can't run up a bill.

Run it on your laptop with:
    uv run uvicorn app:app --reload
then open http://127.0.0.1:8000
"""
import os
import time
from collections import defaultdict, deque
from datetime import date
from functools import cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, Field

import qa

MAX_PER_MINUTE = 5  # questions per visitor per minute
DAILY_BUDGET = float(os.environ.get("DAILY_BUDGET", "0.50"))  # dollars a day, for all visitors together

app = FastAPI()
recent = defaultdict(deque)  # visitor -> times of their recent questions
spent = {"day": "", "dollars": 0.0}  # resets each day, and whenever the server restarts


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)  # FastAPI turns anything else away with a 422


@cache
def index():
    """The index, built once, on the first question (or by the start command, so visitors don't wait)."""
    return qa.Index(qa.ROOT)


def check_limits(request: Request):
    """Runs before every question. Raising an HTTPException turns the request away."""
    # BEGIN m5
    now, times = time.time(), recent[request.client.host]
    while times and now - times[0] > 60:
        times.popleft()  # forget questions older than a minute
    if len(times) >= MAX_PER_MINUTE:
        raise HTTPException(429, "Too many questions. Wait a minute and try again.")
    if spent["day"] != date.today().isoformat():
        spent.update(day=date.today().isoformat(), dollars=0.0)
    if spent["dollars"] >= DAILY_BUDGET:
        raise HTTPException(503, "Today's budget is used up. Try again tomorrow.")
    times.append(now)
    # END m5
    #> # TODO milestone 5: as in E9, a 429 after MAX_PER_MINUTE questions a minute from one visitor,
    #> # and a 503 once today's spending reaches DAILY_BUDGET. Until then, no limits:
    #> pass


@app.get("/")
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True}  # the host checks this to know the app is up


@app.post("/ask", response_class=EventSourceResponse, dependencies=[Depends(check_limits)])
def ask(body: Question):
    """Stream the agent's events to the page as they happen: each tool call, then the answer."""
    # BEGIN m5
    start = time.perf_counter()
    for event in qa.steps(body.question, index()):
        if event["type"] == "done":
            spent["dollars"] += event["cost"]
            event["seconds"] = round(time.perf_counter() - start, 1)
        yield event
    # END m5
    #> # TODO milestone 5: yield each event from qa.steps, add the cost of the "done" event to
    #> # spent["dollars"], and add how many seconds it took.
    #> raise NotImplementedError("milestone 5: ask")
