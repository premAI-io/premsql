## Prem text2sql

Welcome to the text2sql documentation. This library offers modular tools and components designed to help developers create more efficient and reliable text-to-SQL models and engines. Please note: This library is in its early stages. We are actively developing additional features, which will be released soon.

### High level architecture

In a high level, this library is composed of the following components shown in this figure below:


![text2sql architecture](/docs/assets/text2sql_arch.png)

As shown in the figure above this library aims to provide the following components:

- `evaluator`: This will help you to evaluate your text2sql models or systems on different benchmark dataset. Currently the first version of this component is released. We do our benchmarking with [BIRDBench dataset](https://bird-bench.github.io/). However our API is very much modular, so you can extend it to other custom datasets aslong it follows a specific format. More on that in our [evaluation section](/docs/evaluation.md). 

- `synthetic data generator`: Sometimes if you need to make very domain specific text2sql models which needs to be tuned on your data, you would need data points (user query - sql query pair). Doing it manually is very much time taking. So this module will help you to do that faster. (This is on developement)

- `fine-tuner`: This module will help you to perform multiple fine-tuning experiments on different LLMs/SLMs over existing dataset or your own dataset. 

- `connector`: This component would help you to connect your text2sql pipeline with your data source. This can be a simple postgres database or any cloude DB instance. (This is on developement)

- `agents`: Finally, agents is aimed to help you to build end to end pipelines with different types of function / tool calls. This module would act as an orchestractor that would generate SQLs from text, validate SQLs, run into sandboxes / connectors, do self-correction etc so that you can get as much robust performances as possible. (This is on developement)

### A note on our Roadmap

As of now, we have just released our very first alpha version of our evaluator. However in terms of priority, we would be developing first the fine-tuner component and make more improvements for evaluator. After this we would be moving towards connectors and synthetic data generator and agents. 