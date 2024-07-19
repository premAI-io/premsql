import json
import os
import sqlite3
from typing import Dict
from text2sql.eval import prompts


def new_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_db_schemas(bench_root: str, db_name: str) -> Dict[str, str]:
    """
    Read an sqlite file, and return the CREATE commands for each of the tables in the database.
    """
    asdf = "database" if bench_root == "spider" else "databases"
    with sqlite3.connect(
        f"file:{bench_root}/{asdf}/{db_name}/{db_name}.sqlite?mode=ro", uri=True
    ) as conn:
        # conn.text_factory = bytes
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schemas = {}
        for table in tables:
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(
                    table[0]
                )
            )
            schemas[table[0]] = cursor.fetchone()[0]

        return schemas


def nice_look_table(column_names: list, values: list):
    rows = []
    # Determine the maximum width of each column
    widths = [
        max(len(str(value[i])) for value in values + [column_names])
        for i in range(len(column_names))
    ]

    # Print the column names
    header = "".join(
        f"{column.rjust(width)} " for column, width in zip(column_names, widths)
    )
    # print(header)
    # Print the values
    for value in values:
        row = "".join(f"{str(v).rjust(width)} " for v, width in zip(value, widths))
        rows.append(row)
    rows = "\n".join(rows)
    final_output = header + "\n" + rows
    return final_output


def generate_schema_prompt(db_path):
    # extract create ddls
    """
    :param root_place:
    :param db_name:
    :return:
    """
    full_schema_prompt_list = []
    conn = sqlite3.connect(db_path)
    # Create a cursor object
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    schemas = {}
    for table in tables:
        if table == "sqlite_sequence":
            continue
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(
                table[0]
            )
        )
        create_prompt = cursor.fetchone()[0]
        schemas[table[0]] = create_prompt

    for k, v in schemas.items():
        full_schema_prompt_list.append(v)

    schema_prompt = "\n\n".join(full_schema_prompt_list)

    return schema_prompt


def generate_comment_prompt(question, knowledge=None):
    question_prompt = "-- {}".format(question)
    knowledge_prompt = "-- External Knowledge: {}".format(knowledge)

    if not knowledge_prompt:
        result_prompt = prompts.PATTERN_PROMPT_NO_KG + "\n" + question_prompt
    else:
        result_prompt = (
            knowledge_prompt + "\n" + prompts.PATTERN_PROMPT_KG + "\n" + question_prompt
        )

    return result_prompt


def few_shot():
    one_shot_demo = (
        prompts.INI_TABLE_KG
        + "\n"
        + prompts.INI_PROMPT_KG
        + "\n"
        + prompts.INI_COT_RESULT_KG
    )
    return one_shot_demo


def few_shot_no_kg():
    one_shot_demo = (
        prompts.INI_TABLE_NO_KG
        + "\n"
        + prompts.INI_PROMPT_NO_KG
        + "\n"
        + prompts.INI_COT_RESULT_NO_KG
    )
    return one_shot_demo


def generate_combined_prompts_one(db_path, question, knowledge=None):
    schema_prompt = generate_schema_prompt(db_path)
    comment_prompt = generate_comment_prompt(question, knowledge)
    combined_prompts = (
        schema_prompt + "\n\n" + comment_prompt + prompts.COT_WIZARD + "\nSELECT "
    )
    return combined_prompts


def question_package(data_json, knowledge=False):
    question_list = []
    for data in data_json:
        question_list.append(data["question"])

    return question_list


def knowledge_package(data_json, knowledge=False):
    knowledge_list = []
    for data in data_json:
        knowledge_list.append(data["evidence"])

    return knowledge_list


def decouple_question_schema(datasets, db_root_path):
    question_list = []
    db_path_list = []
    knowledge_list = []
    for i, data in enumerate(datasets):
        question_list.append(data["question"])
        cur_db_path = db_root_path + data["db_id"] + "/" + data["db_id"] + ".sqlite"
        db_path_list.append(cur_db_path)
        knowledge_list.append(data["evidence"])

    return question_list, db_path_list, knowledge_list


def generate_sql_file(sql_lst, output_path=None):
    result = {}
    for i, sql in enumerate(sql_lst):
        result[i] = sql

    if output_path:
        directory_path = os.path.dirname(output_path)
        print(directory_path)
        new_directory(directory_path)
        json.dump(result, open(output_path, "w"), indent=4)

    return result
