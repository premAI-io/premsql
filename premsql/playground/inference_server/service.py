import importlib
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Optional

from dotenv import load_dotenv

from premsql.logger import setup_console_logger

logger = setup_console_logger(name="[AGENT-SERVER]")


def load_config_from_file(file_path):
    # Get the absolute path
    abs_path = Path(file_path).resolve()
    spec = importlib.util.spec_from_file_location("config_module", abs_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    if hasattr(config_module, "config") and hasattr(config_module, "pipelines_mapping"):
        return (config_module.pipelines_mapping, config_module.config)
    else:
        raise ValueError(f"No 'config' variable found in {file_path}")


class AgentServer:
    def __init__(
        self,
        dsn_or_db_path: str,
        agent_name: str,
        config_path: Optional[str] = None,
        env_file_path: Optional[str] = None,
        include_tables: Optional[list] = None,
        exclude_tables: Optional[list] = None,
    ):
        if env_file_path:
            load_dotenv(dotenv_path=env_file_path)

        # May be add it to somewhere else to make it more configurable
        self.agent_name = agent_name
        if config_path:
            self.pipeline_mapping, self.config_mapping = load_config_from_file(
                config_path
            )
        else:
            import premsql.playground.inference_server.default_configs as server_config

            self.pipeline_mapping, self.config_mapping = (
                server_config.pipelines_mapping,
                server_config.config,
            )

        agent_config = self.config_mapping[agent_name]["init"]

        self.agent = self.pipeline_mapping[agent_name](
            **agent_config,
            dsn_or_db_path=dsn_or_db_path,
            include_tables=include_tables,
            exclude_tables=exclude_tables,
        )

    def run(
        self,
        question: str,
        additional_knowledge: Optional[str] = None,
        fewshot_dict: Optional[dict] = None,
    ):
        parameters = {
            **self.config_mapping[self.agent_name]["run"],
            **dict(
                question=question,
                additional_knowledge=additional_knowledge,
                fewshot_dict=fewshot_dict,
            ),
        }
        return self.agent.query(**parameters)

    @property
    def agents(self):
        return list(self.pipeline_mapping.keys())

    def close(self):
        del self.agent
