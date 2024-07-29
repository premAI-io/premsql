import json
from abc import ABC, abstractmethod
from typing import Optional

# TODO: Additional code optimization
# - using existing configs for doing operations
# - remove the res keyword and use the metric name or it's alias
# - multi processing support


class BirdBenchExecutorBase(ABC):

    @abstractmethod
    def execute_model(self):
        raise NotImplementedError

    @abstractmethod
    def compute_metric(self, results: list):
        raise NotImplementedError

    def load_json(self, path: str) -> dict:
        with open(path, "r") as json_file:
            contents = json.loads(json_file.read())
        return contents

    def compute_metric_by_diff(self, exec_results, filter_used: Optional[tuple] = None):
        if filter_used is not None:
            results = []
            filter_key, filter_value = filter_used
            if filter_key == "difficulty":
                for content in exec_results:
                    results.append({"res": content["result"]})
                result = self.compute_metric(results)
                res = {
                    filter_value: (result, len(results)),
                    "overall": (result, len(results)),
                    **dict(
                        zip(
                            list(
                                set(["simple", "moderate", "challenging"])
                                - set([filter_value])
                            ),
                            [(0, 0), (0, 0)],
                        )
                    ),
                }
                return res
        else:
            results = {"simple": [], "moderate": [], "challenging": []}
            for content in exec_results:
                results[content["difficulty"]].append({"res": content["result"]})

            overall = [{"res": content["result"]} for content in exec_results]
            return {
                "simple": (
                    (
                        self.compute_metric(results["simple"])
                        if len(results["simple"]) > 0
                        else 0
                    ),
                    len(results["simple"]),
                ),
                "moderate": (
                    (
                        self.compute_metric(results["moderate"])
                        if len(results["moderate"]) > 0
                        else 0
                    ),
                    len(results["moderate"]),
                ),
                "challenging": (
                    (
                        self.compute_metric(results["challenging"])
                        if len(results["challenging"]) > 0
                        else 0
                    ),
                    len(results["challenging"]),
                ),
                "overall": (self.compute_metric(overall), len(exec_results)),
            }
