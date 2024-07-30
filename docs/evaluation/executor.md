# Executor 

For evaluation, we will use two classes, `BirdExecutorAcc` and `BirdExecutorVES`. These two are different metric that are popularly used to evaluate text to SQL tasks. 

- BirdExecutorAcc is very straight forward accuracy metric. 

- VES or Valid Efficiency Score is a score that returns 0 if the predicted SQL gives the wrong result else, it gives the relative efficiency (time required to execute the predicted SQL over the actual SQL). VES is super important when it comes to determining how optimized SQL our LLM generates. 

To use this, we do the following: 

```python
from text2sql.eval.executor import BirdExecutorAcc
from text2sql.eval.executor import BirdExecutorVES
from text2sql.eval.settings import APIConfig, SQLGeneratorConfig


config = SQLGeneratorConfig(model_name="some-experiment")

# Instantiate the metrics
acc = BirdExecutorAcc(generator_config=config)
ves = BirdExecutorVES(generator_config=config)

# Now execute 

acc_res = acc.execute(model_responses=response_from_model)
ves_res = ves.execute(model_responses=response_from_model)
```

**Note**: If you have used any filter (based on difficulty) before to get the dataset, then provide the filter while you do the execution, else it can be None. Here is how we do it. If you have used a filter based on `db_id`, there is no need to put anything inside the `filter_used` argument. 

To understand how to get the response from model, you can checkout [this part](/docs/evaluation/generator.md) of the documentation. If you want to know how to get the data then [check out this part](/docs/evaluation/dataset.md) of our documentation. 

## Writing custom custom evaluator:

The evaluations above are strictly based on SQLite databases. To create custom evaluation engines, you need to create your own engine. You can derive it from the `BirdExecutorAcc` or `BirdExecutorVES` class if your data has similar filters like difficulty as it is there in the BIRDBench dataset. Even if you are not using it, just add a placeholder for a way around. It is simple. Here is a rough structure of how the evaluator class should look like:


```python
from text2sql.eval.executor.bird.acc import BirdExecutorAcc

class AccuracyFromPostGres(BirdExecutorAcc):
    def __init__(self, generator_config: SQLGeneratorConfig) -> None:
        self.generator_config = generator_config
    
    def execute_sql(self, predicted_sql: str, ground_truth: str, db_path: str) -> int:
        # Write the logic to fetch results from postgres
        pass 
```

Once done, you can call this class to evaluate directly in postgres database. 

**Please note that**: We are in the very early stages of development, so it will take us some time to make integrations of custom evaluators from different connectors more seamless. Future releases aim to make this better and easier. 
