-- Repository Health Dashboard Queries
-- 1. Tech Stack Distribution
-- Usage: Identify the dominant languages and file types in the repository.
SELECT extension,
    COUNT(*) as file_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
WHERE extension IS NOT NULL
GROUP BY extension
ORDER BY file_count DESC
LIMIT 15;
-- 2. Complexity/Depth Analysis
-- Usage: Understand the structural depth of the codebase.
SELECT depth,
    COUNT(*) as item_count,
    COUNTIF(is_directory) as directories,
    COUNTIF(NOT is_directory) as files
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
GROUP BY depth
ORDER BY depth;
-- 3. Legacy/Archive Candidate Identification
-- Usage: Find files in paths that suggest they are deprecated or archived.
SELECT path,
    name
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
WHERE regexp_contains(
        lower(path),
        r 'archive|deprecated|old|legacy|backup'
    )
ORDER BY path;
-- 4. Duplicate File Detection
-- Usage: Find files with the same name strategies to identify copy-paste code.
SELECT name,
    COUNT(*) as count
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
WHERE NOT is_directory
GROUP BY name
HAVING count > 5
ORDER BY count DESC
LIMIT 20;
-- 5. Python Entry Points
-- Usage: Identify main entry points for Python applications.
SELECT path
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
WHERE name LIKE 'main.py'
    OR name LIKE '__main__.py'
    OR name LIKE 'server.py';
-- 6. Test Files
-- Usage: Estimate test coverage by file count.
SELECT path
FROM `uvai-730bb.eventrelay_metadata.repository_tree`
WHERE name LIKE 'test_%'
    OR name LIKE '%_test.py'
    OR path LIKE '%/tests/%';