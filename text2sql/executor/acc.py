import sys
import sqlite3
from tqdm import tqdm
from pathlib import Path
from func_timeout import FunctionTimedOut, func_timeout
from typing import Optional, Union, List, Dict, Any
from text2sql.logger import setup_console_logger
from text2sql.utils import save_to_json

logger = setup_console_logger(name="[EVALUATION]")


class Text2SQLAccuracyFromSQLite:
    def __init__(self, experiment_path: Union[str, Path]):
        self.experiment_path = Path(experiment_path)

    def match_sqls(
        self, predicted_sql: str, ground_truth_sql: str, dsn_or_db_path: str
    ) -> int:
        conn = sqlite3.connect(dsn_or_db_path)
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        cursor.execute(ground_truth_sql)
        ground_truth_res = cursor.fetchall()
        conn.close()
        return 1 if set(predicted_res) == set(ground_truth_res) else 0

    def execute_model(
        self,
        predicted_sql: str,
        ground_truth_sql: str,
        dsn_or_db_path: str,
        meta_time_out: int = 1000,
    ) -> Dict[str, Any]:
        try:
            result = func_timeout(
                meta_time_out,
                self.match_sqls,
                args=(predicted_sql, ground_truth_sql, dsn_or_db_path),
            )
            return {"accuracy": result, "error": None}
        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut as e:
            return {"accuracy": 0, "error": f"Function Timed Out Error: {e}"}
        except Exception as e:
            return {"accuracy": 0, "error": f"Exception: {e}"}

    def compute_metric(self, results: List[Dict[str, Any]]) -> float:
        try:
            return sum(res["accuracy"] for res in results) / len(results) * 100
        except ZeroDivisionError:
            return 0.0
        except Exception as e:
            logger.error(f"Error computing ex-accuracy metric: {e}")
            return 0.0

    def execute(
        self,
        model_responses: List[Dict[str, Any]],
        filter_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        data_with_results = []
        for response in tqdm(model_responses, total=len(model_responses)):
            result = self.execute_model(
                predicted_sql=response["generated"],
                ground_truth_sql=response["sql"],
                dsn_or_db_path=response["db_path"],
            )
            data_with_results.append({**response, **result})

        execution_result = {}
        if filter_by:
            if filter_by not in data_with_results[0]:
                raise KeyError(f"Filter key: {filter_by} is not found in responses")

            filter_values = {response[filter_by] for response in data_with_results}
            total_responses = len(data_with_results)
            overall_metric = 0.0

            for value in filter_values:
                filtered_responses = [
                    response
                    for response in data_with_results
                    if response[filter_by] == value
                ]
                metric_value = self.compute_metric(results=filtered_responses)
                execution_result[value] = metric_value
                overall_metric += (
                    metric_value * len(filtered_responses) / total_responses
                )

            execution_result["overall"] = overall_metric
        else:
            execution_result["overall"] = self.compute_metric(results=data_with_results)

        save_to_json(
            json_object=execution_result,
            save_path=self.experiment_path / "ex_accuracy.json",
        )

        # also save the data_with_results
        save_to_json(
            json_object=data_with_results,
            save_path=self.experiment_path / "predict.json",
        )
        return execution_result
