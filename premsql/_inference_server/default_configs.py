# The way it works:
# - every agent (main) should contain some set of workers,
#   executors

import premsql.generators as generators
import premsql.executors as executors
import premsql.prompts as prompts 
import premsql.pipelines as pipelines

# Define the pipeline mapping
pipelines_mapping = {
    "simple_agent": pipelines.SimpleText2SQLAgent
}

# Define the config the pipeline which is being mapped
config = {
    "simple_agent": {
        "init": {
            "generator": generators.Text2SQLGeneratorMLX(
                model_name_or_path="premai-io/prem-1B-SQL",
                experiment_name="default_mlx_generator",
                type="test"
            ),
            "corrector": None,
            "executor": executors.ExecutorUsingLangChain()
        },
        "run": {
            "prompt_template": prompts.OLD_BASE_TEXT2SQL_PROMPT,
            "additional_knowledge": None,
            "fewshot_dict": None, 
            "temperature": 0.1,
            "max_new_tokens": 256,
            "render_results_using": "json"
        }
    }
}
