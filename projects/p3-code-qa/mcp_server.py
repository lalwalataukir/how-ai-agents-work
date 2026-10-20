"""The codebase index as an MCP server, so Claude Code (or any MCP app) can search and read the
code with your chunking, your hybrid search and your guards.

Test it with:
    uv run mcp dev mcp_server.py
Add it to Claude Code with:
    claude mcp add code-qa -- uv --directory /full/path/to/code-qa run mcp_server.py
"""
from functools import cache

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import qa

mcp = MCPServer("code-qa")


@cache
def index():
    return qa.Index(qa.ROOT)


@mcp.tool()
def search_code(query: str) -> list[dict]:
    """Search the codebase by keyword and meaning. Returns up to 5 chunks, each with its file, lines, name and code."""
    # BEGIN m6
    return [{"path": c.path, "start": c.start, "end": c.end, "name": c.name, "code": c.text} for c in index().search(query)]
    # END m6
    #> # TODO milestone 6: search the index and return each chunk's path, start, end, name and code.
    #> raise NotImplementedError("milestone 6: search_code")


@mcp.tool()
def read_lines(path: str, start: int, end: int) -> str:
    """Read numbered lines from a file in the codebase, at most 200. Hidden and secret files are refused."""
    # BEGIN m6
    try:
        text, _ = qa.read_lines(qa.ROOT, path, start, end)  # the same guard as the agent's tool
    except ValueError as error:
        raise ToolError(str(error)) from None  # an expected refusal: its message goes to the app
    return text
    # END m6
    #> # TODO milestone 6: return the lines from qa.read_lines, so the guards from milestone 4 apply here
    #> # too. Turn a ValueError into a ToolError, so the app sees why.
    #> raise NotImplementedError("milestone 6: read_lines")


if __name__ == "__main__":
    mcp.run()  # talks to the app over stdin and stdout
