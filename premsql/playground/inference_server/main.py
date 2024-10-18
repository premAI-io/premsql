import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from service import AgentServer


class QueryRequest(BaseModel):
    question: str
    additional_knowledge: Optional[str]
    few_shot_examples: Optional[dict]


agent_service = None


@asynccontextmanager
async def lifespan(app: FastAPI, args: argparse.Namespace):
    global agent_service
    agent_service = AgentServer(
        agent_name=args.agent_name,
        dsn_or_db_path=args.dsn_or_db_path,
        config_path=args.config_path,
        env_file_path=args.env_path,
        include_tables=args.include_tables,
        exclude_tables=args.exclude_tables,
    )
    yield


def create_app(args: argparse.Namespace) -> FastAPI:
    app = FastAPI(lifespan=lambda app: lifespan(app, args))

    @app.get("/agents")
    async def get_available_agents():
        return {"available_agents": agent_service.agents}

    @app.post("/query")
    async def query(request: QueryRequest):
        if agent_service is None:
            raise HTTPException(
                status_code=500, detail="Agent service is not initialized"
            )
        try:
            result = agent_service.run(
                question=request.question,
                additional_knowledge=request.additional_knowledge,
                fewshot_dict=request.few_shot_examples,
            )
            return {**result}
        except Exception as e:
            # logger.error(f"Error processing query: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error processing query: {str(e)}"
            )

    return app


def parse_arguments():
    parser = argparse.ArgumentParser(description="PremSQL Inference Server")
    parser.add_argument(
        "--agent_name", required=True, help="The name of the agent to be used"
    )
    parser.add_argument(
        "--dsn_or_db_path", required=True, help="Database connection string or path"
    )
    parser.add_argument("--config_path", help="Path to configuration file")
    parser.add_argument("--env_path", help="Path to your .env file path")
    parser.add_argument(
        "--include_tables", help="Comma-separated list of tables to include"
    )
    parser.add_argument(
        "--exclude_tables", help="Comma-separated list of tables to exclude"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to run the server on")
    parser.add_argument(
        "--port", type=int, default=8500, help="Port to run the server on"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    app = create_app(args)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
