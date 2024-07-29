# Settings and Configurations 

This section discusses different configs that text2sql has for evaluation. Primarily we have two different configurations. 

## SQLGeneratorConfig

This configuration acts as a general settings which controls the entire evaluation process. There are several arguments however these are some argumets you can tweak:

- `model_name (str)`: Think of this as your experiment name. You can give it any name. However we prefer to give it the name by the name of the model which will be used to evaluate. Example: `gpt-4o-zeroshot` or `experiment-1-gpt-4o-mini`. 

- `use_knowledge (bool)`: When you set this as `True` it will be inserting existing domain knowledge (around the database or tables) inside the prompt.
  
You can also tweak other arguments. Any path related arguments should only be changed when you have your dataset into a different location. 


## APIConfig and ModelConfig

These are the configs that handles the LLM Generation. 

- In `APIConfig` you need to add the `model_name` and add the `api_key` argument. dditionally you can also put other parameters like `temperature`, `max_tokens` etc to tweak generations. 

- In `ModelConfig`, you need to put the `model_name` argument as a required argument. If your model is placed in a different location then add the `model_path` argument. If your model is an instruct model, then set `is_instruct` as `True`. If you are using a non-cuda device then set `device` to `cpu`. Additional argument like, `temperature`, `max_tokens` etc can be changed to tweak. 


## Creating your custom config

If you need to create some config which needs to have more paramteres just extend with the existing configurations. For example, if you are using some different API service which has some tweakable config, just extend it like this:

```python
class MyAPIConfig(APIConfig):
    # add your additional configs here
    ...
```