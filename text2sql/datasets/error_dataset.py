import json
from copy import deepcopy
from pathlib import Path
from typing import Union, Optional, Sequence
from transformers import AutoTokenizer

from text2sql.generators.base import Text2SQLGeneratorBase
from text2sql.evaluator.base import Text2SQLEvaluatorBase
from text2sql.datasets.prompts import ERROR_HANDLING_PROMPT
from text2sql.logger import setup_console_logger

logger = setup_console_logger("[ERROR-HANDLING-DATASET]")

class ErrorHandlingDataset:
    pass 
