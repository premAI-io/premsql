# metrics.py

import os
import sys
import time
import json
import sqlite3
import math
import numpy as np
from typing import Optional, List, Tuple, Dict
from func_timeout import func_timeout, FunctionTimedOut

from text2sql.settings import SQLGeneratorConfig, MetricConfig
from text2sql.eval.executor_base import ExecutorBase


class SQLExecutorEX(ExecutorBase):
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

    def compute_acc_by_diff(
        self,
        exec_results: List[Dict],
        diff_json_path: str,
        num_rows: Optional[int] = None,
    ) -> Tuple:
        num_queries = len(exec_results)
        results = [res["res"] for res in exec_results]
        contents = self.load_json(diff_json_path)

        if num_rows:
            contents = contents[:num_rows]
        simple_results, moderate_results, challenging_results = [], [], []

        for i, content in enumerate(contents):
            if content["difficulty"] == "simple":
                simple_results.append(exec_results[i])

            if content["difficulty"] == "moderate":
                moderate_results.append(exec_results[i])

            if content["difficulty"] == "challenging":
                challenging_results.append(exec_results[i])

        try:
            simple_acc = sum([res["res"] for res in simple_results]) / len(
                simple_results
            )
        except Exception:
            simple_acc = 0

        try:
            moderate_acc = sum([res["res"] for res in moderate_results]) / len(
                moderate_results
            )
        except Exception:
            moderate_acc = 0

        try:
            challenging_acc = sum([res["res"] for res in challenging_results]) / len(
                challenging_results
            )
        except Exception:
            challenging_acc = 0

        all_acc = sum(results) / num_queries
        count_lists = [
            len(simple_results),
            len(moderate_results),
            len(challenging_results),
            num_queries,
        ]
        return (
            simple_acc * 100,
            moderate_acc * 100,
            challenging_acc * 100,
            all_acc * 100,
            count_lists,
        )

    def execute_ex(
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

        simple_acc, moderate_acc, challenging_acc, acc, count_lists = (
            self.compute_acc_by_diff(
                exec_result, metric_config.diff_json_path, num_rows
            )
        )
        score_lists = [simple_acc, moderate_acc, challenging_acc, acc]
        score_dict = {
            "simple_acc": (simple_acc, count_lists[0]),
            "moderate_acc": (moderate_acc, count_lists[1]),
            "challenging_acc": (challenging_acc, count_lists[2]),
            "overall": (acc, count_lists[3]),
        }
        with open(
            os.path.join(
                generator_config.data_output_folder,
                (
                    "score_acc_cot.json"
                    if generator_config.chain_of_thought
                    else "score_acc.json"
                ),
            ),
            "w",
        ) as json_file:
            json.dump(score_dict, json_file)

        self.print_data(score_lists, count_lists)
        print("=" * 91)
        print("Finished evaluation")
        return score_dict


class SQLExecutorVES(ExecutorBase):
    def clean_abnormal(self, input):
        input = np.asarray(input)
        processed_list = []
        mean = np.mean(input, axis=0)
        std = np.std(input, axis=0)
        for x in input:
            if x < mean + 3 * std and x > mean - 3 * std:
                processed_list.append(x)
        return processed_list

    def execute_sql(self, sql, db_path):
        # Connect to the database
        conn = sqlite3.connect(db_path)
        # Create a cursor object
        cursor = conn.cursor()
        start_time = time.time()
        cursor.execute(sql)
        exec_time = time.time() - start_time
        return exec_time

    def iterated_execute_sql(self, predicted_sql, ground_truth, db_path, iterate_num):
        conn = sqlite3.connect(db_path)
        diff_list = []
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        cursor.execute(ground_truth)
        ground_truth_res = cursor.fetchall()
        time_ratio = 0
        if set(predicted_res) == set(ground_truth_res):
            for i in range(iterate_num):
                predicted_time = self.execute_sql(predicted_sql, db_path)
                ground_truth_time = self.execute_sql(ground_truth, db_path)
                diff_list.append(ground_truth_time / predicted_time)
            processed_diff_list = self.clean_abnormal(diff_list)
            time_ratio = sum(processed_diff_list) / len(processed_diff_list)
        return time_ratio

    def execute_model(
        self, predicted_sql, ground_truth, db_place, idx, iterate_num, meta_time_out
    ):
        try:
            time_ratio = func_timeout(
                meta_time_out * iterate_num,
                self.iterated_execute_sql,
                args=(predicted_sql, ground_truth, db_place, iterate_num),
            )
        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut:
            result = [(f"timeout",)]
            time_ratio = 0
        except Exception as e:
            result = [(f"error",)]  # possibly len(query) > 512 or not executable
            time_ratio = 0
        result = {"sql_idx": idx, "time_ratio": time_ratio}
        return result

    def compute_ves(self, exec_results):
        num_queries = len(exec_results)
        total_ratio = 0
        count = 0

        for _, result in enumerate(exec_results):
            if result["time_ratio"] != 0:
                count += 1
            total_ratio += math.sqrt(result["time_ratio"]) * 100
        ves = total_ratio / num_queries
        return ves

    def compute_ves_by_diff(
        self, exec_results, diff_json_path, num_rows: Optional[int] = None
    ):
        num_queries = len(exec_results)
        contents = self.load_json(diff_json_path)
        if num_rows:
            contents = contents[:num_rows]

        simple_results, moderate_results, challenging_results = [], [], []
        for i, content in enumerate(contents):
            if content["difficulty"] == "simple":
                simple_results.append(exec_results[i])
            if content["difficulty"] == "moderate":
                moderate_results.append(exec_results[i])
            if content["difficulty"] == "challenging":
                challenging_results.append(exec_results[i])
        simple_ves = self.compute_ves(simple_results)
        moderate_ves = self.compute_ves(moderate_results)
        challenging_ves = self.compute_ves(challenging_results)
        all_ves = self.compute_ves(exec_results)
        count_lists = [
            len(simple_results),
            len(moderate_results),
            len(challenging_results),
            num_queries,
        ]
        return simple_ves, moderate_ves, challenging_ves, all_ves, count_lists

    def execute_ves(
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
                exec_result, metric_config.diff_json_path, num_rows
            )
        )

        score_lists = [simple_ves, moderate_ves, challenging_ves, ves]
        score_dict = {
            "simple_ves": (simple_ves, count_lists[0]),
            "moderate_ves": (moderate_ves, count_lists[1]),
            "challenging_ves": (challenging_ves, count_lists[2]),
            "overall": (ves, count_lists[3]),
        }

        with open(
            os.path.join(
                generator_config.data_output_folder,
                (
                    "score_ves_cot.json"
                    if generator_config.chain_of_thought
                    else "score_ves.json"
                ),
            ),
            "w",
        ) as json_file:
            json.dump(score_dict, json_file)

        self.print_data(score_lists, count_lists, metric="ves")
        print("=" * 91)
        print("Finished evaluation")
        return score_dict
