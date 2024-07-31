# Generators

The generators class lets you generate SQL responses when given the input prompt. Currently, we natively support two types of generators:

- `from_api`: This uses models from API calls. We use Prem AI API to connect different closed-source models. You can check out how to get started with Prem AI in our [documentation](https://docs.premai.io/introduction).  

- `from_hf`: This connects different huggingface models. Please note that the current version only supports CausalLM models. We will provide more general support in the coming versions. 

Generators can be anything as long as it takes a string prompt as input and outputs a string. This can be LLM or even an agentic workflow (as a function or an API). So you can test out LLM's performance natively or agents too through this. 

Let's see how we can use Prem AI API to get the results from the model. 


```python
import os

from text2sql.eval.generator import SQLGeneratorFromAPI
from text2sql.eval.settings import APIConfig, SQLGeneratorConfig

# Create an API Config 
api_key = os.environ.get("PREMAI_API_KEY")

config = SQLGeneratorConfig(model_name="some-experiment")
api_config = api_config = APIConfig(
    api_key=api_key, 
    temperature=0.1, 
    max_tokens=256,
    model_name="gpt-4o"
)

# Create the client instance, which will use the config 
client_gpt4o = SQLGeneratorFromAPI(
    generator_config=config,
    engine_config=api_config
)

# Call the API
data_with_results = client_gpt4o.generate_and_save_results(
    data=dataset, force=False
)
```

`APIConfig` acts as a config to control your LLM. You must put your `api_key` and the `model_name` as required parameters. Additionally, you can also put other parameters like `temperature`, `max_tokens` etc, to tweak generations. 

`SQLGeneratorFromAPI` is our engine that generates responses and appends those generations inside our initial data. We will use the data (containing the LLM generations) to further evaluate them. In this step, we are only going to generate results.

The same API Interface is been used in `SQLGeneratorFromModel` class. However in that case you need to use the `ModelConfig`. You can learn more about different [configs here](/docs/evaluation/settings_and_configurations.md) and about [datasets here](/docs/evaluation/dataset.md).

## Creating Custom generators. 

Both the mentioned generated are derived from the `BaseGenerator` class. So here is how you will create your own generator class, which might use your own API or any other engine like vLLM or Llama CPP, etc. 

```python 
from typing import Union
from text2sql.eval.generator.bird.base import BaseGenerator
from text2sql.eval.settings import APIConfig, SQLGeneratorConfig, ModelConfig

class SQLGeneratorFromYourConnector(BaseGenerator):
    def __init__(
        self, 
        generator_config: SQLGeneratorConfig, 
        engine_config: Union[APIConfig, ModelConfig]
    ) -> None:
        
        super().__init__(generator_config=generator_config, engine_config=engine_config)
        self.client = ... # Define your client here 

    def generate(self, prompt: str) -> str:

        # Call your client here and do the inference 
        try:
            result = ...
        except Exception as e:
            result = "error:{}".format(e)

        return result
```

Once created you can now use it in the existing pipelines without changing any other code. 
