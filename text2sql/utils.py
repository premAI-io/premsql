import json
import sqlite3
from pathlib import Path
from typing import Union

from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[UTILS]")


def save_to_json(save_path: Union[str, Path], json_object: dict):
    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        with open(save_path, "w") as json_file:
            json.dump(json_object, json_file, indent=4)
        logger.info(f"Saved JSON in: {save_path}")
    except Exception as e:
        logger.error(f"Unable to save JSON, Error: {e}")


def load_results_from_json(result_json_path: str) -> dict:
    try:
        with open(result_json_path, "r") as json_file:
            return json.load(json_file)
    except Exception as e:
        logger.error(f"Unable to load JSON, Error: {e}")


def execute_sql(dsn_or_db_path: str, sql: str):
    conn = sqlite3.connect(dsn_or_db_path)
    cursor = conn.cursor()
    error = None
    try:
        cursor.execute(sql)
        conn.commit()
        return None
    except Exception as e:
        error = f"Error: {str(e)}"
    return error


def _filter_options(data: list[dict], filter_by: tuple, accepted_keys: list[str]):
    filter_key, filter_value = filter_by
    assert filter_key in accepted_keys, ValueError(
        f"Filtering is supported for keys: `{''.join(accepted_keys)}`"
    )
    for key in accepted_keys:
        if filter_key == key:
            accepted_values = set([content[key] for content in data])
            assert filter_value in accepted_values, ValueError(
                f"Available values for key: {key} are: {', '.join(accepted_values)}"
            )

    filtered_data = [content for content in data if content[filter_key] == filter_value]
    return filtered_data
