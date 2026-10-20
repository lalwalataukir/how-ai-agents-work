"""E9 lab: the research assistant as a web app, with streaming, rate limits and a daily cost cap.

Run it on your laptop with:
    uv run uvicorn app:app --reload
then open http://127.0.0.1:8000
"""
import os
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, Field

import agent

MAX_PER_MINUTE = 5  # questions per visitor per minute
DAILY_BUDGET = float(os.environ.get("DAILY_BUDGET", "0.50"))  # dollars a day, for all visitors together
WEB_TOOLS = ["search_wikipedia", "read_page"]  # a public site gets no private notes and no saving

app = FastAPI()
recent = defaultdict(deque)  # visitor -> times of their recent questions
spent = {"day": "", "dollars": 0.0}  # resets each day, and whenever the server restarts


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)  # FastAPI rejects anything else with a 422


def check_limits(request: Request):
    """Runs before every question. Raising an HTTPException turns the request away."""
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


@app.get("/")
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True}  # the host checks this to know the app is up


@app.post("/ask", response_class=EventSourceResponse, dependencies=[Depends(check_limits)])
def ask(body: Question):
    """Stream the agent's events to the page as they happen: plan, tools, text, done."""
    start, first_text = time.perf_counter(), None
    for event in agent.steps(body.question, [], tools=WEB_TOOLS, approve=lambda name, args: False):
        if event["type"] == "text" and first_text is None:
            first_text = time.perf_counter() - start  # what the visitor feels as speed
        if event["type"] == "done":
            spent["dollars"] += event["cost"]
            event["seconds"] = round(time.perf_counter() - start, 1)
            event["first_text"] = round(first_text or event["seconds"], 1)
        yield event
