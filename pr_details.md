Title: 🔒 fix: prevent SQL injection in database cleanup service

Description:
🎯 **What:** Fixed a SQL/Command injection vulnerability in `DatabaseCleanupService` caused by directly inserting untrusted table names into SQLite PRAGMA and DELETE statements.

⚠️ **Risk:** If a malicious string could be supplied as a `table_name` in a `RetentionPolicy`, it could be used to execute arbitrary SQL commands, resulting in data loss, schema manipulation, or data exposure.

🛡️ **Solution:** Added a strict allowlist validation using a regular expression (`^[a-zA-Z0-9_]+$`) that guarantees the `table_name` only contains valid alphanumeric characters and underscores. If validation fails, the process aborts safely. As defense-in-depth, the table name is correctly quoted using double quotes. Also created unit tests to confirm valid names succeed and malicious ones are rejected.
