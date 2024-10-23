import sqlite3
import time

from premsql.executors.base import BaseExecutor
from premsql.utils import convert_sqlite_dsn_to_path

class SQLiteExecutor(BaseExecutor):
    def execute_sql(self, sql: str, dsn_or_db_path: str) -> dict:
        dsn_or_db_path = convert_sqlite_dsn_to_path(dsn=dsn_or_db_path)
        conn = sqlite3.connect(dsn_or_db_path)
        cursor = conn.cursor()

        start_time = time.time()
        try:
            cursor.execute(sql)
            result = cursor.fetchall()
            error = None
        except Exception as e:
            result = None
            error = str(e)

        end_time = time.time()
        cursor.close()
        conn.close()

        result = {
            "result": result,
            "error": error,
            "execution_time": end_time - start_time,
        }
        return result
