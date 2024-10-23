import pandas as pd 
from typing import Optional
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.pipelines.base import WorkerBase
from premsql.pipelines.models import ExitWorkerOutput, FollowupWorkerOutput
from premsql.pipelines.baseline.prompts import BASELINE_FOLLOWUP_WORKER_PROMPT
from premsql.logger import setup_console_logger

logger = setup_console_logger("[BASELINE-FOLLOWUP-WORKER]")

class BaseLineFollowupWorker(WorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase) -> None:
        self.generator = generator
    
    def run(
        self,
        prev_output: ExitWorkerOutput,
        db_schema: str,
        user_feedback: Optional[str] = None,
        prompt_template: Optional[str] = BASELINE_FOLLOWUP_WORKER_PROMPT,
        temperature: Optional[float] = 0.18,
        max_new_tokens: Optional[int] = 128,
    ) -> FollowupWorkerOutput:
        if prev_output.route_taken == "query":
            error = (prev_output.error_from_sql_worker or "") + "\n" + user_feedback
            dataframe = prev_output.sql_output_dataframe
        elif prev_output.route_taken == "plot":
            error = (prev_output.error_from_plot_worker or "") + "\n" + user_feedback
            dataframe = prev_output.plot_input_dataframe
        elif prev_output.route_taken == "analyse":
            dataframe = prev_output.analysis_input_dataframe
            error = (
                (prev_output.error_from_analysis_worker or "") + "\n" + user_feedback
            )
        else:
            error = user_feedback
            dataframe = next(
                (
                    df
                    for df in [
                        prev_output.sql_output_dataframe,
                        prev_output.plot_input_dataframe,
                        prev_output.analysis_input_dataframe,
                    ]
                    if df is not None
                ),
                None,
            )
        
        # convert this dict to dataframe
        if dataframe:
            dataframe = pd.DataFrame(dataframe['data'], columns=dataframe['columns'])
        
        prompt = prompt_template.format(
            schema=db_schema,
            decision=prev_output.route_taken,
            question=prev_output.question,
            dataframe=dataframe,
            analysis=prev_output.analysis,
            error_from_model=error,
        )
        try:
            result = self.generator.generate(
                data_blob={"prompt": prompt},
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                postprocess=False,
            )
            result = eval(result.replace("null", "None"))
            error_from_model = None
            assert "alternate_decision" in result
            assert "suggestion" in result
        except Exception as e:
            result = {
                "alternate_decision": prev_output.route_taken,
                "suggestion": "Worker unable to generate alternative suggestion",
            }
            error_from_model = str(e)
        
        return FollowupWorkerOutput(
            question=user_feedback or prev_output.question,
            error_from_model=error_from_model,
            route_taken=result['alternate_decision'],
            suggestion=result['suggestion'],
            additional_input={
                "temperature": temperature,
                "max_new_tokens": max_new_tokens
            },
        )

