import re
import time
import ollama


LOCAL_MODEL_NAME = "gemma3:4b"


def generate_sql(user_prompt, db_schema):
    system_prompt = f"""
You are a precise SQLite text-to-SQL generator.

RULES:
1. Generate exactly one valid SQLite SELECT query.
2. Use ONLY tables and columns present in the schema.
3. Never invent columns, tables, or relationships.
4. Follow the foreign key relationships provided in the schema.
5. Verify every JOIN condition carefully.
6. For revenue or sales, use InvoiceLine.UnitPrice *
   InvoiceLine.Quantity, unless the question specifies otherwise.
7. Use appropriate GROUP BY and aggregate functions.
8. Do not use INSERT, UPDATE, DELETE, DROP, or other
   data-modifying statements.
9. Return ONLY the SQL query inside a ```sql code block.
10. If information needed to answer is missing from the
    schema, do not invent it.

Database Schema:
{db_schema}
"""

    response = ollama.chat(
        model=LOCAL_MODEL_NAME,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Write a SQL query for {user_prompt}"}
        ],
        options={
            'temperature': 0.0
        }
    )

    print("Total duration:", response.get("total_duration", 0) / 1e9, "seconds")
    print("Load duration:", response.get("load_duration", 0) / 1e9, "seconds")
    print("Prompt evaluation:", response.get("prompt_eval_duration", 0) / 1e9, "seconds")
    print("Generation:", response.get("eval_duration", 0) / 1e9, "seconds")
    print("Tokens generated:", response.get("eval_count", 0))
    # Return the SQL query block only
    # If not found then return full response content
    content = response['message']['content']
    match = match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()



if __name__ == '__main__':
    from database import get_db_schema, execute_sql
    # user_prompt = "Show all customers with their first name, last name, and email."
    user_prompt = "Find the top 5 best-selling artists based on total track sales"
    db_schema = get_db_schema(r"data/Chinook_Sqlite.sqlite")
    print("Model Running...")
    start_time = time.time()
    sql = generate_sql(user_prompt, db_schema)  # Replace with your function name
    end_time = time.time()
    print("Generated SQL:")
    print(sql)
    print("\n\nTime taken:", end_time - start_time, "seconds")