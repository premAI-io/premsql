from textwrap import dedent
from typing import Literal, Optional

from premsql.executors.base import BaseExecutor
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger
from premsql.pipelines.base import Text2SQLWorkerBase
from premsql.pipelines.baseline.prompts import (
    BASELINE_TEXT2SQL_TABLE_SELECTION_PROMPT,
    BASELINE_TEXT2SQL_WORKER_ERROR_HANDLING_PROMPT,
    BASELINE_TEXT2SQL_WORKER_PROMPT,
    BASELINE_TEXT2SQL_WORKER_PROMPT_NO_FEWSHOT,
)
from premsql.pipelines.models import Text2SQLWorkerOutput
from premsql.pipelines.utils import execute_and_render_result

logger = setup_console_logger("[BASELINE-TEXT2SQL-WORKER]")


class BaseLineText2SQLWorker(Text2SQLWorkerBase):
    def __init__(
        self,
        db_connection_uri: str,
        generator: Text2SQLGeneratorBase,
        helper_model: Optional[Text2SQLGeneratorBase] = None,
        executor: Optional[BaseExecutor] = None,
        include_tables: Optional[list] = None,
        exclude_tables: Optional[list] = None,
        auto_filter_tables: Optional[bool] = False,
    ):
        super().__init__(
            db_connection_uri=db_connection_uri,
            generator=generator,
            executor=executor,
            include_tables=include_tables,
            exclude_tables=exclude_tables,
        )

        self.corrector = helper_model
        self.table_filer_worker = helper_model
        self.auto_filter_tables = auto_filter_tables

    @staticmethod
    def show_dataframe(output: Text2SQLWorkerOutput):
        import pandas as pd

        if output.output_dataframe:
            df = pd.DataFrame(
                output.output_dataframe["data"],
                columns=output.output_dataframe["columns"],
            )
            return df
        return pd.DataFrame({})

    def filer_tables_from_schema(
        self, question: str, additional_input: Optional[str] = None
    ) -> dict:
        prompt = BASELINE_TEXT2SQL_TABLE_SELECTION_PROMPT.format(
            schema=self.db.get_context()["table_info"],
            additional_info=additional_input,
            question=question,
        )
        all_tables = self.db.get_usable_table_names()
        try:
            to_include = []
            output = self.corrector.generate({"prompt": prompt}, postprocess=False)
            output = eval(output)
            for table in all_tables:
                if table in output["include"]:
                    to_include.append(table)
        except Exception as e:
            logger.info(f"Error while selecting table: {e}")
            to_include = all_tables
        return to_include

    def _create_prompt(
        self,
        question: str,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
        prompt_template: Optional[str] = BASELINE_TEXT2SQL_WORKER_PROMPT,
    ) -> str:
        to_include = self.filer_tables_from_schema(
            question=question, additional_input=additional_knowledge
        )
        logger.info(f"Taking the following selected table in schema: {to_include}")
        self.db = self.initialize_database(
            db_connection_uri=self.db_connection_uri, include_tables=to_include
        )
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

        if fewshot_dict is None:
            prompt = BASELINE_TEXT2SQL_WORKER_PROMPT_NO_FEWSHOT.format(
                schemas=schema_prompt,
                additional_knowledge=additional_knowledge,
                question=question,
            )
        else:
            prompt = prompt_template.format(
                schemas=schema_prompt,
                additional_knowledge=additional_knowledge,
                few_shot_examples=knowledge_prompt,
                question=question,
            )
        return prompt

    def run(
        self,
        question: str,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
        temperature: Optional[float] = 0.1,
        max_new_tokens: Optional[int] = 256,
        render_results_using: Optional[Literal["json", "dataframe"]] = "json",
        prompt_template: Optional[str] = BASELINE_TEXT2SQL_WORKER_PROMPT,
        error_handling_prompt_template: Optional[
            str
        ] = BASELINE_TEXT2SQL_WORKER_ERROR_HANDLING_PROMPT,
        **kwargs,
    ) -> Text2SQLWorkerOutput:
        prompt = self._create_prompt(
            question=question,
            additional_knowledge=additional_knowledge,
            fewshot_dict=fewshot_dict,
            prompt_template=prompt_template,
        )
        generated_sql = self.generator.execution_guided_decoding(
            data_blob={"prompt": prompt, "db_path": self.db_connection_uri},
            executor=self.executor,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            max_retries=5,
            postprocess=True,
            **kwargs,
        )

        result = execute_and_render_result(
            db=self.db, sql=generated_sql, using=render_results_using
        )

        if result["error_from_model"] is not None:
            logger.info("=> Going for final correction ...")
            generated_sql = self.do_correction(
                question=question,
                result=result,
                additional_knowledge=additional_knowledge,
                fewshot_dict=fewshot_dict,
                prompt_template=prompt_template,
                error_handling_prompt_template=error_handling_prompt_template,
                **kwargs,
            )
            result = execute_and_render_result(
                db=self.db, sql=generated_sql, using=render_results_using
            )

        return Text2SQLWorkerOutput(
            db_connection_uri=self.db_connection_uri,
            sql_string=generated_sql,
            sql_reasoning=None,
            input_dataframe=None,
            output_dataframe=result["dataframe"],  # Truncating to
            question=question,
            error_from_model=result["error_from_model"],
            additional_input={
                "additional_knowledge": additional_knowledge,
                "fewshot_dict": fewshot_dict,
                "temperature": temperature,
                "max_new_tokens": max_new_tokens,
                **kwargs,
            },
        )

    def do_correction(
        self,
        question: str,
        result: dict,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
        prompt_template: Optional[str] = BASELINE_TEXT2SQL_WORKER_PROMPT,
        error_handling_prompt_template: Optional[
            str
        ] = BASELINE_TEXT2SQL_WORKER_ERROR_HANDLING_PROMPT,
        **kwargs,
    ):
        if not self.corrector:
            logger.info("Corrector model not defined, no furthur correction possible.")

        error_prompt = error_handling_prompt_template.format(
            existing_prompt=self._create_prompt(
                question=question,
                additional_knowledge=additional_knowledge,
                fewshot_dict=fewshot_dict,
                prompt_template=prompt_template,
            ),
            error_msg=result["error_from_model"],
            sql=result["sql_string"],
        )
        return self.generator.generate(
            data_blob={"prompt": error_prompt}, postprocess=True, **kwargs
        )
