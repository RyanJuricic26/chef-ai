# sql_validator.py
import re
import sqlparse
from typing import Dict, Any, Literal
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of SQL validation"""
    is_valid: bool
    error_message: str = ""
    warnings: list[str] = []
    sanitized_query: str = ""


# Database Schema Definition
DATABASE_SCHEMA = {
    "tables": {
        "users": {
            "columns": ["id", "name"],
            "description": "User information"
        },
        "recipes": {
            "columns": [
                "id", "name", "description", "instructions",
                "prep_time", "cook_time", "servings", "difficulty",
                "cuisine_type", "url", "created_at"
            ],
            "description": "Recipe information with cooking details"
        },
        "ingredients": {
            "columns": ["id", "name", "category"],
            "description": "Available ingredients"
        },
        "recipe_ingredients": {
            "columns": [
                "id", "recipe_id", "ingredient_id",
                "quantity", "unit", "notes"
            ],
            "description": "Junction table linking recipes to ingredients"
        }
    },
    "relationships": {
        "recipe_ingredients.recipe_id": "recipes.id",
        "recipe_ingredients.ingredient_id": "ingredients.id"
    }
}


def get_schema_documentation() -> str:
    """
    Generate formatted schema documentation for LLM context

    Returns:
        Formatted schema string
    """
    doc = "DATABASE SCHEMA:\n\n"

    for table_name, table_info in DATABASE_SCHEMA["tables"].items():
        doc += f"Table: {table_name}\n"
        doc += f"Description: {table_info['description']}\n"
        doc += f"Columns: {', '.join(table_info['columns'])}\n\n"

    doc += "RELATIONSHIPS:\n"
    for fk, pk in DATABASE_SCHEMA["relationships"].items():
        doc += f"- {fk} -> {pk}\n"

    return doc


def check_for_sql_injection(query: str) -> tuple[bool, str]:
    """
    Check for common SQL injection patterns

    Args:
        query: SQL query to check

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Normalize query for checking
    normalized = query.lower().strip()

    # Dangerous patterns
    dangerous_patterns = [
        (r';\s*drop\s+table', "Detected DROP TABLE command"),
        (r';\s*delete\s+from', "Detected DELETE command"),
        (r';\s*update\s+', "Detected UPDATE command"),
        (r';\s*insert\s+into', "Detected INSERT command"),
        (r';\s*alter\s+table', "Detected ALTER TABLE command"),
        (r';\s*create\s+table', "Detected CREATE TABLE command"),
        (r';\s*truncate\s+', "Detected TRUNCATE command"),
        (r'--', "Detected SQL comment (possible injection)"),
        (r'/\*', "Detected multi-line comment (possible injection)"),
        (r'union\s+select', "Detected UNION SELECT (possible injection)"),
        (r'exec\s*\(', "Detected EXEC command"),
        (r'execute\s*\(', "Detected EXECUTE command"),
        (r'xp_', "Detected extended stored procedure"),
        (r'sp_', "Detected stored procedure"),
    ]

    for pattern, message in dangerous_patterns:
        if re.search(pattern, normalized):
            return False, f"Security violation: {message}"

    # Check for multiple statements (semicolon followed by another statement)
    statements = [s.strip() for s in normalized.split(';') if s.strip()]
    if len(statements) > 1:
        return False, "Multiple SQL statements not allowed"

    return True, ""


def validate_query_structure(query: str) -> tuple[bool, str]:
    """
    Validate that the query is properly structured and only uses SELECT

    Args:
        query: SQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Parse the SQL
        parsed = sqlparse.parse(query)

        if not parsed:
            return False, "Unable to parse SQL query"

        statement = parsed[0]

        # Check that it's a SELECT statement
        if statement.get_type() != 'SELECT':
            return False, f"Only SELECT queries allowed. Got: {statement.get_type()}"

        return True, ""

    except Exception as e:
        return False, f"SQL parsing error: {str(e)}"


def validate_schema_references(query: str) -> tuple[bool, str, list[str]]:
    """
    Validate that all referenced tables and columns exist in schema

    Args:
        query: SQL query to validate

    Returns:
        Tuple of (is_valid, error_message, warnings)
    """
    warnings = []
    normalized = query.lower()

    # Extract table references
    table_pattern = r'\b(?:from|join)\s+([a-z_][a-z0-9_]*)'
    referenced_tables = set(re.findall(table_pattern, normalized))

    # Check all referenced tables exist
    valid_tables = set(DATABASE_SCHEMA["tables"].keys())
    invalid_tables = referenced_tables - valid_tables

    if invalid_tables:
        return False, f"Invalid table(s) referenced: {', '.join(invalid_tables)}", []

    # Extract column references (basic check)
    # This is simplified - full validation would require a SQL parser
    for table in referenced_tables:
        valid_columns = DATABASE_SCHEMA["tables"][table]["columns"]

        # Look for table.column patterns
        column_pattern = rf'{table}\.([a-z_][a-z0-9_]*)'
        referenced_columns = re.findall(column_pattern, normalized)

        for col in referenced_columns:
            if col not in valid_columns:
                warnings.append(f"Column '{col}' may not exist in table '{table}'")

    return True, "", warnings


def validate_sql_query(query: str) -> ValidationResult:
    """
    Comprehensive SQL validation with security and schema checks

    Args:
        query: SQL query to validate

    Returns:
        ValidationResult with validation status and details
    """
    # 1. Check for SQL injection
    is_safe, injection_error = check_for_sql_injection(query)
    if not is_safe:
        return ValidationResult(
            is_valid=False,
            error_message=injection_error
        )

    # 2. Validate query structure
    is_valid_structure, structure_error = validate_query_structure(query)
    if not is_valid_structure:
        return ValidationResult(
            is_valid=False,
            error_message=structure_error
        )

    # 3. Validate schema references
    is_valid_schema, schema_error, warnings = validate_schema_references(query)
    if not is_valid_schema:
        return ValidationResult(
            is_valid=False,
            error_message=schema_error,
            warnings=warnings
        )

    # All checks passed
    return ValidationResult(
        is_valid=True,
        sanitized_query=query.strip(),
        warnings=warnings
    )


def explain_validation_failure(result: ValidationResult) -> str:
    """
    Generate a helpful error message for LLM to retry

    Args:
        result: Failed validation result

    Returns:
        Formatted error message
    """
    message = f"SQL Validation Failed: {result.error_message}\n\n"

    if result.warnings:
        message += "Warnings:\n"
        for warning in result.warnings:
            message += f"- {warning}\n"
        message += "\n"

    message += "Please revise your query following these guidelines:\n"
    message += "1. Only SELECT statements are allowed\n"
    message += "2. Use only tables and columns from the schema\n"
    message += "3. No multiple statements or dangerous commands\n\n"
    message += get_schema_documentation()

    return message
