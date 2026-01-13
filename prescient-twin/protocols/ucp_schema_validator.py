import json
from functools import lru_cache
from importlib.resources import files
from typing import Any, Dict

from jsonschema import validate, ValidationError, SchemaError

# Define the package where UCP schemas are expected to be located.
# This assumes a directory structure like:
# prescient-twin/
# ├── protocols/
# │   ├── __init__.py
# │   ├── ucp_schema_validator.py
# │   └── schemas/
# │       ├── ucp_request_schema.json
# │       └── ucp_response_schema.json
SCHEMA_PACKAGE = "prescient_twin.protocols.schemas"
UCP_REQUEST_SCHEMA_FILE = "ucp_request_schema.json"
UCP_RESPONSE_SCHEMA_FILE = "ucp_response_schema.json"


class UCPSchemaError(Exception):
    """Custom exception for issues related to UCP schema loading or validation setup."""
    pass


@lru_cache(maxsize=None)
def _load_schema(schema_filename: str) -> Dict[str, Any]:
    """
    Loads a JSON schema from the specified package resource and caches it.

    This function uses `importlib.resources.files` for robust and package-aware
    loading of schema files, ensuring they can be found whether the package
    is installed or run directly. The `@lru_cache` decorator ensures that
    each schema is loaded only once.

    Args:
        schema_filename: The name of the schema file (e.g., "ucp_request_schema.json").

    Returns:
        The loaded JSON schema as a dictionary.

    Raises:
        UCPSchemaError: If the schema file cannot be found, is not valid JSON,
                        or any other error occurs during loading.
    """
    try:
        schema_path = files(SCHEMA_PACKAGE) / schema_filename
        with schema_path.open('r', encoding='utf-8') as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError as e:
        raise UCPSchemaError(
            f"UCP schema file not found: '{schema_filename}' in package '{SCHEMA_PACKAGE}'. "
            "Ensure the schema file exists and is correctly placed."
        ) from e
    except json.JSONDecodeError as e:
        raise UCPSchemaError(
            f"Invalid JSON in UCP schema file '{schema_filename}': {e}. "
            "Ensure the schema file contains valid JSON."
        ) from e
    except Exception as e:
        raise UCPSchemaError(
            f"An unexpected error occurred while loading UCP schema '{schema_filename}': {e}"
        ) from e


def get_ucp_request_schema() -> Dict[str, Any]:
    """
    Retrieves the cached UCP request schema.

    Returns:
        The UCP request schema as a dictionary.
    """
    return _load_schema(UCP_REQUEST_SCHEMA_FILE)


def get_ucp_response_schema() -> Dict[str, Any]:
    """
    Retrieves the cached UCP response schema.

    Returns:
        The UCP response schema as a dictionary.
    """
    return _load_schema(UCP_RESPONSE_SCHEMA_FILE)


def validate_ucp_request(request_data: Dict[str, Any]) -> None:
    """
    Validates an outgoing UCP request against the official UCP request schema.

    This function ensures that the structure and data types of the request
    adhere to the UCP specification, promoting data integrity and protocol compliance.

    Args:
        request_data: The UCP request data as a dictionary.

    Raises:
        ValidationError: If the `request_data` does not conform to the UCP request schema.
                         This exception provides details about the validation failure.
        SchemaError: If the loaded UCP request schema itself is invalid according to
                     the JSON Schema draft specification. This indicates an issue
                     with the schema definition, not the data being validated.
        UCPSchemaError: If there's an issue loading or parsing the schema file.
        RuntimeError: For any other unexpected errors during the validation process.
    """
    try:
        schema = get_ucp_request_schema()
        validate(instance=request_data, schema=schema)
    except (ValidationError, SchemaError, UCPSchemaError) as e:
        # Re-raise specific validation or schema loading errors directly
        raise e
    except Exception as e:
        # Catch any other unexpected errors during validation
        raise RuntimeError(f"An unexpected error occurred during UCP request validation: {e}") from e


def validate_ucp_response(response_data: Dict[str, Any]) -> None:
    """
    Validates an incoming UCP response against the official UCP response schema.

    This function ensures that the structure and data types of the response
    adhere to the UCP specification, promoting data integrity and protocol compliance.

    Args:
        response_data: The UCP response data as a dictionary.

    Raises:
        ValidationError: If the `response_data` does not conform to the UCP response schema.
                         This exception provides details about the validation failure.
        SchemaError: If the loaded UCP response schema itself is invalid according to
                     the JSON Schema draft specification. This indicates an issue
                     with the schema definition, not the data being validated.
        UCPSchemaError: If there's an issue loading or parsing the schema file.
        RuntimeError: For any other unexpected errors during the validation process.
    """
    try:
        schema = get_ucp_response_schema()
        validate(instance=response_data, schema=schema)
    except (ValidationError, SchemaError, UCPSchemaError) as e:
        # Re-raise specific validation or schema loading errors directly
        raise e
    except Exception as e:
        # Catch any other unexpected errors during validation
        raise RuntimeError(f"An unexpected error occurred during UCP response validation: {e}") from e