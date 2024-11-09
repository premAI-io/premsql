from typing import Optional

import pandas as pd

from premsql.logger import setup_console_logger
from premsql.agents.base import RouterWorkerBase, RouterWorkerOutput
from premsql.agents.utils import convert_df_to_dict

logger = setup_console_logger("[BASELINE-ROUTER]")


class SimpleRouterWorker(RouterWorkerBase):
    def run(
        self, question: str, input_dataframe: Optional[pd.DataFrame]
    ) -> RouterWorkerOutput:
        if question.startswith("/query"):
            route_to = "query"
        elif question.startswith("/analyse"):
            route_to = "analyse"
        elif question.startswith("/plot"):
            route_to = "plot"
        else:
            route_to = "followup"
        logger.info(f"Routing to: {route_to}")
        question = (
            question.split(f"/{route_to}")[1] if route_to != "followup" else question
        )

        return RouterWorkerOutput(
            question=question,
            route_to=route_to,
            input_dataframe=(
                convert_df_to_dict(df=input_dataframe) if input_dataframe else None
            ),
            decision_reasoning="Simple routing based on question prefix",
            additional_input={},
            error_from_model=None,
        )
