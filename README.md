## Prem Text2SQL

This library offers modular tools and components designed to help developers create efficient and reliable text-to-SQL models and engines.

**Please note:** This library is in its early stages, and we are actively developing additional features. This current release focuses only on evaluation. You can check out our in-depth [documentation here](/docs/evaluation/).

## Blogs and Resources 

- [Documentation](/docs)
- [Examples](/examples)
- [Blog: How much Text to SQL is a solved Problem](https://blog.premai.io/text2sql-eval)
- [Blog: State of SQL 2024](https://blog.premai.io/state-of-text2sql-2024/)

## Quick Start

First, install the library using the following command:

```bash
git clone https://github.com/premAI-io/text2sql.git
cd text2sql
pip install -e .
```

You can either use the Prem AI API to evaluate different closed-source models or use HuggingFace models to evaluate open-source models. Here, we show you how to use the Prem AI API. If you are not familiar with how to use the Prem AI API, [check out our docs](https://docs.premai.io/introduction) to get started quickly.

```python
from text2sql.eval.dataset.bird import BirdBenchEvalDataset
from text2sql.eval.settings import SQLGeneratorConfig, APIConfig
from text2sql.eval.generator.bird.from_api import SQLGeneratorFromAPI
from text2sql.eval.executor.bird.acc import BirdExecutorAcc
from text2sql.eval.executor.bird.ves import BirdExecutorVES

# Create a config (which contains all the general settings)
# and give a name to the experiment you are performing.
# We are doing a full evaluation of gpt4-o here.

config = SQLGeneratorConfig(model_name="gpt-4o-full-eval")
eval_dataset = BirdBenchEvalDataset(config=config)

# Instantiate the bird dataset and apply the prompt with knowledge. 

dataset = eval_dataset.process_and_filter().apply_prompt(apply_knowledge=True)
api_config = APIConfig(
    api_key=api_key, 
    temperature=0.1, 
    max_tokens=256,
    model_name="gpt-4o"
)

# Instantiate the client. We are going to use the Prem AI API for running 
# the experiments here. 

client_gpt4o = SQLGeneratorFromAPI(
    generator_config=config,
    engine_config=api_config
)

# Now generate and save the results. 
# This will save the results inside ./experiment/eval/gpt-4o-full-eval.

data_with_gen = client_gpt4o.generate_and_save_results(
    data=dataset, force=False
)

# Instantiate the classes for accuracy and VES.

acc = BirdExecutorAcc(generator_config=config)
ves = BirdExecutorVES(generator_config=config)

# Finally, perform the evaluation for accuracy and VES.

acc_res = acc.execute(model_responses=data_with_gen)
ves_res = ves.execute(model_responses=data_with_gen)
```

**Output**

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

Check out our [examples](/examples/evaluation.ipynb) and [documentation](/docs/evaluation/) to get an in-depth understanding of each component and how to use it.

We have also benchmarked several closed and open-source models. Here are some results for the following models:

- gpt-4o
- gpt-4o-mini
- claude-3.5-sonnet
- codellama-70b-instruct
- claude-3-opus
- llama-3.1-405-instruct

**Accuracy**

![Model Accuracy Comparison (1)](https://github.com/user-attachments/assets/af37984d-3c44-4b85-b816-33e6a79b050c)

**Valid Efficiency Score**

![Model comparison VES (1)](https://github.com/user-attachments/assets/09bdb4fe-c241-4e76-a068-9787bd4da8f1)


We have also made a detailed blog about this. If you are more interested in the analysis, you can check out the [blog post here](https://blog.premai.io/text2sql-eval).

## High-Level Architecture

The library is composed of the following components:

![text2sql architecture](/docs/assets/text2sql_arch.png)

- **evaluator**: Helps evaluate text2sql models or systems on benchmark datasets like [BIRDBench](https://bird-bench.github.io/). It can be extended to other custom datasets as long as they follow a specific format. More details in our [evaluation section](/docs/evaluation.md).

- **synthetic data generator**: (In development) Facilitates the creation of domain-specific text2sql models by generating user query - SQL query pairs faster than manual creation.

- **fine-tuner**: Supports multiple fine-tuning experiments on different LLMs/SLMs over existing or custom datasets.

- **connector**: (In development) Connects the text2sql pipeline with data sources like PostgreSQL databases or cloud DB instances.

- **agents**: (In development) Helps build end-to-end pipelines with various functions and tools, generating SQLs from text, validating them, running them in sandboxes/connectors, and performing self-corrections for robust performance.

## Roadmap

As of now, we have just released our very first alpha version of our evaluator. Our development priorities follow this approximate order:

1. Fine-tuner component and evaluator improvements
2. Connectors
3. Synthetic data generator
4. Agents

## Contributing

We welcome contributions from the community! If you would like to contribute, please follow these steps:

1. Fork the repository and create your branch from `main`.
2. If you have added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code adheres to our coding standards and conventions.
5. Submit a pull request, describing what your changes do and why you think they are beneficial.

---
