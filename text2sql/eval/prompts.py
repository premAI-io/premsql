# All the big prompts are stored here

PATTERN_PROMPT_NO_KG = """
-- Using valid SQLite, answer the following questions for the tables provided above
"""

PATTERN_PROMPT_KG = """
"-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above."
"""

# Few shot cot prompts with KG

INI_TABLE_KG = """
CREATE TABLE singer\n(\n    singer_id         TEXT not null\n        primary key,\n    nation       TEXT  not null,\n    sname       TEXT null,\n    dname       TEXT null,\n    cname       TEXT null,\n    age    INTEGER         not null,\n    year  INTEGER          not null,\n    birth_year  INTEGER          null,\n    salary  REAL          null,\n    city TEXT          null,\n    phone_number   INTEGER          null,\n--     tax   REAL      null,\n)
"""

INI_PROMPT_KG = """
-- External Knowledge: age = year - birth_year;\n-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.\n-- How many singers in USA who is older than 27?\nThe final SQL is: Let's think step by step.
"""

INI_COT_RESULT_KG = """
1. referring to external knowledge, we need to filter singers 'by year' - 'birth_year' > 27; 2. we should find out the singers of step 1 in which nation = 'US', 3. use COUNT() to count how many singers. Finally the SQL is: SELECT COUNT(*) FROM singer WHERE year - birth_year > 27;</s>
"""

# Few shot cot prompts without KG


INI_TABLE_NO_KG = """
CREATE TABLE singer\n(\n    singer_id         TEXT not null\n        primary key,\n    nation       TEXT  not null,\n    sname       TEXT null,\n    dname       TEXT null,\n    cname       TEXT null,\n    age    INTEGER         not null,\n    year  INTEGER          not null,\n    age  INTEGER          null,\n    salary  REAL          null,\n    city TEXT          null,\n    phone_number   INTEGER          null,\n--     tax   REAL      null,\n)
"""

INI_PROMPT_NO_KG = """
-- External Knowledge:\n-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above.\n-- How many singers in USA who is older than 27?\nThe final SQL is: Let's think step by step.
"""

INI_COT_RESULT_NO_KG = """
1. 'older than 27' refers to age > 27 in SQL; 2. we should find out the singers of step 1 in which nation = 'US', 3. use COUNT() to count how many singers. Finally the SQL is: SELECT COUNT(*) FROM singer WHERE age > 27;</s>
"""

COT_WIZARD = """
\nGenerate the SQL after thinking step by step: 
"""

SYSTEM_PROMPT = """
Only output the SQL query from the given context and what ever is asked to retrieve. You should NOT give or output anything else other than the SQL query. ONLY THE RAW SQL. DO not start with ```sql or end with ```. JUST the raw SQL query.
"""
