import sys
import json
import multiprocessing as mp
from typing import Optional, List, Tuple, Dict
from func_timeout import func_timeout, FunctionTimedOut


class ExecutorBase:
    def __init__(self):
        self.exec_result = []

    def result_callback(self, result: dict):
        self.exec_result.append(result)

    def load_json(self, dir: str) -> dict:
        with open(dir, "r") as j:
            contents = json.loads(j.read())
        return contents

    def sort_results(self, list_of_dicts: List[Dict]) -> List[Dict]:
        return sorted(list_of_dicts, key=lambda x: x["sql_idx"])

    def run_sqls_parallel(
        self,
        sqls: List[Tuple[str, str]],
        db_places: List[str],
        num_cpus: int = 1,
        meta_time_out: float = 30.0,
    ):
        pool = mp.Pool(processes=num_cpus)
        for i, sql_pair in enumerate(sqls):
            predicted_sql, ground_truth = sql_pair
            pool.apply_async(
                self.execute_model,
                args=(predicted_sql, ground_truth, db_places[i], i, meta_time_out),
                callback=self.result_callback,
            )
        pool.close()
        pool.join()

    def package_sqls(
        self,
        sql_path: str,
        db_root_path: str,
        mode: str = "gpt",
        data_mode: str = "dev",
        num_rows: Optional[int] = None,
    ) -> Tuple[List[str], List[str]]:
        clean_sqls = []
        db_path_list = []

        if mode == "gpt":
            sql_data = json.load(open(sql_path, "r"))
            for idx, sql_str in sql_data.items():
                if type(sql_str) == str:
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

                for idx, sql_str in enumerate(sql_txt):
                    sql, db_name = sql_str.strip().split("\t")
                    clean_sqls.append(sql)
                    db_path_list.append(
                        db_root_path + db_name + "/" + db_name + ".sqlite"
                    )

        return clean_sqls, db_path_list

    def execute_model(
        self,
        predicted_sql: str,
        ground_truth: str,
        db_place: str,
        idx: int,
        meta_time_out: float,
    ) -> dict:
        try:
            res = func_timeout(
                meta_time_out,
                self.execute_sql,
                args=(predicted_sql, ground_truth, db_place),
            )
        except KeyboardInterrupt:
            sys.exit(0)
        except FunctionTimedOut:
            result = [(f"timeout",)]
            res = 0
        except Exception as e:
            result = [(f"error",)]
            res = 0
        result = {"sql_idx": idx, "res": res}
        return result

    def print_data(
        self, score_lists: List[float], count_lists: List[int], metric="accuracy"
    ):
        levels = ["simple", "moderate", "challenging", "total"]
        print("{:20} {:20} {:20} {:20} {:20}".format("", *levels))
        print("{:20} {:<20} {:<20} {:<20} {:<20}".format("count", *count_lists))

        print(f"{'='*41}   {metric.upper()}    {'='*41}")
        print(
            "{:20} {:<20.2f} {:<20.2f} {:<20.2f} {:<20.2f}".format(
                "accuracy", *score_lists
            )
        )
