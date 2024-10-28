from typing import Optional

import pandas as pd
from tqdm.auto import tqdm

from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger
from premsql.agents.base import AnalyserWorkerOutput, AnalysisWorkerBase
from premsql.agents.baseline.prompts import (
    BASELINE_ANALYSIS_MERGER_PROMPT,
    BASELINE_ANALYSIS_WORKER_PROMPT,
)
from premsql.agents.utils import convert_df_to_dict

logger = setup_console_logger("[BASELINE-ANALYSER-WORKER]")

CHUNK_TEMPLATE = """
# Analysis:
{analysis}

# Reasoning
{reasoning}
"""

# TODO: Need to think of the case when there is no df being passed


class BaseLineAnalyserWorker(AnalysisWorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase) -> None:
        self.generator = generator

    def run_chunkwise_analysis(
        self,
        question: str,
        input_dataframe: pd.DataFrame,
        chunk_size: Optional[int] = 20,
        max_chunks: Optional[int] = 20,
        temperature: Optional[float] = 0.19,
        max_new_tokens: Optional[int] = 600,
        analysis_prompt_template: Optional[str] = BASELINE_ANALYSIS_WORKER_PROMPT,
        merger_prompt_template: Optional[str] = BASELINE_ANALYSIS_MERGER_PROMPT,
        verbose: Optional[bool] = False,
    ) -> tuple[str, str]:
        num_chunks = (len(input_dataframe) + chunk_size - 1) // chunk_size
        chunks = [
            input_dataframe[i * chunk_size : (i + 1) * chunk_size]
            for i in range(num_chunks)
        ][:max_chunks]
        analysis_list = []
        num_errors = 0

        for i, chunk in tqdm(enumerate(chunks), total=len(chunks)):
            analysis, error_from_model = self.analyse(
                question=question,
                input_dataframe=chunk,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                prompt_template=analysis_prompt_template,
            )
            if error_from_model:
                num_errors += 1
                logger.error(f"Error while analysing: {i}, Skipping ...")
                continue

            if verbose:
                logger.info(
                    CHUNK_TEMPLATE.format(
                        analysis=analysis["analysis"],
                        reasoning=analysis["analysis_reasoning"],
                    )
                )
            analysis_list.append(analysis)

        analysis_list_str = "\n".join(
            [
                analysis["analysis"] + " " + analysis["analysis_reasoning"]
                for analysis in analysis_list
            ]
        )
        if num_errors < len(chunks):
            summarized_analysis_prompt = merger_prompt_template.format(
                analysis=analysis_list_str
            )
            summary = self.generator.generate(
                data_blob={"prompt": summarized_analysis_prompt},
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                postprocess=False,
            )
            analysis = {
                "analysis": summary,
                "analysis_reasoning": "Analysis summarised by AI",
            }
            error_from_model = None

        else:
            analysis = {
                "analysis": "\n".join(
                    [
                        content["analyse"] if "analyse" in content else ""
                        for content in analysis_list
                    ]
                ),
                "analysis_reasoning": "Appending all the analysis",
            }
            error_from_model = "Model not able to summarise analysis"

        return analysis, error_from_model

    def analyse(
        self,
        question: str,
        input_dataframe: pd.DataFrame,
        temperature: Optional[float] = 0.19,
        max_new_tokens: Optional[int] = 512,
        prompt_template: Optional[str] = BASELINE_ANALYSIS_WORKER_PROMPT,
    ) -> dict:
        analysis = self.generator.generate(
            data_blob={
                "prompt": prompt_template.format(
                    dataframe=str(input_dataframe), question=question
                )
            },
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            postprocess=False,
        )
        try:
            analysis = analysis.replace("null", "None")
            analysis = eval(analysis)
            error_from_model = None
        except Exception as e:
            analysis = {
                "analysis": "Not able to analyse, Try again",
                "analysis_reasoning": None,
            }
            error_from_model = str(e)

        logger.info(analysis)
        logger.info("------------")
        logger.info(error_from_model)

        return analysis, error_from_model

    def run(
        self,
        question: str,
        input_dataframe: pd.DataFrame,
        do_chunkwise_analysis: Optional[bool] = False,
        chunk_size: Optional[int] = 20,
        max_chunks: Optional[int] = 20,
        temperature: Optional[float] = 0.19,
        max_new_tokens: Optional[int] = 600,
        analysis_prompt_template: Optional[str] = BASELINE_ANALYSIS_WORKER_PROMPT,
        analysis_merger_template: Optional[str] = BASELINE_ANALYSIS_MERGER_PROMPT,
        verbose: Optional[bool] = False,
    ) -> AnalyserWorkerOutput:
        if len(input_dataframe) > chunk_size and do_chunkwise_analysis:
            logger.info("Going for chunk wise analysis ...")
            analysis, error_from_model = self.run_chunkwise_analysis(
                question=question,
                input_dataframe=input_dataframe,
                chunk_size=chunk_size,
                max_chunks=max_chunks,
                analysis_prompt_template=analysis_prompt_template,
                merger_prompt_template=analysis_merger_template,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                verbose=verbose,
            )
        else:
            if len(input_dataframe) > chunk_size:
                logger.info(
                    "Truncating table, you can also choose chunk wise analysis, but it takes more time."
                )
            analysis, error_from_model = self.analyse(
                question=question,
                input_dataframe=input_dataframe.iloc[:chunk_size, :],
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                prompt_template=analysis_prompt_template,
            )
        return AnalyserWorkerOutput(
            question=question,
            input_dataframe=convert_df_to_dict(df=input_dataframe),
            analysis=analysis.get("analysis", "Not able to analyse"),
            analysis_reasoning=analysis.get("analysis_reasoning", None),
            error_from_model=error_from_model,
            additional_input={
                "temperature": temperature,
                "max_new_tokens": max_new_tokens,
                "chunkwise_analysis": do_chunkwise_analysis,
                "chunk_size": chunk_size,
                "max_chunks": max_chunks,
            },
        )
