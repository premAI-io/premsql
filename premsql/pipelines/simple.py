from textwrap import dedent
from typing import Optional, Union

import pandas as pd
import sqlparse
from premai import Prem
from premsql.prompts import ERROR_HANDLING_PROMPT, OLD_BASE_TEXT2SQL_PROMPT
from premsql.executors.from_langchain import ExecutorUsingLangChain, SQLDatabase
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger
from tabulate import tabulate

logger = setup_console_logger("[SIMPLE-AGENT]")


class SimpleText2SQLAgent:
    def __init__(
        self,
        dsn_or_db_path: Union[str, SQLDatabase],
        generator: Text2SQLGeneratorBase,
        premai_project_id: Optional[str] = None,
        premai_api_key: Optional[str] = None,
    ):
        self.db = (
            SQLDatabase.from_uri(dsn_or_db_path, sample_rows_in_table_info=0)
            if isinstance(dsn_or_db_path, str)
            else dsn_or_db_path
        )
        self.dsn_or_db_path = dsn_or_db_path
        self.generator = generator
        self.executor = ExecutorUsingLangChain()
        self.project_id = premai_project_id

        self.corrector = (
            Prem(api_key=premai_api_key)
            if premai_project_id and premai_api_key
            else None
        )
        logger.info("Everything set")

        if self.corrector:
            logger.info("Using gpt-4o as the final corrector")

    def _create_prompt(
        self,
        question: str,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
        prompt_template: Optional[str] = OLD_BASE_TEXT2SQL_PROMPT,
    ):
        schema_prompt = self.db.get_context()["table_info"]
        knowledge_prompt = ""

        if fewshot_dict is not None:
            template = dedent(
                """
            Question: {question}
            SQL: {sql}
            """
            )
            knowledge_prompt = "".join(
                template.format(question=sample_question, sql=sample_sql)
                for sample_question, sample_sql in fewshot_dict.items()
            )

        prompt = prompt_template.format(
            schemas=schema_prompt,
            additional_knowledge=additional_knowledge,
            few_shot_examples=knowledge_prompt,
            question=question,
        )
        return prompt

    def query(
        self,
        question: str,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
        prompt_template: Optional[str] = OLD_BASE_TEXT2SQL_PROMPT,
        temperature: Optional[float] = 0.1,
        max_new_tokens: Optional[int] = 256,
        render_results_using: Optional[str] = "dataframe",
        **kwargs
    ):
        prompt = self._create_prompt(
            question=question,
            additional_knowledge=additional_knowledge,
            fewshot_dict=fewshot_dict,
            prompt_template=prompt_template,
        )
        generated_sql = self.generator.execution_guided_decoding(
            data_blob={"prompt": prompt, "db_path": self.dsn_or_db_path},
            executor=self.executor,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            max_retries=5,
            postprocess=True,
            **kwargs
        )
        result = self.render_result(sql=generated_sql, using=render_results_using)

        if result["error"] is not None:
            logger.info("=> Going for final correction ...")
            return self.correct_with_gpt(
                question=question, result=result, render_using=render_results_using
            )
        return result

    def render_result(self, sql, using="tabulate"):
        result = self.db.run_no_throw(command=sql, fetch="cursor")

        # This assumes that an error happens
        if isinstance(result, str):
            to_show = {
                "table": pd.DataFrame(data=[{"error": result}]),
                "error": result,
                "sql": sql,
            }

        else:
            table = pd.DataFrame(data=result.fetchall(), columns=result.keys())
            to_show = {"table": table, "error": None, "sql": sql}

        if using == "tabulate":
            to_show["table"] = tabulate(
                to_show["table"], headers="keys", tablefmt="psql", showindex=False
            )

        return to_show

    def correct_with_gpt(self, question, result: dict, render_using: str):
        if self.corrector:
            error_prompt = ERROR_HANDLING_PROMPT.format(
                existing_prompt=self._create_prompt(question=question),
                error_msg=result["error"],
                sql=result["sql"],
            )
            corrected_sql = sqlparse.format(
                self.corrector.chat.completions.create(
                    project_id=self.project_id,
                    model="gpt-4o",
                    messages=[{"role": "user", "content": error_prompt}],
                )
                .choices[0]
                .message.content.split("# SQL:")[-1]
                .strip()
            )

            return self.render_result(sql=corrected_sql, using=render_using)
        return result
