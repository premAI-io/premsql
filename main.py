from text2sql.dataset import BirdDevDataset
from text2sql.generator.from_hf import GeneratorHFModel
from text2sql.executor.from_sqlite import ExecutorFromSQLite

data_path = "./path/to/test/dataset"
model_name_or_path = "anindya64/text2sql_draft"

# Load the dataset
dataset = BirdDevDataset(
    data_path=data_path,
    databases_folder_name="dev_databases",  # Change the name here if there is other name
    json_file_name="dev.json",              # Change the name here if the name is different
    num_fewshot=5,                          # This is not to be changed
    model_name_or_path=model_name_or_path,
)

# Generate the results
generator = GeneratorHFModel(
    model_or_name_or_path=model_name_or_path,
    experiment_name="test_prem_text2sql",
    type="test",
    device="cuda:0",
)

responses = generator.generate_and_save_results(
    data=dataset,
    temperature=0.1,
    max_retries=5,
    force=True,
)

# Evaluate the results
executor = ExecutorFromSQLite(
    experiment_path=generator.experiment_path,
)

ex_acc = executor.compute(
    model_responses=responses,
    metric="accuracy",
    filter_by="difficulty"
)

ves = executor.compute(
    model_responses=responses,
    metric="ves",
    filter_by="difficulty"
)

print(f"Accuracy: {ex_acc}")
print(f"VES: {ves}")
