from textwrap import dedent
from typing import Optional, Union

import sqlparse

from premsql.executors.from_langchain import SQLDatabase, ExecutorUsingLangChain
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger
from premsql.prompts import ERROR_HANDLING_PROMPT, OLD_BASE_TEXT2SQL_PROMPT
from premsql.pipelines.common import execute_and_render_result


logger = setup_console_logger("[SIMPLE-AGENT]")

class SimpleText2SQLAgent:
    def __init__(
        self, 
        dsn_or_db_path: Union[str, SQLDatabase], 
        generator: Text2SQLGeneratorBase,
        corrector: Optional[Text2SQLGeneratorBase]=None,
        executor: Optional[ExecutorUsingLangChain]=None,
        include_tables: Optional[list] = None,
        exclude_tables: Optional[list] = None,
    ) -> None:
        if include_tables is not None and exclude_tables is not None:
            raise ValueError("Either include_tables or exclude_tables can be provided, not both")

        self.db = self._initialize_database(dsn_or_db_path, include_tables, exclude_tables)
        self.generator = generator
        self.corrector = corrector
        self.executor = executor if executor is not None else ExecutorUsingLangChain()
        self.dsn_or_db_path = dsn_or_db_path

        logger.info("SimpleText2SQLAgent is set")

    def _initialize_database(
        self, dsn_or_db_path: str, include_tables: Optional[list]=None, exclude_tables: Optional[list]=None
    ):
        try:
            if isinstance(dsn_or_db_path, str):
                return SQLDatabase.from_uri(
                    dsn_or_db_path, 
                    sample_rows_in_table_info=0,
                    ignore_tables=exclude_tables,
                    include_tables=include_tables
                )
        except Exception as e:
            logger.error(f"Error loading the database: {e}")
            raise RuntimeError(f"Error loading the database: {e}")
    
    
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
        result = execute_and_render_result(
            db=self.db,
            sql=generated_sql,
            using=render_results_using
        )
        
        # This means an error has occured
        if  result["error"] is not None:
            logger.info("=> Going for final correction ...")
            generated_sql = self.do_correction(
                question=question,
                result=result,
            )
            result = execute_and_render_result(
            db=self.db,
            sql=generated_sql,
            using=render_results_using
        )

        return {
            "bot_message": "Here are your fetch results",
            "sql": result["sql"],
            "table": result["table"],
            "plot": None,
            "error": result.get("error", None)
        }
            
    def do_correction(self, question: str, result: dict, **kwargs):
        if self.corrector:
            error_prompt = ERROR_HANDLING_PROMPT.format(
                existing_prompt=self._create_prompt(question=question),
                error_msg=result["error"],
                sql=result["sql"]
            )
            corrected_sql = sqlparse.format(
                self.corrector.generate(
                    data_blob={"prompt": error_prompt},
                    **kwargs  
                )
            )
            return corrected_sql