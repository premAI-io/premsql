import json
import math
import multiprocessing as mp
import sqlite3
import sys
import time

import numpy as np
from func_timeout import FunctionTimedOut, func_timeout

# Initialize the global variable
exec_result = []

def result_callback(result):
    global exec_result
    exec_result.append(result)

def clean_abnormal(input):
    input = np.asarray(input)
    processed_list = []
    mean = np.mean(input, axis=0)
    std = np.std(input, axis=0)
    for x in input:
        if x < mean + 3 * std and x > mean - 3 * std:
            processed_list.append(x)
    return processed_list

def execute_sql(sql, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    start_time = time.time()
    cursor.execute(sql)
    exec_time = time.time() - start_time
    return exec_time

def iterated_execute_sql(predicted_sql, ground_truth, db_path, iterate_num):
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
            predicted_time = execute_sql(predicted_sql, db_path)
            ground_truth_time = execute_sql(ground_truth, db_path)
            diff_list.append(ground_truth_time / predicted_time)
        processed_diff_list = clean_abnormal(diff_list)
        time_ratio = sum(processed_diff_list) / len(processed_diff_list)
    return time_ratio

def execute_model(predicted_sql, ground_truth, db_place, idx, iterate_num, meta_time_out):
    try:
        time_ratio = func_timeout(
            meta_time_out * iterate_num,
            iterated_execute_sql,
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

N = 3

def package_sqls(sql_path, db_root_path, mode="gpt", data_mode="dev"):
    clean_sqls = []
    db_path_list = []
    if mode == "gpt":
        sql_data = json.load(open(sql_path + "predict_" + data_mode + ".json", "r"))
        for idx, sql_str in sql_data.items():
            if type(sql_str) == str:
                sql, db_name = sql_str.split("\t----- bird -----\t")
            else:
                sql, db_name = " ", "financial"
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + "/" + db_name + ".sqlite")

    elif mode == "gt":
        sqls = open(sql_path + data_mode + ".sql")  #'_gold.sql')
        sql_txt = sqls.readlines()
        for idx, sql_str in enumerate(sql_txt[:N]):
            sql, db_name = sql_str.strip().split("\t")
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + "/" + db_name + ".sqlite")

    return clean_sqls, db_path_list

def run_sqls_parallel(sqls, db_places, num_cpus=1, iterate_num=100, meta_time_out=30.0):
    global exec_result
    exec_result = []
    pool = mp.Pool(processes=num_cpus)
    for i, sql_pair in enumerate(sqls):
        predicted_sql, ground_truth = sql_pair
        pool.apply_async(
            execute_model,
            args=(
                predicted_sql,
                ground_truth,
                db_places[i],
                i,
                iterate_num,
                meta_time_out,
            ),
            callback=result_callback,
        )
    pool.close()
    pool.join()

def sort_results(list_of_dicts):
    return sorted(list_of_dicts, key=lambda x: x["sql_idx"])

def compute_ves(exec_results):
    num_queries = len(exec_results)
    total_ratio = 0
    count = 0

    for i, result in enumerate(exec_results):
        if result["time_ratio"] != 0:
            count += 1
        total_ratio += math.sqrt(result["time_ratio"]) * 100
    ves = total_ratio / num_queries
    return ves

def load_json(dir):
    with open(dir, "r") as j:
        contents = json.loads(j.read())
    return contents

def compute_ves_by_diff(exec_results, diff_json_path):
    num_queries = len(exec_results)
    contents = load_json(diff_json_path)[:N]
    print("-----------")
    print(len(contents), len(exec_results))

    simple_results, moderate_results, challenging_results = [], [], []
    for i, content in enumerate(contents):
        if content["difficulty"] == "simple":
            simple_results.append(exec_results[i])
        if content["difficulty"] == "moderate":
            moderate_results.append(exec_results[i])
        if content["difficulty"] == "challenging":
            challenging_results.append(exec_results[i])
    try:
        simple_ves = compute_ves(simple_results)
    except Exception:
        simple_ves = 0

    try:
        moderate_ves = compute_ves(moderate_results)
    except Exception:
        moderate_ves = 0

    try:
        challenging_ves = compute_ves(challenging_results)
    except Exception:
        challenging_ves = 0

    try:
        all_ves = compute_ves(exec_results)
    except Exception:
        all_ves = 0
    
    
    count_lists = [
        len(simple_results),
        len(moderate_results),
        len(challenging_results),
        num_queries,
    ]
    return simple_ves, moderate_ves, challenging_ves, all_ves, count_lists

def print_data(score_lists, count_lists):
    levels = ["simple", "moderate", "challenging", "total"]
    print("{:20} {:20} {:20} {:20} {:20}".format("", *levels))
    print("{:20} {:<20} {:<20} {:<20} {:<20}".format("count", *count_lists))

    print(f"{'='*41}    VES   {'='*41}")
    print("{:20} {:<20.2f} {:<20.2f} {:<20.2f} {:<20.2f}".format("ves", *score_lists))

def evaluate_sql(
    predicted_sql_path,
    ground_truth_path,
    data_mode,
    db_root_path,
    num_cpus=1,
    meta_time_out=30.0,
    mode_gt='gt',
    mode_predict='gpt',
    diff_json_path=''
):
    global exec_result
    exec_result = []
    
    pred_queries, db_paths = package_sqls(predicted_sql_path, db_root_path, mode=mode_predict, data_mode=data_mode)
    gt_queries, db_paths_gt = package_sqls(ground_truth_path, db_root_path, mode=mode_gt, data_mode=data_mode)

    query_pairs = list(zip(pred_queries, gt_queries))
    run_sqls_parallel(query_pairs, db_places=db_paths, num_cpus=num_cpus, meta_time_out=meta_time_out)
    exec_result = sort_results(exec_result)

    print('start calculate')
    simple_ves, moderate_ves, challenging_ves, ves, count_lists = \
        compute_ves_by_diff(exec_result, diff_json_path)
    score_lists = [simple_ves, moderate_ves, challenging_ves, ves]
    print_data(score_lists, count_lists)
    print("="*91)
    print("Finished evaluation")

# Example usage:
# evaluate_sql(predicted_sql_path='path/to/predicted.sql', ground_truth_path='path/to/ground_truth.sql', data_mode='dev', db_root_path='path/to/db/root')



#     command = f"""
# python3 ./text2sql/eval/evaluator.py \\
#     --predicted_sql_path "{eval_config.predicted_sql_path}" \\
#     --ground_truth_path "{eval_config.ground_truth_path}" \\
#     --data_mode {eval_config.data_mode} \\
#     --db_root_path "{eval_config.db_root_path}" \\
#     --num_cpus {eval_config.num_cpus} \\
#     --diff_json_path "{eval_config.diff_json_path}"
# """

#     os.system(command)