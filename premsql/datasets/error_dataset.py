import json
from pathlib import Path
from typing import Optional, Union

from tqdm import tqdm

from premsql.datasets.base import SupervisedDatasetForTraining, Text2SQLBaseInstance
from premsql.datasets.prompts import ERROR_HANDLING_PROMPT
from premsql.evaluator.base import Text2SQLEvaluatorBase
from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger

logger = setup_console_logger("[ERROR-HANDLING-DATASET]")


class ErrorDatasetInstance(Text2SQLBaseInstance):
    def __init__(self, dataset: list[dict]) -> None:
        super().__init__(dataset=dataset)

    def apply_prompt(
        self,
        prompt_template: Optional[str] = ERROR_HANDLING_PROMPT,
    ):
        data_to_return = []
        for content in tqdm(
            self.dataset, total=len(self.dataset), desc="Applying error prompt"
        ):
            assert "error" in content, "key error is not present"
            error_msg = content["error"]
            prompt = content["prompt"].split("# SQL:")[0].strip()
            prediction = content["generated"]
            error_prompt = prompt_template.format(
                existing_prompt=prompt, sql=prediction, error_msg=error_msg
            )
            data_to_return.append({**content, "prompt": error_prompt})
        return data_to_return


# TODO: Error dataset is not very much optimized
# Since this is not using batching to make the computation first
# We need to optimize this for more faster operations, since this is
# been operated on training data level.
class ErrorDataset:

    @classmethod
    def from_existing(
        cls, eval_path: Union[str, Path], model_name_or_path: Optional[str] = None
    ):
        pass

    @classmethod
    def from_generator(
        cls,
        experiment_name: str,
        generator: Text2SQLGeneratorBase,
        ex_evaluator: Text2SQLEvaluatorBase,
        tokenize: Optional[bool] = False,
        **kwargs
    ):
        dataset = json.load(
            open(Path("./experiments") / "train" / experiment_name / "predict.json"),
            "r",
        )
        error_based_reponses = []

        for content in tqdm(
            dataset, total=len(dataset), desc="Generating results and evaluating"
        ):
            prompt = content["prompt"]
            input_ids = generator.tokenizere.encode(
                text=prompt,
                return_tensors="pt",
                padding="longest",
                max_length=generator.tokenizer.model_max_length,
                truncation=True,
            ).to(generator.device)

            output_tokens = (
                generator.generate(
                    input_ids=input_ids,
                    do_sample=False,
                    max_new_tokens=256,
                    pad_token_id=generator.tokenizer.eos_token_id,
                    **kwargs
                )
                .detach()
                .tolist()[0]
            )
            output_tokens = (
                output_tokens[len(input_ids[0]) :]
                if len(output_tokens) > len(input_ids[0])
                else output_tokens
            )
            generated = generator.postprocess(
                generated.tokenizer.decode(output_tokens, skip_special_tokens=True)
            )

            # Now run this thing into the executor
            result = ex_evaluator.execute_model(
                predicted_sql=generated,
                ground_truth_sql=content["SQL"],
                dsn_or_db_path=content["db_path"],
            )
            error = result["error"]
            if error:
                error_based_reponses.append({**content, "error": error})

        error_instance = ErrorDatasetInstance(dataset=error_based_reponses)
        # Also save the results
        path_to_save = (
            Path("./experiments") / "train" / experiment_name / "error_dataset.json"
        )

        if not path_to_save.exists():
            with open(path_to_save, "w") as json_file:
                json.dump(error_instance, json_file)
            logger.info("Saved Error dataset in {}".format(path_to_save))

        return (
            error_instance
            if not tokenize
            else SupervisedDatasetForTraining(
                dataset=error_instance,
                model_name_or_path=generator.model_name_or_path,
                hf_token=kwargs.get("hf_token", None),
            )
        )
