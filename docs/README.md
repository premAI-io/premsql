## Prem text2sql

Welcome to the text2sql documentation. This library offers modular tools and components designed to help developers create more efficient and reliable text-to-SQL models and engines. Please note: This library is in its early stages. Currently we support evaluation. We are actively developing the other mentioned features, which we will roll out soon.

### High-level architecture

In a high level, this library is composed of the following components shown in the figure below:


![text2sql architecture](/docs/assets/text2sql_arch.png)

As shown in the figure above, this library aims to provide the following components:

- `evaluator`: This will help you to evaluate your text2sql models or systems on different benchmark dataset. Currently, the first version of this component is released. We do our benchmarking with [BIRDBench dataset](https://bird-bench.github.io/). However, our API is very much modular, so you can extend it to other custom datasets as long it follows a specific format. More on that in our [evaluation section](/docs/evaluation.md). 

- `Synthetic data generator`: Sometimes, if you need to make domain-specific text2sql models that need to be tuned on your data, you would need data points (user query - SQL query pair). Doing it manually is very much time-consuming. So this module will help you to do that faster. (This is on development)

- `fine-tuner`: This module will help you to perform multiple fine-tuning experiments on different LLMs/SLMs over existing datasets or your dataset. 

- `connector`: This component would help you to connect your text2sql pipeline with your data source. This can be a simple Postgres database or any cloud DB instance. (This is on development)

- `agents`: Finally, agents are aimed to help you to build end-to-end pipelines with different types of function/tool calls. This module would act as an orchestractor that would generate SQLs from text, validate SQLs, run into sandboxes/connectors, do self-correction etc so that you can get as much robust performances as possible. (This is on development)

### A note on our Roadmap

As of now, we have just released our very first alpha version of our evaluator. However, in terms of priority, we will first develop the fine-tuner component and make more improvements to the evaluator. After this, we will move towards connectors, synthetic data generators, and agents. 
