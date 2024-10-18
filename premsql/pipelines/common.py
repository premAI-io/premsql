from typing import Any, Dict, Literal

import pandas as pd
from tabulate import tabulate

from premsql.executors.from_langchain import SQLDatabase


def execute_and_render_result(
    db: SQLDatabase, sql: str, using: Literal["dataframe", "tabulate", "json"]
):
    result = db.run_no_throw(command=sql, fetch="cursor")

    if isinstance(result, str):
        return _render_error(result, sql, using)

    return _render_data(result, sql, using)


def _render_error(error: str, sql: str, using: str) -> Dict[str, Any]:
    to_show = {"error": error, "sql": sql, "table": None}

    if using == "dataframe":
        to_show["table"] = pd.DataFrame([{"error": error}])
    elif using == "tabulate":
        to_show["table"] = tabulate(
            pd.DataFrame([{"error": error}]),
            headers="keys",
            tablefmt="psql",
            showindex=False,
        )
    elif using == "json":
        to_show["table"] = {"data": f"Error: {error}", "columns": "ERROR"}

    return to_show


def _render_data(result, sql: str, using: str) -> Dict[str, Any]:
    table = pd.DataFrame(data=result.fetchall(), columns=result.keys())
    to_show = {"table": table, "error": None, "sql": sql}

    if using == "tabulate":
        to_show["table"] = tabulate(
            table, headers="keys", tablefmt="psql", showindex=False
        )
    elif using == "json":
        to_show["table"] = {"data": table.to_dict(), "columns": list(result.keys())}

    return to_show
