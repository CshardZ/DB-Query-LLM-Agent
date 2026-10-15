import re
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.align import Align

LOCAL_MODEL_NAME = "gemma3:4b"
console = Console()


def generate_sql(user_prompt: str, db_schema: str, error_message: str = None, failed_sql: str = None) -> str:
    system_prompt = f"""You are a precise SQLite text-to-SQL generator.

CRITICAL JOIN & COLUMN RULES:
1. Generate exactly one valid SQLite SELECT query.
2. Examine the database schema carefully. Verify which table contains each column before referencing it.
3. Check column locations:
   - 'Quantity' belongs to 'InvoiceLine', NOT 'Track'.
   - 'UnitPrice' exists on 'Track' and 'InvoiceLine'.
   - To calculate sales/revenue or quantities, join Track -> InvoiceLine on Track.TrackId = InvoiceLine.TrackId.
4. Follow foreign keys in both direction to construct complete JOIN chains (e.g., Artist -> Album -> Track -> InvoiceLine).
5. Do not invent non-existent columns on any table.
6. Return ONLY the executable SQL query enclosed inside a ```sql ``` code block.

Database Schema Context:
{db_schema}
"""

    if error_message and failed_sql:
        user_message = f"""The previous SQL query failed during execution.

User Question: {user_prompt}
Failed SQL Query:
{failed_sql}

SQLite Error Message:
{error_message}

Carefully re-check column locations across all tables in the schema above and write a corrected SQLite query."""
    else:
        user_message = f"Write a SQL query for: {user_prompt}"

    response = ollama.chat(
        model=LOCAL_MODEL_NAME,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ],
        options={'temperature': 0.0}
    )

    content = response['message']['content']
    match = re.search(r"```sql\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def synthesize_answer(user_prompt: str, sql_query: str, columns: list, rows: list) -> str:
    sys_prompt = """You are an executive data analyst.
Your job is to deliver high-level, human-understandable insights based on database query results.

RESPONSE FORMAT RULES:
1. DO NOT output raw table dumps, individual lists of rows, or SQL column names.
2. Deliver high-level analytical insights, patterns, or metric summaries.
3. Format all takeaways using concise, clean bullet points.
4. Highlight important numbers, metrics, or entities using bold text.
5. Keep explanations direct, professional, and clear."""

    total_rows = len(rows)
    displayed_rows = rows[:10]
    
    formatted_data = f"Total Row Count: {total_rows}\nColumns: {columns}\nData Sample:\n{displayed_rows}"
    
    user_context = f"""User Question: {user_prompt}
Executed SQL Query: {sql_query}
QueryResult Context:
{formatted_data}

Provide clear, high-level insights addressing the user's question in clean bullet points."""

    response = ollama.chat(
        model=LOCAL_MODEL_NAME,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_context}
        ],
        options={"temperature": 0.2}
    )
    
    return response['message']['content']


def run_agent(db_path: str, user_question: str, max_retries: int = 2):
    from database import get_db_schema, execute_sql

    # Centered Title Header using Align.center
    title_panel = Panel(
        Align.center(f"[bold cyan]Database:[/] {db_path}\n[bold cyan]User Query:[/] {user_question}"),
        title="[bold white]DATABASE QUERY LLM AGENT[/]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(title_panel)

    with console.status("[bold green]Analyzing database schema...", spinner="dots"):
        console.print("[bold yellow][Step 1][/] Analyzing Database Schema")
        schema = get_db_schema(db_path)

    with console.status("[bold green]Generating SQL query with Gemma-3:4b...", spinner="dots"):
        console.print("[bold yellow][Step 2][/] Generating SQL Query")
        sql_query = generate_sql(user_question, schema)
    
    syntax = Syntax(sql_query, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="Generated SQL", border_style="dim"))

    with console.status("[bold green]Executing SQL query...", spinner="dots"):
        console.print("[bold yellow][Step 3][/] Executing Query")
        columns, results, error = execute_sql(db_path, sql_query)

    attempts = 0
    while error and attempts < max_retries:
        attempts += 1
        console.print(f"[bold red]SQL Error:[/] {error}")
        console.print(f"[bold yellow][Step 3.1][/] Attempting Auto-Correction ({attempts}/{max_retries})")
        
        with console.status("[bold green]Fixing SQL query...", spinner="dots"):
            sql_query = generate_sql(user_prompt=user_question, db_schema=schema, error_message=str(error), failed_sql=sql_query)
        
        syntax = Syntax(sql_query, "sql", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Corrected SQL", border_style="dim"))
        columns, results, error = execute_sql(db_path, sql_query)

    if error:
        console.print(Panel(f"[bold red]Execution Failed:[/] {error}", border_style="red"))
        return

    console.print(f"[dim]Query succeeded — {len(results)} rows returned.[/dim]\n")

    with console.status("[bold green]Synthesizing insights...", spinner="dots"):
        console.print("[bold yellow][Step 4][/] Synthesizing Insights")
        final_answer = synthesize_answer(user_question, sql_query, columns, results)

    console.print(
        Panel(
            Markdown(final_answer),
            title="[bold green]FINAL INSIGHTS[/]",
            border_style="green"
        )
    )


if __name__ == '__main__':
    user_prompt = "Find the top 5 best-selling artists based on total track sales"

    run_agent(
        db_path=r"data/Chinook_Sqlite.sqlite",
        user_question=user_prompt
    )