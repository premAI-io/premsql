from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

from premsql.pipelines.base import AgentBase, AgentOutput
from premsql.logger import setup_console_logger

logger = setup_console_logger("[FASTAPI-INFERENCE-SERVICE]")

class QuestionInput(BaseModel):
    question: str

class SessionInfoResponse(BaseModel):
    status: int
    session_name: Optional[str] = None
    db_connection_uri: Optional[str] = None
    session_db_path: Optional[str] = None
    base_url: Optional[str] = None
    created_at: Optional[datetime] = None

class AgentServer:
    def __init__(self, agent: AgentBase, url: Optional[str]="0.0.0.0", port: Optional[int] = 8100) -> None:
        self.agent = agent
        self.port = port
        self.url = url
        self.app = self.create_app()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        # Startup: Log the initialization
        logger.info("Starting up the application")
        yield
        # Shutdown: Clean up resources
        logger.info("Shutting down the application")
        if hasattr(self.agent, 'cleanup'):
            await self.agent.cleanup()

    def create_app(self):
        app = FastAPI(lifespan=self.lifespan)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )

        @app.post("/completion", response_model=AgentOutput)
        async def completion(input_data: QuestionInput):
            try:
                result = self.agent(question=input_data.question, server_mode=True)
                return AgentOutput(**result.model_dump())
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
            
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        @app.get("/session_info", response_model=SessionInfoResponse)
        async def get_session_info():
            try:   
                session_name = getattr(self.agent, 'session_name', None)
                db_connection_uri = getattr(self.agent, 'db_connection_uri', None)
                session_db_path = getattr(self.agent, 'session_db_path', None)
                
                if any(attr is None for attr in [session_name, db_connection_uri, session_db_path]):
                    raise ValueError("One or more required attributes are None")
                
                return SessionInfoResponse(
                    status=200,
                    session_name=session_name,
                    db_connection_uri=db_connection_uri,
                    session_db_path=session_db_path,
                    base_url=f"{self.url}:{self.port}",
                    created_at=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error getting session info: {str(e)}")
                return SessionInfoResponse(
                    status=500,
                    session_name=None,
                    db_connection_uri=None,
                    session_db_path=None,
                    base_url=None,
                    created_at=None
                )
        return app

    def launch(self):
        import uvicorn
        logger.info(f"Starting server on port {self.port}")
        uvicorn.run(self.app, host=self.url, port=int(self.port))