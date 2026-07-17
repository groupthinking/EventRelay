🔒 Fix SQL injection in get_innovation_dashboard

🎯 **What:** The vulnerability fixed
Resolved a SQL injection vulnerability in `get_innovation_dashboard` of `scripts/archive/youtube_innovation_learning_database.py`. The original implementation used f-strings to inject SQL directly into queries via `conn.execute(f"...")` utilizing dynamic time filters.

⚠️ **Risk:** The potential impact if left unfixed
A maliciously crafted `time_range` argument (or any unchecked dictionary key in a theoretical similar context) could allow execution of arbitrary SQL commands. This could lead to information disclosure or data destruction.

🛡️ **Solution:** How the fix addresses the vulnerability
Replaced f-strings with parameterized queries using `?`. To support `datetime` manipulation properly within SQLite, updated the `time_filters` dictionary to store valid modifiers (`-1 day`, `-7 days`, `-100 years`) and parameterized the offset in the query string `datetime('now', ?)`. Automated linting via `ruff check --fix` and formatting via `black` were run afterwards.
