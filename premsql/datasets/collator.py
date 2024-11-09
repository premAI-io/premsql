from dataclasses import dataclass
from typing import Sequence
from premsql.logger import setup_console_logger

logger = setup_console_logger("[DATASET-COLLATOR]")

try:
    import torch
    import transformers
except ImportError:
    logger.warn("Ensure torch and transformers are installed.")
    logger.warn("Install them by: pip install torch transformers")

@dataclass
class DataCollatorForSupervisedDataset:
    tokenizer: "transformers.PreTrainedTokenizer"

    def __call__(self, instances: Sequence[dict]) -> dict[str, torch.Tensor]:
        input_ids, labels = tuple(
            [instance[key] for instance in instances] for key in ("input_ids", "labels")
        )
        input_ids = torch.nn.utils.rnn.pad_sequence(
            input_ids,
            batch_first=True,
            padding_value=self.tokenizer.pad_token_id,
        )
        labels = torch.nn.utils.rnn.pad_sequence(
            labels, batch_first=True, padding_value=-100
        )
        return dict(
            input_ids=input_ids,
            labels=labels,
            attention_mask=input_ids.ne(self.tokenizer.pad_token_id),
        )
