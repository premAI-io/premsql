## Evaluators 

premsql evaluators help you to evaluate your text-to-sql models on various validation datasets. 
Currently, we support two metrics for evaluation:

- Execution Accuracy
- Valid Efficiency Score

**Execution Accuracy (EX):** From the name, it is clear that the correctness of the LLM is measured by comparing the executed results from
the LLM with the ground truth.

**Valid Efficiency Score (VES):** The primary objective of LLM-generated SQL queries is to be accurate. 
However, it also needs to be performance-optimized when dealing with big data. This metric asses both of the 
objectives. It quantifies how efficient the query is and whether the query is accurate or not. The figure below 
shows how it is computed.

Here is a quick start on how to use evaluators using premsql

```python
import json
from pathlib import Path
from premsql.datasets import Text2SQLDataset
from premsql.generators.premai import Text2SQLGeneratorPremAI
from premsql.evaluator import Text2SQLEvaluator, SQLiteExecutor

# Get the validation dataset

dataset = Text2SQLDataset(
    dataset_name="bird",
    split="test",
    database_folder_name="test_databases",
    json_file_name="test.json",
    dataset_folder="/root/anindya/Submission/text2sql/data",
).setup_dataset(
    num_rows=10,
    num_fewshot=3,
)

generator = Text2SQLGeneratorPremAI(
    model_name="gpt-4o",
    project_id=1234,
    premai_api_key="FK-xxxx-xxx-xxx",
    experiment_name="test_generators",
    device="cuda:0",
    type="test"
)

executor = SQLiteExecutor()
evaluator = Text2SQLEvaluator(
    executor=executor, experiment_path=experiment_path
)

# Calculate Execution Accuracy
ex = evaluator.execute(
    metric_name="accuracy", 
    model_responses=responses, 
    filter_by="difficulty"
)

# Similarity calculate Valid Efficiency Score

ves = evaluator.execute(
    metric_name="ves", 
    model_responses=responses, 
    filter_by="difficulty"
)
```

**Output**

Here is the output of execution accuracy of different models. 

```
Accuracy:
---------
+-------------+-------------------+-------------------+
| Category    |   num_correct (%) |   total questions |
+=============+===================+===================+
| simple      |           58.4865 |               925 |
+-------------+-------------------+-------------------+
| moderate    |           43.75   |               464 |
+-------------+-------------------+-------------------+
| challenging |           42.7586 |               145 |
+-------------+-------------------+-------------------+
| overall     |           52.5424 |              1534 |
+-------------+-------------------+-------------------+

Valid Efficiency Score (VES):
-----------------------------

+-------------+-----------+-------------------+
| Category    |   VES (%) |   total questions |
+=============+===========+===================+
| simple      |   60.1844 |               925 |
+-------------+-----------+-------------------+
| moderate    |   46.4345 |               464 |
+-------------+-----------+-------------------+
| challenging |   43.9845 |               145 |
+-------------+-----------+-------------------+
| overall     |   54.4941 |              1534 |
+-------------+-----------+-------------------+
```

We have also benchmarked several closed and open-source models. Here are some results for the following models:

- gpt-4o
- gpt-4o-mini
- claude-3.5-sonnet
- codellama-70b-instruct
- claude-3-opus
- llama-3.1-405-instruct

**Accuracy**

![accuracy comparison](/assets/Model-Accuracy-Comparison.png)

**Valid Efficiency Score**

![ves comparison](/assets/Models-VES-Comparison.png)

We have also made a detailed blog about this. If you are more interested in the analysis, you can check out the [blog post here](https://blog.premai.io/text2sql-eval).
