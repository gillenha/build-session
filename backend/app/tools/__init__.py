"""Tool registry and dispatcher. Only the model's tool_use blocks reach run_tool."""
import json

from app.tools import filings, quote

DEFINITIONS = [quote.DEFINITION, filings.DEFINITION]
_RUNNERS = {"get_quote": quote.run, "search_filings": filings.run}


def run_tool(name: str, args: dict) -> tuple[object | None, str, bool]:
    """Returns (result data or None, content string for the model, is_error)."""
    runner = _RUNNERS.get(name)
    if runner is None:
        return None, f"Unknown tool {name}", True
    try:
        data = runner(**args)
    except (LookupError, TypeError, ValueError) as e:
        return None, str(e), True
    return data, json.dumps(data), False
