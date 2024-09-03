import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from func_timeout import FunctionTimedOut, func_timeout
from tqdm import tqdm

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
                ground_truth_sql=response["SQL"],
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


class Text2SQLVESFromSQLite:
    def __init__(self, experiment_path: Union[str, Path]):
        self.experiment_path = Path(experiment_path)

    def clean_abnormal(self, input: List[float]) -> List[float]:
        input_array = np.asarray(input)
        mean = np.mean(input_array)
        std = np.std(input_array)
        return [x for x in input_array if mean - 3 * std < x < mean + 3 * std]

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

    def sql_execution_time(self, sql: str, dsn_or_db_path) -> float:
        conn = sqlite3.connect(dsn_or_db_path)
        cursor = conn.cursor()
        start_time = time.time()
        cursor.execute(sql)
        exec_time = time.time() - start_time
        return exec_time

    def execute_fn(
        self,
        predicted_sql: str,
        ground_truth_sql: str,
        dsn_or_db_path: str,
        iterate_num: int = 10,
    ) -> float:
        if self.match_sqls(predicted_sql, ground_truth_sql, dsn_or_db_path) == 1:
            diff_list = []
            for _ in range(iterate_num):
                predicted_time = self.sql_execution_time(
                    sql=predicted_sql, dsn_or_db_path=dsn_or_db_path
                )
                ground_truth_time = self.sql_execution_time(
                    sql=ground_truth_sql, dsn_or_db_path=dsn_or_db_path
                )
                diff_list.append(ground_truth_time / predicted_time)
            diff_list = self.clean_abnormal(diff_list)
            time_ratio = sum(diff_list) / len(diff_list)
            return time_ratio
        return 0.0

    def execute_model(
        self,
        predicted_sql: str,
        ground_truth_sql: str,
        dsn_or_db_path: str,
        iterate_num: int = 10,
        meta_time_out: int = 1000,
    ):
        try:
            result = func_timeout(
                meta_time_out,
                self.execute_fn,
                args=(predicted_sql, ground_truth_sql, dsn_or_db_path, iterate_num),
            )
            return {"ves": result, "error": None}
        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut as e:
            return {"ves": 0, "error": f"Function Timed Out Error: {e}"}
        except Exception as e:
            return {"ves": 0, "error": f"Exception: {e}"}

    def compute_metric(self, results: List[Dict[str, Any]]) -> float:
        try:
            num_queries = len(results)
            total_ratio = 0.0
            for result in results:
                total_ratio += math.sqrt(result["ves"]) * 100
            ves = total_ratio / num_queries
            return ves
        except Exception as e:
            logger.error(f"Error computing VES metric: {e}")
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
                ground_truth_sql=response["SQL"],
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
            json_object=execution_result, save_path=self.experiment_path / "ves.json"
        )

        # also save the data_with_results
        save_to_json(
            json_object=data_with_results,
            save_path=self.experiment_path / "predict.json",
        )
        return execution_result


class ExecutorFromSQLite:
    def __init__(self, experiment_path: Union[str, Path]):
        self.acc = Text2SQLAccuracyFromSQLite(experiment_path)
        self.ves = Text2SQLVESFromSQLite(experiment_path)

    def compute(
        self,
        model_responses: list[dict],
        metric: Literal["accuracy", "ves"],
        filter_by: Optional[dict] = None,
    ) -> dict:
        assert metric in ["accuracy", "ves"], f"Unknown metric: {metric}"
        if metric == "accuracy":
            return self.acc.execute(
                model_responses=model_responses, filter_by=filter_by
            )

        return self.ves.execute(model_responses=model_responses, filter_by=filter_by)
