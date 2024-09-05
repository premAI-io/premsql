import math
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import numpy as np
from func_timeout import FunctionTimedOut, func_timeout
from tqdm.auto import tqdm

from premsql.datasets.utils import save_to_json


class BaseExecutor(ABC):
    @abstractmethod
    def execute_sql(self, sql: str, dsn_or_db_path: str) -> dict:
        return {"result": None, "execution_time": None, "error": None}

    def match_sqls(
        self, predicted_sql: str, gold_sql: str, dsn_or_db_path: str
    ) -> bool:
        prediction = self.execute_sql(sql=predicted_sql, dsn_or_db_path=dsn_or_db_path)
        gold = self.execute_sql(sql=gold_sql, dsn_or_db_path=dsn_or_db_path)
        if prediction["error"]:
            return {
                "result": 0,
                "error": prediction["error"],
            }

        is_match = set(prediction["result"]) == set(gold["result"])
        return {
            "result": int(is_match),
            "error": None if is_match else "Table mismatch",
        }

    def clean_abnormal(self, input: list[float]) -> list[float]:
        input_array = np.asarray(input)
        mean = np.mean(input_array)
        std = np.std(input_array)
        return [x for x in input_array if mean - 3 * std < x < mean + 3 * std]

    def iterated_execution(
        self,
        predicted_sql: str,
        gold_sql: str,
        dsn_or_db_path: str,
        num_iterations: int,
    ) -> dict:
        is_match = self.match_sqls(
            predicted_sql=predicted_sql,
            gold_sql=gold_sql,
            dsn_or_db_path=dsn_or_db_path,
        )

        if is_match["result"] == 1:
            diff_list = [
                self.execute_sql(sql=gold_sql, dsn_or_db_path=dsn_or_db_path)[
                    "execution_time"
                ]
                / self.execute_sql(sql=gold_sql, dsn_or_db_path=dsn_or_db_path)[
                    "execution_time"
                ]
                for _ in range(num_iterations)
            ]
            processed_diff_list = self.clean_abnormal(diff_list)
            return {
                "result": sum(processed_diff_list) / len(processed_diff_list),
                "error": None,
            }
        return {"result": 0, "error": is_match["error"]}


class Text2SQLEvaluator:
    def __init__(
        self, executor: BaseExecutor, experiment_path: Union[str, Path]
    ) -> None:
        self.executor = executor
        self.experiment_path = Path(experiment_path)

    def _execute_model(
        self,
        metric_name: str,
        generated_sql: str,
        gold_sql: str,
        dsn_or_db_path: str,
        meta_time_out: Optional[int] = 1000,
        num_iterations: Optional[int] = None,
        debug: Optional[bool] = False,
    ):
        assert metric_name in ["accuracy", "ves"], "Invalid metric name"
        try:
            if metric_name == "accuracy":
                result = func_timeout(
                    meta_time_out,
                    self.executor.match_sqls,
                    args=(generated_sql, gold_sql, dsn_or_db_path),
                )
            elif metric_name == "ves":
                num_iterations = 10 if num_iterations is None else num_iterations
                result = func_timeout(
                    meta_time_out,
                    self.executor.iterated_execution,
                    args=(generated_sql, gold_sql, dsn_or_db_path, num_iterations),
                )
            else:
                raise ValueError(f"Invalid metric name: {metric_name}")

            return {
                metric_name: result["result"],
                "error": result["error"],
            }
        except FunctionTimedOut as e:
            return {
                metric_name: None,
                "error": f"Function Timed out: {e}",
            }
        except Exception as e:
            if debug:
                traceback.print_exc()

            return {
                metric_name: None,
                "error": f"Exception: {e}",
            }

    def execute(
        self,
        metric_name: str,
        model_responses: list[dict],
        filter_by: Optional[str] = None,
        num_iterations: Optional[int] = 10,
        meta_time_out: Optional[int] = 1000,
        debug: Optional[bool] = False,
    ) -> dict:
        data_with_results = []

        for response in tqdm(model_responses, total=len(model_responses)):
            result = self._execute_model(
                metric_name=metric_name,
                generated_sql=response["generated"],
                gold_sql=response["SQL"],
                dsn_or_db_path=response["db_path"],
                num_iterations=num_iterations,
                meta_time_out=meta_time_out,
                debug=debug,
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
                metric_value = self.compute_metric(
                    results=filtered_responses, metric_name=metric_name
                )
                execution_result[value] = metric_value
                overall_metric += (
                    metric_value * len(filtered_responses) / total_responses
                )

            execution_result["overall"] = overall_metric
        else:
            execution_result["overall"] = self.compute_metric(
                results=data_with_results, metric_name=metric_name
            )

        save_to_json(
            json_object=execution_result,
            save_path=self.experiment_path / f"{metric_name}.json",
        )

        # also save the data_with_results
        save_to_json(
            json_object=data_with_results,
            save_path=self.experiment_path / "predict.json",
        )
        return execution_result

    def compute_metric(self, results: list[dict], metric_name: str) -> float:
        if metric_name == "accuracy":
            return sum(res["accuracy"] for res in results) / len(results) * 100

        elif metric_name == "ves":
            num_queries = len(results)
            total_ratio = 0.0
            for result in results:
                total_ratio += math.sqrt(result["ves"]) * 100
            ves = total_ratio / num_queries
            return ves

        else:
            raise ValueError(f"Invalid metric name: {metric_name}")
