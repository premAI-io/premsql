from premsql.datasets import (
    BirdDataset,
    SpiderUnifiedDataset,
    DomainsDataset,
    GretelAIDataset,
)

from premsql.executors.from_sqlite import SQLiteExecutor
from premsql.datasets import Text2SQLDataset
from premsql.tuner.peft import Text2SQLPeftTuner
from premsql.datasets.error_dataset import ErrorDatasetGenerator


path = "/root/anindya/text2sql/data"
model_name_or_path = "premai-io/prem-1B-SQL"

bird_train = BirdDataset(
    split="train",
    dataset_folder=path,
).setup_dataset(
    num_rows=100,
)

spider_train = SpiderUnifiedDataset(
    split="train", dataset_folder="./data"
).setup_dataset(num_rows=100)

domains_dataset = DomainsDataset(
    split="train",
    dataset_folder="./data",
).setup_dataset(num_rows=100)

gertelai_dataset = GretelAIDataset(
    split="train",
    dataset_folder="./data",
).setup_dataset(num_rows=100)

existing_error_dataset = ErrorDatasetGenerator.from_existing(
    experiment_name="testing_error_gen"
)
merged_dataset = [
    *spider_train,
    *bird_train,
    *domains_dataset,
    *gertelai_dataset,
    *existing_error_dataset,
]
bird_dev = Text2SQLDataset(
    dataset_name="bird",
    split="validation",
    dataset_folder=path,
).setup_dataset(num_rows=10, filter_by=("difficulty", "challenging"))

tuner = Text2SQLPeftTuner(
    model_name_or_path=model_name_or_path, experiment_name="lora_tuning"
)

tuner.train(
    train_datasets=merged_dataset,
    output_dir="./output",
    num_train_epochs=1,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    evaluation_dataset=bird_dev,
    eval_steps=100,
    max_seq_length=1024,
    executor=SQLiteExecutor(),
    filter_eval_results_by=("difficulty", "challenging"),
)
