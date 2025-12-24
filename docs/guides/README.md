# Video dev 

This directory contains a FastAPI server that provides read-only access to the project files, along with dependency management and logging endpoints.

## Setup

1.  **Install Dependencies**: Make sure you have Python and pip installed. It's recommended to use a virtual environment.

    ```sh
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    pip install -e .[youtube,ml,postgres]
    pip install -e .
    ```

2.  **Run the Server**: You can run the server using the VSCode task you created.
    *   Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`).
    *   Type `Tasks: Run Task`.
    *   Select `Run Read-Only Proxy`.

    Alternatively, you can run it from the command line:
    ```sh
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
    ```

## Testing

The easiest way to test the server is to use the provided `api_test.http` file inside Cursor.

1.  Open the `api_test.http` file.
2.  Click the "Send Request" link that appears above any of the endpoint blocks.
3.  The response from the server will appear directly in an inline editor.

This provides a one-click harness to validate every endpoint without needing Postman, `curl`, or a browser.

## Endpoint Guide

### Health Check

*   `GET /status`: A lightweight health check to confirm the server is running.

### File System

*   `GET /list`: Lists all project files. Use `?all=true` to include files in `.venv`.
*   `GET /file?path=...`: Fetches the content of a specific file.
*   `GET /search?query=...`: Searches for a string in all files.
    *   `&regex=true`: Treat the query as a regular expression.
    *   `&all=true`: Include `.venv` in the search.

### Dependencies

*   `GET /dependencies`: Checks for drift between declared and installed dependencies.
*   `POST /dependencies/update`: Installs dependencies (legacy; now use pyproject extras).
*   `POST /dependencies/sync`: Writes legacy `requirements.txt` snapshot for drift detection.

### Logging

*   `GET /logs`: Retrieves the most recent logs from the in-memory buffer.
    *   `?event=...`: Filter logs by a specific event type.
*   `GET /logs/stream`: Streams logs in real-time using Server-Sent Events (SSE).
*   `POST /logs/clear`: Manually clears the log buffer.

### Restore a backup (replace with a real timestamp from /backups)
POST http://localhost:8000/dependencies/restore/YYYY-MM-DDTHHMMSS


## Scope and Limitations

- **Content Focus:** This system is designed primarily for educational and technical video content. Music videos are explicitly out of scope for processing.
