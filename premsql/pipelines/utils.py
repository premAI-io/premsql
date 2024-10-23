from typing import Any, Dict, Literal
import pandas as pd
from premsql.executors.from_langchain import SQLDatabase

def convert_df_to_dict(df: pd.DataFrame):
    return {
        "data": df.to_dict(), 
        "columns": list(df.keys())
    }

def execute_and_render_result(
    db: SQLDatabase, sql: str, using: Literal["dataframe","json"]
):
    result = db.run_no_throw(command=sql, fetch="cursor")

    if isinstance(result, str):
        return _render_error(result, sql, using)
    return _render_data(result, sql, using)


def _render_error(error: str, sql: str, using: str) -> Dict[str, Any]:
    to_show = {"sql_string": sql, "error_from_model": error, "dataframe": None}

    if using == "dataframe":
        to_show["dataframe"] = pd.DataFrame([{"error": error}])
    elif using == "json":
        to_show["dataframe"] = {"data": f"Error: {error}", "columns": "ERROR"}
    return to_show


def _render_data(result, sql: str, using: str) -> Dict[str, Any]:
    table = pd.DataFrame(data=result.fetchall(), columns=result.keys())
    to_show = {"sql_string": sql, "error_from_model": None, "dataframe": table}

    if using == "json":
        to_show["dataframe"] = {"data": table.to_dict(), "columns": list(result.keys())}
    return to_show