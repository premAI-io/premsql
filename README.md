# PremSQL
End-to-End Local-First Text-to-SQL Pipelines

PremSQL is an open-source library designed to help developers create secure, fully local Text-to-SQL solutions using small language models. It provides all the essential tools to build and deploy end-to-end Text-to-SQL pipelines with customizable components, making it ideal for secure, autonomous AI-powered data analysis.

![alt architecture](/assets/architecture.png)

## 🚀 Features

- **Local-First**: Avoid third-party closed-source providers and keep your data secure.
- **Customizable Datasets**: Create, fine-tune, and evaluate models with built-in or custom datasets.
- **Robust Executors and Evaluators**: Easily connect to databases and assess model performance.
- **Advanced Generators**: Convert natural language prompts into executable SQL queries.
- **Error Handling and Self-Correction**: Automatically correct SQL queries during inference.
- **Fine-Tuning Support**: Fine-tune models with LoRA, QLoRA, or full fine-tuning strategies.
- **End-to-End Pipelines**: Seamlessly integrate all components for autonomous data analysis.

## 📚 Table of Contents

- [PremSQL](#premsql)
  - [🚀 Features](#-features)
  - [📚 Table of Contents](#-table-of-contents)
  - [🛠️ Installation](#️-installation)
  - [🚀 Quickstart](#-quickstart)
  - [📦 Components Overview](#-components-overview)
    - [Datasets](#datasets)
    - [Executors and Evaluators](#executors-and-evaluators)
    - [Generators](#generators)
    - [Error Handling](#error-handling)
    - [Tuner](#tuner)
    - [Pipelines](#pipelines)
  - [🤝 Contributing](#-contributing)
  - [📝 License](#-license)

## 🛠️ Installation

PremSQL requires Python 3.8 or higher. Install the library via pip:

```bash
pip install premsql
```

## 🚀 Quickstart

Here’s a quick example of how to use PremSQL to generate SQL queries from natural language inputs:

```python
from premsql.pipelines.simple import SimpleText2SQLAgent
from premsql.generators.huggingface import Text2SQLGeneratorHF
from langchain_community.utilities.sql_database import SQLDatabase
from premsql.utils import convert_sqlite_path_to_dsn

dsn_or_db_path = convert_sqlite_path_to_dsn("/path/to/db.sqlite")
db = SQLDatabase.from_uri(dsn_or_db_path)

# Create the pipeline and connect to the DB
pipeline = SimpleText2SQLAgent(
    dsn_or_db_path=db,
    generator=Text2SQLGeneratorHF(
        model_or_name_or_path="premai-io/prem-1B-SQL",
        experiment_name="test_nli",
        device="cuda:0",
        type="test"
    ),
)

# Ask a question
response = pipeline.query(
    question="Please list the phone numbers of the direct charter-funded schools that opened after 2000/1/1",
)

print(response["table"])
```

## 📦 Components Overview

### Datasets

PremSQL provides flexible interfaces for creating high-quality datasets tailored to Text-to-SQL tasks. These datasets include schema information, few-shot examples, and additional context to guide SQL generation.

**Example:**

```python
from premsql.datasets import Text2SQLDataset

# Load the BirdBench dataset
bird_dataset = Text2SQLDataset(
    dataset_name='bird', 
    split="train", 
    force_download=False,
    dataset_folder="path/to/store/the/dataset"
)
```

### Executors and Evaluators

Executors connect to databases and execute SQL, while evaluators assess the performance of your models against predefined metrics like Execution Accuracy (EX) and Valid Efficiency Score (VES).

**Example:**

```python
from premsql.evaluator import Text2SQLEvaluator, SQLiteExecutor

executor = SQLiteExecutor()
evaluator = Text2SQLEvaluator(
    executor=executor, 
    experiment_path="path/to/experiment"
)

ex = evaluator.execute(
    metric_name="accuracy", 
    model_responses=responses, 
    filter_by="difficulty"
)

print(f"Execution Accuracy is: {ex}")
```

### Generators

Generators are responsible for converting natural language prompts into executable SQL queries. They support multiple decoding methods, including execution-guided decoding for error correction.

**Example:**

```python
from premsql.generators.huggingface import Text2SQLGeneratorHF
from premsql.datasets import Text2SQLDataset

# Define a dataset
dataset = Text2SQLDataset(
    dataset_name="bird",
    split="test",
    database_folder_name="test_databases",
    json_file_name="test.json",
    dataset_folder="/path/to/dataset/folder",
).setup_dataset(num_rows=10, num_fewshot=3)

# Define a generator 
generator = Text2SQLGeneratorHF(
    model_or_name_or_path="premai-io/prem-1B-SQL",
    experiment_name="test_generators",
    device="cuda:0",
    type="test"
)

# Generate on the full dataset
response = generator.generate_and_save(
    dataset=dataset,
    temperature=0.1,
    max_new_tokens=256
)
```

### Error Handling

PremSQL provides error-handling prompts and datasets that improve the model’s ability to self-correct SQL queries during inference, ensuring high-quality, executable outputs.

**Example Error Correction Prompt:**

```plaintext
{existing_prompt}

# Generated SQL: {sql}

## Error Message

{error_msg}

Carefully review the original question and error message, then rewrite the SQL query to address the identified issues.
```

### Tuner

Fine-tune your Text-to-SQL models with ease using PremSQL’s tuner module, which supports LoRA, QLoRA, and full fine-tuning strategies.

**Example Fine-Tuning Workflow:**

```python
from premsql.tuner import SQLTuner
from premsql.datasets import Text2SQLDataset

# Load the dataset
dataset = Text2SQLDataset(
    dataset_name='bird', 
    split="train"
)

# Initialize the tuner
tuner = SQLTuner(
    model_name="premai-io/prem-1B-SQL",
    dataset=dataset,
    output_dir="./finetuned_model"
)

# Start fine-tuning
tuner.fine_tune()
```

### Pipelines

PremSQL pipelines are end-to-end solutions that connect to your database and generate SQL queries from natural language questions, providing complete control over your data analysis workflows.

**Example Simple Pipeline:**

```python
from premsql.pipelines.simple import SimpleText2SQLAgent
from premsql.generators.huggingface import Text2SQLGeneratorHF
from langchain_community.utilities.sql_database import SQLDatabase

dsn_or_db_path = convert_sqlite_path_to_dsn("/path/to/db.sqlite")
db = SQLDatabase.from_uri(dsn_or_db_path)

pipeline = SimpleText2SQLAgent(
    dsn_or_db_path=db,
    generator=Text2SQLGeneratorHF(
        model_or_name_or_path="premai-io/prem-1B-SQL",
        experiment_name="test_nli",
        device="cuda:0",
        type="test"
    ),
)

response = pipeline.query(
    question="List the phone numbers of the charter-funded schools opened after 2000/1/1",
)

print(response["table"])
```

## 🤝 Contributing

We welcome contributions from the community! If you’d like to contribute to PremSQL, please follow these guidelines:

1. **Fork the repository** and clone your fork.
2. **Create a new branch** for your feature or bug fix.
3. **Make your changes** and ensure the code passes all tests.
4. **Submit a pull request** with a clear description of your changes.

For detailed guidelines, please check the [CONTRIBUTING.md](CONTRIBUTING.md).

## 📝 License

PremSQL is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

---

Join us in revolutionizing the NL2SQL landscape with local-first, autonomous AI-powered data analysis! For more details, visit our [documentation](https://docs.premai.io/premsql/introduction) and check out our [GitHub repository](https://github.com/premAI-io/premsql).
