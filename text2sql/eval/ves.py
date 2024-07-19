import sys
import json
import numpy as np
import sqlite3
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut
import time
import math
from typing import List, Tuple, Dict, Optional
from text2sql.settings import SQLGeneratorConfig, MetricConfig


class SQLVesEvaluator:
    def __init__(self):
        self.exec_result = []

    def load_json(self, dir: str) -> dict:
        with open(dir, "r") as j:
            contents = json.loads(j.read())
        return contents

    def result_callback(self, result: dict):
        self.exec_result.append(result)

    def clean_abnormal(self, input: np.ndarray) -> List[float]:
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
        diff_list = []
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        cursor.execute(ground_truth)
        ground_truth_res = cursor.fetchall()
        time_ratio = 0
        if set(predicted_res) == set(ground_truth_res):
            for _ in range(iterate_num):
                predicted_time = self.execute_sql(predicted_sql, db_path)
                ground_truth_time = self.execute_sql(ground_truth, db_path)
                diff_list.append(ground_truth_time / predicted_time)
            processed_diff_list = self.clean_abnormal(diff_list)
            time_ratio = sum(processed_diff_list) / len(processed_diff_list)
        return time_ratio

    def execute_model(
        self,
        predicted_sql: str,
        ground_truth: str,
        db_place: str,
        idx: int,
        iterate_num: int,
        meta_time_out: float,
    ) -> dict:
        try:
            time_ratio = func_timeout(
                meta_time_out * iterate_num,
                self.iterated_execute_sql,
                args=(predicted_sql, ground_truth, db_place, iterate_num),
            )
        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut:
            time_ratio = 0
        except Exception:
            time_ratio = 0
        result = {"sql_idx": idx, "time_ratio": time_ratio}
        return result

    def package_sqls(
        self,
        sql_path: str,
        db_root_path: str,
        mode: str = "gpt",
        data_mode: str = "dev",
        num_rows: Optional[int] = None 
    ) -> Tuple[List[str], List[str]]:
        clean_sqls = []
        db_path_list = []
        if mode == "gpt":
            sql_data = json.load(open(sql_path, "r"))
            for idx, sql_str in sql_data.items():
                if isinstance(sql_str, str):
                    sql, db_name = sql_str.split("\t----- bird -----\t")
                else:
                    sql, db_name = " ", "financial"
                clean_sqls.append(sql)
                db_path_list.append(db_root_path + db_name + "/" + db_name + ".sqlite")
        elif mode == "gt":
            with open(sql_path + data_mode + ".sql") as sqls:
                sql_txt = sqls.readlines()
                if num_rows:
                    sql_txt = sql_txt[:num_rows]
                for sql_str in sql_txt:
                    sql, db_name = sql_str.strip().split("\t")
                    clean_sqls.append(sql)
                    db_path_list.append(
                        db_root_path + db_name + "/" + db_name + ".sqlite"
                    )
        return clean_sqls, db_path_list

    def run_sqls_parallel(
        self,
        sqls: List[Tuple[str, str]],
        db_places: List[str],
        num_cpus: int = 1,
        iterate_num: int = 100,
        meta_time_out: float = 30.0,
    ):
        pool = mp.Pool(processes=num_cpus)
        for i, sql_pair in enumerate(sqls):
            predicted_sql, ground_truth = sql_pair
            pool.apply_async(
                self.execute_model,
                args=(
                    predicted_sql,
                    ground_truth,
                    db_places[i],
                    i,
                    iterate_num,
                    meta_time_out,
                ),
                callback=self.result_callback,
            )
        pool.close()
        pool.join()

    def sort_results(self, list_of_dicts: List[Dict]) -> List[Dict]:
        return sorted(list_of_dicts, key=lambda x: x["sql_idx"])

    def compute_ves(self, exec_results: List[Dict]) -> float:
        num_queries = len(exec_results)
        total_ratio = 0
        for result in exec_results:
            if result["time_ratio"] != 0:
                total_ratio += math.sqrt(result["time_ratio"]) * 100
        return total_ratio / num_queries

    def compute_ves_by_diff(
        self,
        exec_results: List[Dict],
        diff_json_path: str,
        num_rows: Optional[int] = None,
    ) -> Tuple:
        num_queries = len(exec_results)
        contents = self.load_json(diff_json_path)
        if num_rows:
            contents = contents[:num_rows]

        simple_results, moderate_results, challenging_results = [], [], []
        for i, content in enumerate(contents):
            if content["difficulty"] == "simple":
                simple_results.append(exec_results[i])
            elif content["difficulty"] == "moderate":
                moderate_results.append(exec_results[i])
            elif content["difficulty"] == "challenging":
                challenging_results.append(exec_results[i])
        
        try:
            simple_ves = self.compute_ves(simple_results)
        except Exception:
            simple_ves = 0 
        
        try:
            moderate_ves = self.compute_ves(moderate_results)
        except Exception:
            moderate_ves = 0
        
        try:
            challenging_ves = self.compute_ves(challenging_results)
        except Exception:
            challenging_ves = 0
        
        try:
            all_ves = self.compute_ves(exec_results)
        except Exception:
            all_ves = 0
        
        count_lists = [
            len(simple_results),
            len(moderate_results),
            len(challenging_results),
            num_queries,
        ]
        return simple_ves, moderate_ves, challenging_ves, all_ves, count_lists

    def print_data(self, score_lists: List[float], count_lists: List[int]):
        levels = ["simple", "moderate", "challenging", "total"]
        print("{:20} {:20} {:20} {:20} {:20}".format("", *levels))
        print("{:20} {:<20} {:<20} {:<20} {:<20}".format("count", *count_lists))
        print(f"{'='*41}   VES    {'='*41}")
        print(
            "{:20} {:<20.2f} {:<20.2f} {:<20.2f} {:<20.2f}".format("ves", *score_lists)
        )

    def execute(
        self,
        generator_config: SQLGeneratorConfig,
        metric_config: MetricConfig,
        num_rows: Optional[int] = None,
    ):
        pred_queries, db_paths = self.package_sqls(
            generator_config.data_output_path,
            generator_config.db_root_path,
            mode="gpt",
            data_mode=generator_config.mode,
            num_rows=num_rows,
        )
        gt_queries, _ = self.package_sqls(
            metric_config.gt_path,
            generator_config.db_root_path,
            mode="gt",
            data_mode=generator_config.mode,
            num_rows=num_rows,
        )
        query_pairs = list(zip(pred_queries, gt_queries))
        self.run_sqls_parallel(
            query_pairs,
            db_places=db_paths,
            num_cpus=metric_config.num_cpus,
            meta_time_out=metric_config.meta_time_out,
        )
        exec_result = self.sort_results(self.exec_result)
        print("start calculate")
        simple_ves, moderate_ves, challenging_ves, ves, count_lists = (
            self.compute_ves_by_diff(
                exec_result, metric_config.diff_json_path, num_rows=num_rows
            )
        )
        score_lists = [simple_ves, moderate_ves, challenging_ves, ves]
        self.print_data(score_lists, count_lists)
        print("=" * 91)
        print("Finished evaluation")
