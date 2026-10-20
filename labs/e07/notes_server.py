"""E7 lab, part 3: a tiny MCP server, so any MCP app (Claude Code, Claude Desktop and others)
can search your notes with the same code as your agent.

Test it with:
    uv run mcp dev notes_server.py
"""
from mcp.server import MCPServer

from rag import search  # E6: your notes

mcp = MCPServer("research-notes")


@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """Search the user's own notes and PDFs. Returns up to 4 passages, each with its file and page."""
    return search(query)


if __name__ == "__main__":
    mcp.run()  # talks to the app over stdin and stdout
