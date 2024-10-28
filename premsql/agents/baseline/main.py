from typing import Any, Optional

import pandas as pd

from premsql.executors.base import BaseExecutor
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.agents.base import AgentBase, ExitWorkerOutput
from premsql.agents.baseline.workers import (
    BaseLineAnalyserWorker,
    BaseLineFollowupWorker,
    BaseLinePlotWorker,
    BaseLineText2SQLWorker,
)
from premsql.agents.router import SimpleRouterWorker
from premsql.agents.tools.plot.base import BasePlotTool

# TODO: Should the name be changed from baseline to eda or autoeda?


class BaseLineAgent(AgentBase):
    def __init__(
        self,
        session_name: str,
        db_connection_uri: str,
        specialized_model1: Text2SQLGeneratorBase,
        specialized_model2: Text2SQLGeneratorBase,
        executor: BaseExecutor,
        plot_tool: BasePlotTool,
        session_db_path: Optional[str] = None,
        include_tables: Optional[list] = None,
        exclude_tables: Optional[list] = None,
        auto_filter_tables: Optional[bool] = False,
        route_worker_kwargs: Optional[dict] = {},
    ) -> None:
        super().__init__(
            session_name=session_name,
            db_connection_uri=db_connection_uri,
            session_db_path=session_db_path,
            route_worker_kwargs=route_worker_kwargs,
        )
        self.text2sql_worker = BaseLineText2SQLWorker(
            db_connection_uri=db_connection_uri,
            generator=specialized_model1,
            helper_model=specialized_model1,
            executor=executor,
            include_tables=include_tables,
            exclude_tables=exclude_tables,
            auto_filter_tables=auto_filter_tables,
        )
        self.analysis_worker = BaseLineAnalyserWorker(generator=specialized_model2)
        self.plotter_worker = BaseLinePlotWorker(
            generator=specialized_model2, plot_tool=plot_tool
        )
        self.followup_worker = BaseLineFollowupWorker(generator=specialized_model2)
        self.router = SimpleRouterWorker()

    def run(
        self, question: str, input_dataframe: Optional[pd.DataFrame] = None
    ) -> ExitWorkerOutput:
        decision = self.router.run(question=question, input_dataframe=input_dataframe)
        dataframe_from_history = None
        # TODO: This is an assumption that the output tables will be in last
        # 10 conversation

        history_entries = self.history.get(limit=10)
        for entry in history_entries:
            content = entry["message"]
            df = content.show_output_dataframe()
            if df is not None and len(df) > 0:
                dataframe_from_history = content.show_output_dataframe()
                break

        if decision.route_to in ["query", "analyse", "plot"]:
            worker_output = self._execute_worker(
                question=question,
                route_to=decision.route_to,
                input_dataframe=input_dataframe,
                dataframe_from_history=dataframe_from_history,
            )
            exit_output = self._create_exit_worker_output(
                question=question,
                route_taken=decision.route_to,
                worker_output=worker_output,
            )
            if any(
                [
                    exit_output.error_from_analysis_worker,
                    exit_output.error_from_plot_worker,
                    exit_output.error_from_sql_worker,
                ]
            ):
                followup_output = self._handle_followup(exit_output)
                exit_output.followup_suggestion = followup_output.suggestion
                exit_output.followup_route_to_take = (
                    followup_output.alternative_route or "query"
                )  # This is the default route
                exit_output.error_from_followup_worker = (
                    followup_output.error_from_model
                )
        else:
            exit_output = self._handle_followup_route(question=question)
        return exit_output

    def _execute_worker(
        self,
        question: str,
        route_to: str,
        input_dataframe: Optional[pd.DataFrame],
        dataframe_from_history: Optional[pd.DataFrame],
    ):
        decision_mappign = {
            "query": lambda: self.text2sql_worker.run(
                question=question,
                render_results_using="json",
                **self.route_worker_kwargs.get("query", {})
            ),
            "analyse": lambda: self.analysis_worker.run(
                question=question,
                input_dataframe=(
                    dataframe_from_history
                    if input_dataframe is None
                    else input_dataframe
                ),
                **self.route_worker_kwargs.get("analyse", {})
            ),
            "plot": lambda: self.plotter_worker.run(
                question=question,
                input_dataframe=(
                    dataframe_from_history
                    if input_dataframe is None
                    else input_dataframe
                ),
                **self.route_worker_kwargs.get("plot", {})
            ),
        }
        return decision_mappign[route_to]()

    def _create_exit_worker_output(
        self,
        question: str,
        route_taken: str,
        worker_output: Any,  # TODO: change it Literal of worker fixed outputs
    ) -> ExitWorkerOutput:
        exit_output = ExitWorkerOutput(
            session_name=self.session_name,
            question=question,
            route_taken=route_taken,
            db_connection_uri=self.db_connection_uri,
            additional_input=getattr(worker_output, "additional_input", None),
        )
        if route_taken == "query":
            exit_output.sql_string = worker_output.sql_string
            exit_output.sql_reasoning = worker_output.sql_reasoning
            exit_output.sql_output_dataframe = worker_output.output_dataframe
            exit_output.error_from_sql_worker = worker_output.error_from_model

        elif route_taken == "analyse":
            exit_output.analysis = worker_output.analysis
            exit_output.analysis_reasoning = worker_output.analysis_reasoning
            exit_output.analysis_input_dataframe = worker_output.input_dataframe
            exit_output.error_from_analysis_worker = worker_output.error_from_model

        elif route_taken == "plot":
            exit_output.plot_config = worker_output.plot_config
            exit_output.plot_input_dataframe = worker_output.input_dataframe
            exit_output.plot_output_dataframe = worker_output.output_dataframe
            exit_output.image_to_plot = worker_output.image_plot
            exit_output.plot_reasoning = worker_output.plot_reasoning
            exit_output.error_from_plot_worker = worker_output.error_from_model

        return exit_output

    def _handle_followup(self, prev_output: ExitWorkerOutput):
        return self.followup_worker.run(
            prev_output=prev_output,
            db_schema=self.text2sql_worker.db.get_context()["table_info"],
            user_feedback=None,
        )

    def _handle_followup_route(self, question: str) -> ExitWorkerOutput:
        history_entries = self.history.get()
        if len(history_entries) == 0:
            return ExitWorkerOutput(
                session_name=self.session_name,
                question=question,
                route_taken="followup",
                db_connection_uri=self.db_connection_uri,
                additional_input=None,
                followup_suggestion="Before Writing a followup please either query / analyse / plot",
                followup_route_to_take="query",
                error_from_followup_worker=None,
            )
        else:
            followup_output = self.followup_worker.run(
                prev_output=self.history.get(limit=1)[0]["message"],
                user_feedback=question,
                db_schema=self.text2sql_worker.db.get_context()["table_info"],
                **self.route_worker_kwargs.get("followup", {})
            )
        return ExitWorkerOutput(
            session_name=self.session_name,
            question=question,
            route_taken="followup",
            db_connection_uri=self.db_connection_uri,
            additional_input=None,
            followup_suggestion=followup_output.suggestion,
            followup_route_to_take=followup_output.alternative_route
            or "query",  # query should alaways be the default route
            error_from_followup_worker=followup_output.error_from_model,
        )
