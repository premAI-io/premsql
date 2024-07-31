# Evaluation datasets

This component helps you evaluate your model or pipeline on several public benchmark datasets. As of now, we only support BirdBench. Based on demand, we will roll out support for other popular benchmark datasets like Spider and WikiSQL in the future.  

The current version supports and uses the BIRDBench dev dataset to perform all the evaluations. However, the structure of the dataset is as follows:

```
.
├── dev_databases
│   ├── california_schools
│   │   ├── california_schools.sqlite
│   │   └── database_description
│   ├── card_games
│   │   ├── card_games.sqlite
│   │   ├── card_games.sqlite-shm
│   │   ├── card_games.sqlite-wal
│   │   └── database_description
│   ├── codebase_community
│   │   ├── codebase_community.sqlite
│   │   └── database_description
│   ├── debit_card_specializing
│   │   ├── database_description
│   │   └── debit_card_specializing.sqlite
....
│   └── toxicology
│       ├── database_description
│       └── toxicology.sqlite
├── dev.json
```

Inside `dev_databases`, we have a different folder. Each folder is the name of the database. We have a .sqlite folder under that folder. Additionally, it has a `database_description`, which contains the CSV files of the tables in that database. The `dev.json` is a list of dictionaries that has the following contents:

```JSON
{
    "question_id": 0,
    "db_id": "california_schools",
    "question": "What is the highest eligible free rate for K-12 students in the schools in Alameda County?",
    "evidence": "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`",
    "SQL": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1",
    "difficulty": "simple"
},
```
Where, 

- `question_id`: An integer representing the unique identifier for the question.
db_id: A string indicating the database identifier where the query will be executed.
- `question`: A string containing the natural language question that needs to be converted to SQL.
- `evidence`: A string providing a brief explanation or formula that supports the formation of the SQL query. This acts as the domain knowledge needed about the database and its tables. 
- `SQL`: A string representing the SQL query generated to answer the natural language question. This is the ground truth.
- `difficulty`: A string indicating the level of difficulty of the SQL query, such as "simple," "medium," or "hard." 

This is how we load the database using text2sql library. 

```python 
from text2sql.eval.dataset import BirdBenchEvalDataset
from text2sql.eval.settings import SQLGeneratorConfig

config = SQLGeneratorConfig(model_name="some-experiment-name")
eval_dataset = BirdBenchEvalDataset(config=config)
```

You can see the raw data by simply doing:

```python
raw_validation_data = eval_dataset.data
```

### Filtering Options and processing

We use `process_and_filter` to do more processing on the top of the raw data. It starts by appending the database (.sqlite file path) for each json blob. It also provides the feature to filter the dataset and offset it to get a subset of the data. Here is how you do that:

```python
filter_by = ("difficulty", "simple")
offset = 50

dataset = eval_dataset.process_and_filter(
    num_rows=offset, 
    filter_by=filter_by
)
```

**NOTE**

Argument `filter_by` is a key, value pair. For the BirdBench dataset, there are only two types of filters that you can apply. Here are those:

- When the key is set to: `difficulty`, the values can be: 
  - simple
  - moderate
  - challenging

- When the key is set to `db_id`, the values can be:
  - european_football_2
  - toxicology
  - california_schools
  - student_club
  - superhero
  - card_games
  - thrombosis_prediction
  - financial
  - codebase_community
  - debit_card_specializing
  - formula_1

Key `db_id` only evaluates a specific database. You can check the contents of the database once the data is downloaded inside the `data/eval/dev_databases` folder. This folder will be present inside the folder you are running the experiments. When setting the offset, it will take only the first N rows of the dataset or the filtered dataset.

Both arguments are optional; not using them would load the full data. After applying the filter, our `dataset` will be a list of dictionaries here. Let's see what it looks like (showing you one instance):

```JSON
{
        "question_id": 0,
        "db_id": "california_schools",
        "question": "What is the highest eligible free rate for K-12 students in the schools in Alameda County?",
        "evidence": "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`",
        "SQL": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1",
        "difficulty": "simple",
        "db_path": "./data/eval/dev_databases/california_schools/california_schools.sqlite"
},
```
And `len(dataset)` would be 50 (here). 


## Applying prompts 

Once we get the preprocessed dataset, we apply prompt over it. We do this by the following code:

```python
dataset_with_prompt = dataset.apply_prompt(
    apply_knowledge=True, 
    header_prompt=None
)
```

We fetch the full description of the database along with the schema of the table and insert those schema inside the prompt. If you use:

- `apply_knowledge (bool)`: set as True, then it will use the evidence column else not. From experiments, it has been see that using knowledge it is more efficient. 

- `header_prompt (str)`: You can put additional instruction prompt to optimize or also you can put few shot examples from this. 

`dataset` internally is an object of [`DataInstance`](/text2sql/eval/dataset/bird.py) class, and you can use this to work out few shot examples to put inside header prompt for different tables. We can show that in an another example. This is how the prompt looks like:

```
CREATE TABLE frpm
(
    CDSCode                                       TEXT not null
        primary key,
    `Academic Year`                               TEXT  null,
    `County Code`                                 TEXT  null,
    `District Code`                               INTEGER         null,
    `School Code`                                 TEXT  null,
    `County Name`                                 TEXT null,
    `District Name`                               TEXT null,
    .....  (more columns here. Truncating for space)
)

CREATE TABLE satscores
(
    cds         TEXT not null
        primary key,
    rtype       TEXT  not null,
    sname       TEXT null,
    dname       TEXT null,
    .....  (more columns here. Truncating for space)
)

CREATE TABLE schools
(
    CDSCode     TEXT not null
        primary key,
    NCESDist    TEXT  null,
    NCESSchool  TEXT  null,
    StatusType  TEXT  not null,
    County      TEXT not null,
    District    TEXT not null,
    School      TEXT null,
    .....  (more columns here. Truncating for space)
)

-- External Knowledge: Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`

"-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above."

-- What is the highest eligible free rate for K-12 students in the schools in Alameda County?

Generate the SQL after thinking step by step: 

SELECT 
```

## Create your own Evaluation dataset

There might be instances, where you might need to evaluate with your own database. In those cases there could be two options:

- Case 1: Either your test data belongs inside sqlite databases. 
- Case 2: Or it uses any other engine like Postgres etc. 

### Case 1

Case 1 is super simple, you just need to follow the same folder strucure as [shown above](/docs/evaluation/dataset.md#evaluation-dataset). You need to maintain a `dev.json` which will contain the name of the database, the question, ground-truth and other parameters based on your need, such that it looks like this:

```
# Expected folder structure
data
.
└── eval
    ├── dev_databases
    │   ├── db_name_1
    │   ├── db_name_2
    ├── dev.json

# Content of each blob inside dev.json

{
    "question_id": 0,
    "db_id": "db_name",
    "question": "the natural language question",
    "evidence": "knowledge-if-any",
    "SQL": "ground-truth-goes-here"
},
```

Maintaining this structure would let you run the same pipeline flawlessly without any changes in the line of code. 

### Case 2

In this cases, you are not using any sqlite database. As a way around, you can do a simple migration to sqlite (as validation/test set databases does not need to be large). 

If you still want to connect with different databases, then please wait for sometime. Docs for these are on developement. In the meantime, you check out [our dataset code](/text2sql/eval/dataset/bird.py). You need to come up with similar class stucture such that you can finally have a structure like the JSON blobs shown above. 
