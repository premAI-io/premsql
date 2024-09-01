from pathlib import Path
from typing import Union, Literal, Optional 
from text2sql.executor.acc import Text2SQLAccuracyFromSQLite
from text2sql.executor.ves import Text2SQLVESFromSQLite

class ExecutorFromSQLite:
    def __init__(self, experiment_path: Union[str, Path]):
        self.acc = Text2SQLAccuracyFromSQLite(experiment_path)
        self.ves = Text2SQLVESFromSQLite(experiment_path)

    def compute(
        self, 
        model_responses: list[dict], 
        metric: Literal["accuracy", "ves"],
        filter_by: Optional[dict] = None
    ) -> dict:
        assert metric in ["accuracy", "ves"], f"Unknown metric: {metric}"
        if metric == "accuracy":
            return self.acc.execute(
                model_responses=model_responses,
                filter_by=filter_by
            )
        
        return self.ves.execute(
            model_responses=model_responses,
            filter_by=filter_by
        )
