ERROR_HANDLING_PROMPT = """
{existing_prompt}

# Generated SQL: {sql}

## Error Message

{error_msg}

Carefully review the original question and error message, then rewrite the SQL query to address the identified issues. 
Ensure your corrected query uses correct column names, 
follows proper SQL syntax, and accurately answers the original question 
without introducing new errors.

# SQL: 
"""
