COT_WIZARD = """
\nGenerate the SQL after thinking step by step: 
"""

PATTERN_PROMPT_NO_KG = """
-- Using valid SQLite, answer the following questions for the tables provided above
"""

PATTERN_PROMPT_KG = """
"-- Using valid SQLite and understading External Knowledge, answer the following questions for the tables provided above."
"""

SYSTEM_PROMPT = """
Only output the SQL query from the given context and what ever is asked to retrieve. You should NOT give or output anything else other than the SQL query. ONLY THE RAW SQL. 
"""
