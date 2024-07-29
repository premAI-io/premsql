import os 
import sqlite3
import sys
import math 
import time 
import json 
from typing import Optional

import numpy as np 
from tabulate import tabulate
from func_timeout import FunctionTimedOut, func_timeout

from text2sql.eval.executor.bird.base import BirdBenchExecutorBase
from text2sql.eval.settings import SQLGeneratorConfig

class BirdExecutorVES(BirdBenchExecutorBase):
    def __init__(self, generator_config: SQLGeneratorConfig) -> None:
        self.generator_config = generator_config
    
    # This only keeps those values which are inside +/- 2 sigma
    def clean_abnormal(self, input: np.ndarray) -> list[float]:
        input = np.asarray(input)
        processed_list = []
        mean = np.mean(input, axis=0)
        std = np.std(input, axis=0)
        for x in input:
            if mean - 3 * std < x < mean + 3 * std:
                processed_list.append(x)
        return processed_list
    
    def execute_sql(self, sql: str, db_path: str) -> float:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        start_time = time.time()
        cursor.execute(sql)
        exec_time = time.time() - start_time
        return exec_time
    
    def iterated_execute_sql(
        self, predicted_sql: str, ground_truth: str, db_path: str, iterate_num: int
    ) -> float:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        cursor.execute(ground_truth)
        ground_truth_res = cursor.fetchall()
        
        diff_list = []
        time_ratio = 0
        
        if set(predicted_res) == set(ground_truth_res):
            for _ in range(iterate_num):
                predicted_time = self.execute_sql(predicted_sql, db_path)
                ground_truth_time = self.execute_sql(ground_truth, db_path)
                diff_list.append(ground_truth_time / predicted_time)
            processed_diff_list = self.clean_abnormal(diff_list)
            time_ratio = sum(processed_diff_list) / len(processed_diff_list)
        
        return time_ratio 
    
    # TODO: This part of the code can be reduced by putting it inside
    # the base class 

    def execute_model(
        self, 
        predicted_sql: str, 
        ground_truth: str,
        db_path: str, 
        iteration_num: int, 
        meta_time_out: float 
    ) -> dict:
        
        result = {}
        try:
            res = func_timeout(
                meta_time_out,
                self.iterated_execute_sql,
                args=(predicted_sql, ground_truth, db_path, iteration_num)
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
        num_queries = len(results)
        ves = 0

        for result in results:
            if result["res"] != 0:
                ves += math.sqrt(result["res"])
        return (ves / num_queries) * 100 
    

    # TODO: This function can be transfered to the base class
    def execute(
        self, 
        model_responses: list[dict], 
        iteration_num: Optional[int]=10,
        filter_used: Optional[tuple]=None
    ):
        for response in model_responses:
            result = self.execute_model(
                predicted_sql=response["generated"],
                ground_truth=response["SQL"],
                db_path=response["db_path"],
                meta_time_out=1000,
                iteration_num=iteration_num
            ) 
            response["result"] = result["result"]
            response["error"] = result["error"]
        
        score_dict = self.compute_metric_by_diff(
            exec_results=model_responses,
            filter_used=filter_used 
        )

        if filter_used:
            filter_value = f"_{filter_used[1]}"
        else:
            filter_value = ''
            
        with open(
            os.path.join(
                self.generator_config.data_output_folder,
                f"ves{filter_value}.json"
            ), "w"
        ) as json_file:
            json.dump(score_dict, json_file)
        
        self.print_data(results=score_dict, metric_name="ves")
        return score_dict

    # TODO: redundant function has a scope to optimize 
    def print_data(self, results: dict, metric_name: str):
        print(f"{'='*21}   {metric_name.upper()}    {'='*21}") 
        table_data = [[key, value[0], value[1]] for key, value in results.items()]
        headers = ["Category", "VES (%)", "total questions"]
        print(tabulate(table_data, headers, tablefmt="grid"))