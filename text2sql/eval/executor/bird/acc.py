import json
import os
import sqlite3
import sys
from typing import Optional

from func_timeout import FunctionTimedOut, func_timeout
from tabulate import tabulate

from text2sql.eval.executor.bird.base import BirdBenchExecutorBase
from text2sql.eval.settings import SQLGeneratorConfig


class BirdExecutorAcc(BirdBenchExecutorBase):
    def __init__(self, generator_config: SQLGeneratorConfig) -> None:
        self.generator_config = generator_config

    def execute_sql(self, predicted_sql: str, ground_truth: str, db_path: str) -> int:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        cursor.execute(ground_truth)
        ground_truth_res = cursor.fetchall()
        res = 0
        if set(predicted_res) == set(ground_truth_res):
            res = 1
        return res

    def execute_model(
        self,
        predicted_sql: str,
        ground_truth: str,
        db_path: str,
        meta_time_out: float,
    ):
        result = {}

        try:
            res = func_timeout(
                meta_time_out,
                self.execute_sql,
                args=(predicted_sql, ground_truth, db_path),
            )
            result["result"] = res
            result["error"] = "null"

        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut as e:
            result["result"] = 0
            result["error"] = f"timeout: {e}"

        except Exception as e:
            result["result"] = 0
            result["error"] = f"exception: {e}"

        return result

    def compute_metric(self, results: list):
        try:
            return sum([res["res"] for res in results]) / len(results) * 100
        except Exception:
            return 0

    def execute(self, model_responses: list[dict], filter_used: Optional[tuple] = None):
        for response in model_responses:
            result = self.execute_model(
                predicted_sql=response["generated"],
                ground_truth=response["SQL"],
                db_path=response["db_path"],
                meta_time_out=1000,
            )
            response["result"] = result["result"]
            response["error"] = result["error"]

        score_dict = self.compute_metric_by_diff(
            exec_results=model_responses, filter_used=filter_used
        )

        if filter_used:
            filter_value = f"_{filter_used[1]}"
        else:
            filter_value = ""

        print(
            "=> ", self.generator_config.data_output_folder, f"acc{filter_value}.json"
        )
        with open(
            os.path.join(
                self.generator_config.data_output_folder, f"acc{filter_value}.json"
            ),
            "w",
        ) as json_file:
            json.dump(score_dict, json_file)

        self.print_data(results=score_dict, metric_name="accuracy")
        return score_dict

    def print_data(self, results: dict, metric_name: str):
        print(f"{'='*21}   {metric_name.upper()}    {'='*21}")
        table_data = [[key, value[0], value[1]] for key, value in results.items()]
        headers = ["Category", "num_correct (%)", "total questions"]
        print(tabulate(table_data, headers, tablefmt="grid"))
