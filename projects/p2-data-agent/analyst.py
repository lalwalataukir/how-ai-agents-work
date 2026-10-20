"""Data-analysis agent: ask questions about the shop's sales in plain English. Claude writes SQL,
the code runs it read-only and safely, and every answer shows the queries behind it.

Run it with:
    uv run make_data.py                                    # once: makes shop.db
    uv run analyst.py                                      # ask questions, with follow-ups
    uv run analyst.py "What was revenue in March 2025?"    # one question
    uv run analyst.py --schema                             # what Claude knows about the data
"""
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import matplotlib
from dotenv import load_dotenv
from pydantic import BaseModel

matplotlib.use("Agg")  # draw charts to files, without opening windows
import matplotlib.pyplot as plt  # noqa: E402

load_dotenv()

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50  # dollars per million tokens, for this model
HERE = Path(__file__).parent
DB = HERE / "shop.db"
CHARTS = HERE / "charts"
MAX_ROWS = 200  # the most rows one query sends back to Claude
MAX_SECONDS = 2  # the longest one query may run
MAX_CALLS = 8  # stop condition: most model calls for one question
MAX_TURNS = 6  # follow-ups remember this many earlier questions and answers

SYSTEM = """You are a data analyst for a small online shop. Answer questions about its sales
database by running SQL with the run_sql tool. The database is SQLite.

Rules:
- Get every number from a query. Never guess, and don't add up rows yourself: use SUM, COUNT and AVG.
- Money is stored in cents. Divide by 100.0 for dollars.
- Only orders with status 'completed' count as sales, unless the question says otherwise.
- Use make_chart when the user asks for a chart, or when a trend over time is the answer.
- If the data can't answer the question, say so.

Answer in one or two sentences with the key numbers, and put the main number in value.

<schema>
{schema}
</schema>"""

TOOLS = [
    {
        "name": "run_sql",
        "description": "Run one read-only SQLite SELECT query on the shop database. Returns the columns and "
                       "up to 200 rows as JSON. Errors come back as text: fix the query and try again.",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "One SELECT statement"}},
            "required": ["sql"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "make_chart",
        "description": "Draw a chart from a query with exactly two columns: labels, then numbers. Saves a PNG "
                       "and returns its path. Use bar for categories, line for time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "A short chart title"},
                "kind": {"type": "string", "enum": ["bar", "line"]},
                "sql": {"type": "string", "description": "One SELECT with two columns: labels, then numbers"},
            },
            "required": ["title", "kind", "sql"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

client = anthropic.Anthropic()


# ---------- Milestone 1: know the data ----------

def describe_schema(db=DB):
    """Each table with its row count and columns. Text columns with a few distinct values list them,
    so Claude knows to write status = 'completed', not 'complete'."""
    # BEGIN m1
    conn = sqlite3.connect(db)
    lines = []
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
    for table in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        lines.append(f"{table} ({count} rows)")
        for _, column, kind, *_ in conn.execute(f'PRAGMA table_info("{table}")'):
            line = f"  {column} {kind}"
            if kind == "TEXT":
                values = [row[0] for row in conn.execute(f'SELECT DISTINCT "{column}" FROM "{table}" ORDER BY 1 LIMIT 9')]
                if len(values) <= 8:
                    line += ": " + ", ".join(values)
            lines.append(line)
    conn.close()
    return "\n".join(lines)
    # END m1
    #> # TODO milestone 1: for each table, a line like "orders (2000 rows)", then one line per column,
    #> # such as "  status TEXT: cancelled, completed, refunded". List values only when there are 8 or fewer.
    #> raise NotImplementedError("milestone 1: describe_schema")


# ---------- Milestone 2: a safe SQL tool ----------

ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def only_reads(action, *details):
    """SQLite asks this before each step of a query. Anything but reading is refused."""
    return sqlite3.SQLITE_OK if action in ALLOWED else sqlite3.SQLITE_DENY


def run_sql(db, sql, max_rows=MAX_ROWS, seconds=MAX_SECONDS):
    """Run one query, read-only. Returns {"columns", "rows", "truncated"}.
    Raises ValueError, with a message Claude can act on, for anything that isn't allowed or fails."""
    # BEGIN m2
    if not Path(db).is_file():
        raise ValueError(f"{Path(db).name} doesn't exist. Run: uv run make_data.py")
    conn = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)  # the file itself is read-only
    conn.set_authorizer(only_reads)  # and so is every statement
    deadline = time.monotonic() + seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)  # True stops the query
    try:
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError("That isn't a query. Write one SELECT statement.")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchmany(max_rows + 1)
    except sqlite3.Error as error:
        if "interrupted" in str(error):
            raise ValueError(f"The query took longer than {seconds} seconds. Make it simpler.") from None
        if "not authorized" in str(error):
            raise ValueError("Only SELECT queries are allowed: nothing can be changed or attached.") from None
        raise ValueError(f"SQLite: {error}") from None
    finally:
        conn.close()
    return {"columns": columns, "rows": [list(row) for row in rows[:max_rows]], "truncated": len(rows) > max_rows}
    # END m2
    #> # TODO milestone 2: open db read-only (mode=ro), refuse anything but reading with only_reads,
    #> # stop queries after `seconds`, and return at most max_rows rows. Raise ValueError for every problem.
    #> raise NotImplementedError("milestone 2: run_sql")


# ---------- Milestone 3: the agent ----------

class Answer(BaseModel):
    answer: str  # one or two sentences, with the key numbers
    value: float | None  # the main number in the answer, if there is one


@dataclass
class Cost:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def add(self, usage):
        self.calls += 1
        self.tokens_in += usage.input_tokens
        self.tokens_out += usage.output_tokens

    def dollars(self):
        return (self.tokens_in * PRICE_IN + self.tokens_out * PRICE_OUT) / 1_000_000


@dataclass
class Result:
    answer: Answer
    queries: list = field(default_factory=list)  # every SQL query that ran, in order
    charts: list = field(default_factory=list)  # paths of the charts it saved


def run_tool(name, args, db, result):
    """Run one tool call, and keep a record of it in result. Returns the text to send back, and
    whether it failed. Errors go back to Claude so it can fix its query."""
    # BEGIN m3
    if name == "make_chart":
        return chart_tool(args, db, result)
    if name != "run_sql":
        return f"There is no tool called {name}.", True
    result.queries.append(args["sql"])
    try:
        return json.dumps(run_sql(db, args["sql"]), default=str), False
    except ValueError as error:
        return str(error), True
    # END m3
    #> # TODO milestone 3: run run_sql (send make_chart to chart_tool), add each query to
    #> # result.queries, and turn a ValueError into an error result.
    #> raise NotImplementedError("milestone 3: run_tool")


def ask(question, memory=(), db=DB, cost=None):
    """Answer one question: Claude writes queries, the code runs them, until Claude answers.
    memory holds earlier questions and answers; cost adds up what every call costs."""
    # BEGIN m3
    cost = cost if cost is not None else Cost()
    result = Result(answer=Answer(answer=f"Stopped after {MAX_CALLS} model calls without an answer.", value=None))
    system = SYSTEM.format(schema=describe_schema(db))
    messages = list(memory) + [{"role": "user", "content": question}]
    for _ in range(MAX_CALLS):  # stop condition, as in E7
        response = client.messages.parse(
            model=MODEL, max_tokens=8000, system=system, tools=TOOLS, messages=messages, output_format=Answer,
        )
        cost.add(response.usage)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            if response.stop_reason == "end_turn":
                result.answer = response.parsed_output
            else:
                result.answer = Answer(answer=f"Stopped early ({response.stop_reason}).", value=None)
            return result
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  -> {block.name}: {block.input.get('sql', '')}", file=sys.stderr)
                text, failed = run_tool(block.name, block.input, db, result)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": failed})
        messages.append({"role": "user", "content": results})
    return result
    # END m3
    #> # TODO milestone 3: the tool-use loop, with output_format=Answer and the schema in the system
    #> # prompt. Stop after MAX_CALLS calls. Return a Result.
    #> raise NotImplementedError("milestone 3: ask")


# ---------- Milestone 4: charts ----------

def make_chart(db, title, kind, sql):
    """Draw a two-column query (labels, numbers) as a bar or line chart. Returns the PNG's path."""
    # BEGIN m4
    data = run_sql(db, sql)  # the same safe path as every other query
    if len(data["columns"]) != 2 or not data["rows"]:
        raise ValueError("A chart needs a query with two columns, labels then numbers, and at least one row.")
    labels = [str(row[0]) for row in data["rows"]]
    values = [row[1] for row in data["rows"]]
    if not all(isinstance(value, (int, float)) for value in values):
        raise ValueError("The second column must be numbers.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if kind == "line":
        ax.plot(labels, values, marker="o")
    else:
        ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(data["columns"][1])
    ax.tick_params(axis="x", labelrotation=45 if len(labels) > 6 else 0)
    fig.tight_layout()
    CHARTS.mkdir(exist_ok=True)
    path = CHARTS / (re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] + ".png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
    # END m4
    #> # TODO milestone 4: run sql with run_sql, check it has two columns of labels and numbers,
    #> # draw it with matplotlib, save it in CHARTS as a PNG named after the title, and return the path.
    #> raise NotImplementedError("milestone 4: make_chart")


def chart_tool(args, db, result):
    """The make_chart tool call: returns the text to send back, and whether it failed."""
    # BEGIN m4
    result.queries.append(args["sql"])
    try:
        path = make_chart(db, args["title"], args["kind"], args["sql"])
    except ValueError as error:
        return str(error), True
    result.charts.append(path.relative_to(HERE).as_posix())
    return json.dumps({"saved": path.name}), False
    # END m4
    #> # TODO milestone 4: call make_chart, record the query and the chart in result, send errors back.
    #> return "make_chart isn't built yet. Answer without a chart.", True


# ---------- Milestone 6: follow-up questions ----------

class Session:
    """A conversation: each question can refer back to earlier ones ("now split that by region")."""

    def __init__(self, db=DB):
        self.db, self.memory, self.cost = db, [], Cost()

    def ask(self, question):
        result = ask(question, self.memory, self.db, self.cost)
        self.remember(question, result)
        return result

    def remember(self, question, result):
        """Keep the question, the answer and the last queries, for at most MAX_TURNS turns."""
        # BEGIN m6
        sql = "\n".join(result.queries[-3:]) or "(no queries)"
        self.memory += [{"role": "user", "content": question},
                        {"role": "assistant", "content": f"{result.answer.answer}\n\n<sql>\n{sql}\n</sql>"}]
        self.memory = self.memory[-2 * MAX_TURNS:]
        # END m6
        #> # TODO milestone 6: add the question, and the answer with its last 3 queries, to self.memory.
        #> # Keep only the last MAX_TURNS questions and answers. Until then, nothing is remembered:
        #> pass


def show(session, question):
    """Answer one question in the terminal, with the queries and charts behind it."""
    try:
        result = session.ask(question)
    except anthropic.APIConnectionError:
        print("Could not reach the API. Check your internet connection and try again.")
        return
    except anthropic.APIStatusError as error:  # a bad key, no credit, overloaded: after the SDK's retries
        print(f"The API answered {error.status_code}: {error.message}")
        return
    print(result.answer.answer)
    for sql in dict.fromkeys(result.queries):  # each query once, in order
        print(f"  SQL: {sql}")
    for chart in result.charts:
        print(f"  Chart saved: {chart}")


def main(args):
    if not DB.is_file():
        sys.exit("No shop.db yet. Run: uv run make_data.py")
    if args == ["--schema"]:
        print(describe_schema(DB))
        return
    session = Session(DB)
    if args:
        show(session, " ".join(args))
    else:
        print("Ask about the shop's sales. Type quit to stop.")
        while (question := input("\nYou: ").strip()).lower() not in ("quit", "exit"):
            if question:
                show(session, question)
    print(f"[{session.cost.calls} model calls, ${session.cost.dollars():.4f}]")


if __name__ == "__main__":
    main(sys.argv[1:])
