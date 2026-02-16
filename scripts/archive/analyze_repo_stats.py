import os
from google.cloud import bigquery

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


def run_dashboard():
    client = bigquery.Client()

    with open("scripts/repository_health_dashboard.sql", "r") as f:
        sql_content = f.read()

    # Split by semicolon to get individual queries
    queries = [q.strip() for q in sql_content.split(";") if q.strip()]

    print("# Repository Health Dashboard\n")

    query_names = [
        "Tech Stack Distribution",
        "Complexity/Depth Analysis",
        "Legacy/Archive Candidates",
        "Duplicate File Detection",
        "Python Entry Points",
        "Test Files",
    ]

    for i, query in enumerate(queries):
        if i < len(query_names):
            print(f"## {query_names[i]}")
        else:
            print(f"## Query {i+1}")

        try:
            job = client.query(query)
            results = job.result()

            data = [dict(row) for row in results]
            if data:
                headers = data[0].keys()
                rows = [[row[col] for col in headers] for row in data]
                # Use tabulate if available, else simple pipe format
                if tabulate:
                    print(tabulate(rows, headers=headers, tablefmt="github"))
                else:
                    print(f"| {' | '.join(headers)} |")
                    print(f"| {' | '.join(['---']*len(headers))} |")
                    for row in rows:
                        print(f"| {' | '.join(str(x) for x in row)} |")
            else:
                print("No results found.")

            print("\n")
        except Exception as e:
            print(f"Error running query: {e}\n")


if __name__ == "__main__":
    run_dashboard()
