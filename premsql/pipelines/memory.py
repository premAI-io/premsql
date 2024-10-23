import sqlite3
from typing import List, Optional, Literal

from premsql.logger import setup_console_logger
from premsql.pipelines.models import ExitWorkerOutput

logger = setup_console_logger("[PIPELINE-MEMORY]")


class AgentInteractionMemory:
    def __init__(self, session_name: str, db_path: Optional[str] = None):
        self.session_name = session_name
        self.db_path = db_path or "premsql_pipeline_memory.db"
        self.conn = sqlite3.connect(self.db_path)
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {self.session_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            db_connection_uri TEXT,
            route_taken TEXT,
            sql_string TEXT,
            sql_reasoning TEXT,
            sql_input_dataframe TEXT,
            sql_output_dataframe TEXT,
            error_from_sql_worker TEXT,
            analysis TEXT,
            analysis_reasoning TEXT,
            analysis_input_dataframe TEXT,
            error_from_analysis_worker TEXT,
            plot_config TEXT,
            plot_input_dataframe TEXT,
            plot_output_dataframe TEXT,
            image_to_plot TEXT,
            plot_reasoning TEXT,
            error_from_plot_worker TEXT,
            followup_route_to_take TEXT,
            followup_suggestion TEXT,
            error_from_followup_worker TEXT,
            additional_input TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        self.conn.commit()

    def get(self, limit: Optional[int] = None) -> List[ExitWorkerOutput]:
        cursor = self.conn.cursor()
        if limit is None:
            cursor.execute(f"SELECT * FROM {self.session_name} ORDER BY id DESC")
        else:
            cursor.execute(
                f"SELECT * FROM {self.session_name} ORDER BY id DESC LIMIT ?", (limit,)
            )
        rows = cursor.fetchall()
        return [self._row_to_exit_worker_output(row) for row in rows]
    
    def push(self, output: ExitWorkerOutput):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
        INSERT INTO {self.session_name} (
            question, db_connection_uri, route_taken, sql_string, sql_reasoning,
            sql_input_dataframe, sql_output_dataframe, error_from_sql_worker,
            analysis, analysis_reasoning, analysis_input_dataframe,
            error_from_analysis_worker, plot_config, plot_input_dataframe,
            plot_output_dataframe, image_to_plot, plot_reasoning,
            error_from_plot_worker, followup_route_to_take, followup_suggestion,
            error_from_followup_worker, additional_input
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            self._exit_worker_output_to_tuple(output),
        )
        self.conn.commit()
        logger.info("Pushed to the database")

    def _row_to_exit_worker_output(self, row) -> ExitWorkerOutput:
        return ExitWorkerOutput(
            session_name=self.session_name,
            question=row[1],
            db_connection_uri=row[2],
            route_taken=row[3],
            sql_string=row[4],
            sql_reasoning=row[5],
            sql_input_dataframe=self._parse_json(row[6]),
            sql_output_dataframe=self._parse_json(row[7]),
            error_from_sql_worker=row[8],
            analysis=row[9],
            analysis_reasoning=row[10],
            analysis_input_dataframe=self._parse_json(row[11]),
            error_from_analysis_worker=row[12],
            plot_config=self._parse_json(row[13]),
            plot_input_dataframe=self._parse_json(row[14]),
            plot_output_dataframe=self._parse_json(row[15]),
            image_to_plot=row[16],
            plot_reasoning=row[17],
            error_from_plot_worker=row[18],
            followup_route_to_take=row[19],
            followup_suggestion=row[20],
            error_from_followup_worker=row[21],
            additional_input=self._parse_json(row[22]),
        )

    def _exit_worker_output_to_tuple(self, output: ExitWorkerOutput) -> tuple:
        return (
            output.question,
            output.db_connection_uri,
            output.route_taken,
            output.sql_string,
            output.sql_reasoning,
            self._serialize_json(output.sql_input_dataframe),
            self._serialize_json(output.sql_output_dataframe),
            output.error_from_sql_worker,
            output.analysis,
            output.analysis_reasoning,
            self._serialize_json(output.analysis_input_dataframe),
            output.error_from_analysis_worker,
            self._serialize_json(output.plot_config),
            self._serialize_json(output.plot_input_dataframe),
            self._serialize_json(output.plot_output_dataframe),
            output.image_to_plot,
            output.plot_reasoning,
            output.error_from_plot_worker,
            output.followup_route_to_take,
            output.followup_suggestion,
            output.error_from_followup_worker,
            self._serialize_json(output.additional_input),
        )

    def _parse_json(self, json_str):
        import json

        return json.loads(json_str) if json_str else None

    def _serialize_json(self, obj):
        import json

        return json.dumps(obj) if obj else None

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {self.session_name}")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __del__(self):
        self.close()

    def get_latest_dataframe(
        self, decision: Literal["plot", "analyse", "query", "followup"]
    ) -> dict:
        for content in self.get():
            if decision == "plot" and content.plot_input_dataframe:
                return content.plot_input_dataframe
            elif decision == "analyse" and content.analysis_input_dataframe:
                return content.analysis_input_dataframe
            elif decision == "query" and content.sql_output_dataframe:
                return content.sql_output_dataframe
            elif decision == "followup" and content.sql_output_dataframe:
                return content.sql_output_dataframe
        
        # If no matching dataframe is found, return an empty dictionary
        return {}
