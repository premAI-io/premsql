import json
import os
import sqlite3
from abc import ABC, abstractmethod
from typing import Optional, Union

from tqdm import tqdm

from text2sql.eval import prompts
from text2sql.settings import EvalConfig


N = 3
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
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        json.dump(result, open(output_path, "w"), indent=4)

    return result


class BaseGenerator(ABC):
    def nice_look_table(self, column_names: list, values: list):
        rows = []
        widths = [
            max(len(str(value[i])) for value in values + [column_names])
            for i in range(len(column_names))
        ]
        header = "".join(
            f"{column.rjust(width)} " for column, width in zip(column_names, widths)
        )
        for value in values:
            row = "".join(f"{str(v).rjust(width)} " for v, width in zip(value, widths))
            rows.append(row)
        rows = "\n".join(rows)
        final_output = header + "\n" + rows
        return final_output

    def generate_schema_prompt(self, db_path: str, num_rows: Optional[int] = None):
        full_schema_prompt_list = []

        conn = sqlite3.connect(db_path)
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
            if num_rows:
                cur_table = table[0]
                if cur_table in ["order", "by", "group"]:
                    cur_table = "`{}`".format(cur_table)

                cursor.execute("SELECT * FROM {} LIMIT {}".format(cur_table, num_rows))
                column_names = [description[0] for description in cursor.description]
                values = cursor.fetchall()
                rows_prompt = self.nice_look_table(
                    column_names=column_names, values=values
                )
                verbose_prompt = "/* \n {} example rows: \n SELECT * FROM {} LIMIT {}; \n {} \n */".format(
                    num_rows, cur_table, num_rows, rows_prompt
                )
                schemas[table[0]] = "{} \n {}".format(create_prompt, verbose_prompt)

        for k, v in schemas.items():
            full_schema_prompt_list.append(v)

        schema_prompt = "\n\n".join(full_schema_prompt_list)
        return schema_prompt

    def generate_comment_prompt(self, question: str, knowledge: Optional[str] = None):
        question_prompt = "-- {}".format(question)
        knowledge_prompt = "-- External Knowledge: {}".format(knowledge)

        if not knowledge_prompt:
            result_prompt = prompts.PATTERN_PROMPT_NO_KG + "\n" + question_prompt
        else:
            result_prompt = (
                knowledge_prompt
                + "\n"
                + prompts.PATTERN_PROMPT_KG
                + "\n"
                + question_prompt
            )

        return result_prompt

    def few_shot(self):
        one_shot_demo = (
            prompts.INI_TABLE_KG
            + "\n"
            + prompts.INI_PROMPT_KG
            + "\n"
            + prompts.INI_COT_RESULT_KG
        )
        return one_shot_demo

    def few_shot_no_kg(self):
        one_shot_demo = (
            prompts.INI_TABLE_NO_KG
            + "\n"
            + prompts.INI_PROMPT_NO_KG
            + "\n"
            + prompts.INI_COT_RESULT_NO_KG
        )
        return one_shot_demo

    def generate_combined_prompts_one(
        self, db_path: str, question: str, knowledge: Optional[str] = None
    ):
        # This is the entry to collect values
        schema_prompt = self.generate_schema_prompt(db_path, num_rows=None)
        comment_prompt = self.generate_comment_prompt(question, knowledge)
        combined_prompts = (
            schema_prompt + "\n\n" + comment_prompt + prompts.COT_WIZARD + "\nSELECT "
        )
        return combined_prompts

    @abstractmethod
    def connect_model(
        self,
        prompt: str,
        max_tokens: Optional[int] = 256,
        temperature: Optional[Union[float, int]] = 0,
        stop: Optional[list[str]] = ["--", "\n\n", ";", "#"],
    ) -> str:
        # We need to process the prompt properly based on the engine
        # and also the output should be a plain text
        raise NotImplementedError

    def collect_response_from_model(
        self,
        db_path_list: list[str],
        question_list: list[str],
        knowledge_list: Optional[list[str]] = None,
        max_tokens: Optional[int] = 256,
        temperature: Optional[Union[float, int]] = 0,
        stop: Optional[list[str]] = ["--", "\n\n", ";", "#"],
    ):
        response_list = []
        for i, question in tqdm(enumerate(question_list[:N]), total=len(question_list[:N])):
            if knowledge_list:
                current_prompt = self.generate_combined_prompts_one(
                    db_path=db_path_list[i],
                    question=question,
                    knowledge=knowledge_list[i],
                )
            else:
                current_prompt = self.generate_combined_prompts_one(
                    db_path=db_path_list[i], question=question
                )

            sql = self.connect_model(
                prompt=current_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )

            db_id = db_path_list[i].split("/")[-1].split(".sqlite")[0]
            sql = sql + "\t----- bird -----\t" + db_id
            response_list.append(sql)
        return response_list

    def generate_sql(
        self,
        eval_config: EvalConfig,
        model_name: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[Union[int, float]] = None,
        stop: Optional[list] = None,
    ):
        eval_data = json.load(open(eval_config.eval_path, "r"))
        question_list, db_path_list, knowledge_list = decouple_question_schema(
            datasets=eval_data, db_root_path=eval_config.db_root_path
        )

        assert len(question_list) == len(db_path_list) == len(knowledge_list)
        if eval_config.use_knowledge == True:
            responses = self.collect_response_from_model(
                db_path_list=db_path_list,
                question_list=question_list,
                knowledge_list=knowledge_list,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )
        else:
            responses = self.collect_response_from_model(
                db_path_list=db_path_list,
                question_list=question_list,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            )

        if eval_config.cot == True:
            output_name = (
                eval_config.data_output_path
                + "predict_"
                + eval_config.mode
                + "_cot.json"
            )
        else:
            output_name = (
                eval_config.data_output_path + "predict_" + eval_config.mode + ".json"
            )
        generate_sql_file(sql_lst=responses, output_path=output_name)
        print(
            "successfully collect results from {} for {} evaluation; Use knowledge: {}; Use COT: {}".format(
                model_name,
                eval_config.mode,
                eval_config.use_knowledge,
                eval_config.cot,
            )
        )

