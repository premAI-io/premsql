import json
from typing import Optional, List
from text2sql.eval.generator import SQLGeneratorFromAPI
from text2sql.settings import APIConfig, SQLGeneratorConfig, MetricConfig
from text2sql.eval.executor import SQLExecutorEX
from text2sql.eval.ves import SQLVesEvaluator


def generate_dev(
    engine: str,
    model_name: str,
    num_rows: Optional[int] = None,
    use_knowledge: Optional[bool] = False,
    chain_of_thought: Optional[bool] = False,
    temperature: float = 0,
    max_tokens: Optional[int] = 256,
    stop: Optional[List[str]] = None,
):
    print("Starting to generate SQL for eval ...")
    assert engine in ["prem", "hf"], ValueError("Supported engines: 'prem' and 'hf'")

    if stop is None:
        stop = ["--", "\n\n", ";", "#"]

    generator_config = SQLGeneratorConfig(
        model_name=model_name,
        use_knowledge=use_knowledge,
        chain_of_thought=chain_of_thought,
        engine=engine,
    )

    if engine == "prem":
        api_config = APIConfig(
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        client = SQLGeneratorFromAPI(
            generator_config=generator_config, engine_config=api_config
        )

        client.generate_sql(num_rows=num_rows)

        metric_config = MetricConfig(num_cpus=14)
        metric_config.num_rows = num_rows

        # Doing execution here
        executor = SQLExecutorEX()
        _ = executor.execute_ex(
            generator_config=generator_config,
            metric_config=metric_config,
            num_rows=num_rows,
        )

        executor = SQLVesEvaluator()
        _ = executor.execute(
            generator_config=generator_config,
            metric_config=metric_config,
            num_rows=num_rows,
        )

    else:
        eval_client = None
        raise NotImplementedError(
            "Evaluation client for 'hf' engine is not implemented yet."
        )

    print("Starting to evaluate Generated SQL ...")


premai_models_list = [
    "claude-3.5-sonnet",
    "claude-3-opus",
    "command-r",
    "command-r-plus",
    "gemini-pro",
    "gemini-7b-it-fast",
    "gemma-2",
    "gpt-3.5-turbo",
    "gpt-4-turbo",
    "gpt-4o",
    "codellama-70b-instruct",
    "llama-3-8b-fast",
    "llama-3-8b-instruct",
    "mistral-large",
    "mistral-7b-instruct-v0.1",
    "mistral-8x7b-fast",
]
failed_models = []

for model in premai_models_list:
    print("Model name: ", model)
    print("-" * 91)

    try:
        generate_dev(
            engine="prem", model_name=model, use_knowledge=False, chain_of_thought=False
        )
    except Exception as e:
        print(
            f"Skipping for model: {model} (use_knowledge=False, chain_of_thought=False) due to: {str(e)}"
        )
        failed_models.append(
            {"model": model, "use_knowledge": False, "chain_of_thought": False}
        )
        continue

    try:
        generate_dev(
            engine="prem", model_name=model, use_knowledge=False, chain_of_thought=True
        )
    except Exception as e:
        print(
            f"Skipping for model: {model} (use_knowledge=False, chain_of_thought=True) due to: {str(e)}"
        )
        failed_models.append(
            {"model": model, "use_knowledge": False, "chain_of_thought": True}
        )
        continue

    try:
        generate_dev(
            engine="prem", model_name=model, use_knowledge=True, chain_of_thought=False
        )
    except Exception as e:
        print(
            f"Skipping for model: {model} (use_knowledge=True, chain_of_thought=False) due to: {str(e)}"
        )
        failed_models.append(
            {"model": model, "use_knowledge": True, "chain_of_thought": False}
        )
        continue

    try:
        generate_dev(
            engine="prem", model_name=model, use_knowledge=True, chain_of_thought=True
        )
    except Exception as e:
        print(
            f"Skipping for model: {model} (use_knowledge=True, chain_of_thought=True) due to: {str(e)}"
        )
        failed_models.append(
            {"model": model, "use_knowledge": True, "chain_of_thought": True}
        )
        continue

    print("-" * 91)

with open("failed.json", "w") as json_file:
    json.dump(failed_models, json_file)
