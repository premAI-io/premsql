# Text2SQL Submission to BirdBench 

This branch of the repository contains the code to reproduce the results of our approach to the BirdBench challenge. 

## Setup and installation

To setup the code base to run the evaluation you need to first clone the repo and switch to the `submission` branch. 

```bash
git clone https://github.com/premAI-io/text2sql.git
git checkout -b submission
```

Once done, then you need to create a new virual environment. This can be created with pyenv or conda. Now inside that, you can run the following to install all the requirements. 

If you use conda, then you can create a submission environment by using the following command and then install the requirements.

```bash
conda create -n submission python=3.10
pip install -U -r requirements.txt
```

## How to use the code base

This tutorial shows this for dev dataset but this same thing can be employed
for test dataset.
To begin, ensure that your dataset follows the required directory structure:

```python
├── dev_databases
│   ├── california_schools
│       ├── california_schools.sqlite
│   ├── card_games
│   ├── codebase_community
│   ├── debit_card_specializing
│   ├── european_football_2
│   ├── financial
│   ├── formula_1
│   ├── student_club
│   ├── superhero
│   ├── thrombosis_prediction
│   └── toxicology
├── dev.json
├── dev.sql
├── dev_tables.json
└── dev_tied_append.json
```

In this example, we use the BirdBench development dataset. The dataset structure should include the following mandatory components:

1. **`dev_databases` Folder**: This directory contains subfolders named after each database, each containing a corresponding `.sqlite` file. The `.sqlite` file must match the subfolder's name exactly.

2. **`dev.json` File**: This file contains metadata, including mappings of database paths, questions, filters, and other relevant information.

If your dataset files are named differently (e.g., for test datasets), you can either rename them to match this structure or adjust the names while you instantiate them with our API. Here is an example on how to do that. 

```python
from text2sql.dataset import BirdDevDataset

# inside that it should have the json file and dev_databases folder
data_path = "./path/to/test/dataset"
model_name_or_path = "anindya64/text2sql_draft"

dataset = BirdDevDataset(
    data_path=data_path,
    databases_folder_name="dev_databases",  # Change the name here if there is other name
    json_file_name="dev.json",              # Change the name here if the name is different
    num_fewshot=5,                          # This is not to be changed
    model_name_or_path=model_name_or_path,
)
```
So to summarize the only thing which is rigid is the structure of the data, i.e.

- A parent folder containing folders representing different database.
- Inside each database folder, a .sqlite file with the same name as the database folder name.
- A .json file which has all the information about the different DBs, question etc.

### Generator

A generator object of our text2sql API helps to generate the results. This is how we use it:

Now let's move into the `Generator` section.

```python
from text2sql.generator.from_hf import GeneratorHFModel

generator = GeneratorHFModel(
    model_or_name_or_path=model_name_or_path,
    experiment_name="test_pretext2sql",                 # Give whatever name you want
    type="test",                                        # This should not change
    device="cuda:0",                                    # Cuda device mapping
    hf_token="xxx-xxxx-xxxx"                            # This is Optional
)

responses = generator.generate_and_save_results(
    data=dataset,
    temperature=0.1,    # This is not to be changed
    max_retries=5       # This is not to be changed
)

```
For this testing, we are going to use our official model and the `max_retries` and `temperature` parameters are not subjected to change. Once all the responses are generated, a folder named `experiment` is created under the folder in which the program is run. So in this example, a folder named: `text2sql/experiments/test/test_pretext2sql` will be created. Inside this you will find a `predict.json` file which will contain the following information (each blob of the JSON):

```json
{
    "question_id": 0,
    "db_id": "california_schools",
    "question": "What is the highest eligible free rate for K-12 students in the schools in Alameda County?",
    "evidence": "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`",
    "SQL": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1",
    "difficulty": "simple",
    "db_path": "/root/anindya/text2sql/data/bird/validation/dev_databases/california_schools/california_schools.sqlite",
    "prompt": "<\uff5cbegin\u2581of\u2581sentence\uff5c>You ... students in the schools in Alameda County?\n\n# SQL:\n",
    "generated": "SELECT MAX(CAST(T1.`Free Meal Count (K-12)` AS REAL) / T1.`Enrollment (K-12)`) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Alameda'",
},
```

### Evaluator

This is the simple evaluator whose logic has been taken from the main [BirdBench code](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird). However there is no multiprocessing applied, so evaluation is been done iteratively. If you want to use your own evaluator then you can use the information from `generated` key of the each blob inside the `predict.json` file which is saved after the generation is complete. It also contains all the additional information which was there in the dataset.

Here is the code on how to evaluate using prem text2sql API. 


```python
from text2sql.executor.from_sqlite import ExecutorFromSQLite

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
```

Now the same script is been written in the main.py file. Make changes accordingly based on the dataset file path and then run:

```
python main.py
```

That is how we load dataset, generate predictions and evaluate the generations. For any kind of questions please reach us to: anindyadeep@premai.io
