import os
import shutil
import pytest
import sys
import json
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from FortyFour.Utils import OpenAPICLIGenerator

@pytest.fixture
def generator():
    return OpenAPICLIGenerator(
        openapi_url="http://mock/openapi.json",
        config_module="my_config"
    )

def test_clean_name(generator):
    assert generator.clean_name("Profiles & Memberships") == "profiles_and_memberships"
    assert generator.clean_name("User-Data") == "user_data"

def test_get_command_name_crud(generator):
    # Test CRUD detection
    op = {"operationId": "get_all_companies"}
    assert generator.get_command_name(op, "/companies", "get", "Companies") == "list"
    
    op = {"operationId": "create_company"}
    assert generator.get_command_name(op, "/companies", "post", "Companies") == "create"

def test_generate_command_code_with_config(generator):
    # Check that config import block is present and hardcoded defaults are absent
    ops = [{
        "path": "/test", 
        "method": "get", 
        "details": {"operationId": "test", "description": "desc"}
    }]
    code = generator.generate_command_code("Test", ops, base_url="http://api")
    
    assert "from my_config import BASE_URL, TIMEOUT" in code
    assert "BASE_URL = 'http://api'" not in code
    assert "TIMEOUT = 30" not in code

@patch("httpx.get")
def test_run_creates_files(mock_get, generator, tmp_path):
    # Minimal OpenAPI spec simulation
    mock_spec = {
        "paths": {
            "/ping": {
                "get": {
                    "tags": ["Health"],
                    "operationId": "check_health",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }
    mock_get.return_value.json.return_value = mock_spec
    mock_get.return_value.raise_for_status = MagicMock()

    # Execution in temporary directory
    generator.run(output_dir=str(tmp_path))

    # Verify created files/folders
    assert os.path.exists(tmp_path / "main.py")
    assert os.path.exists(tmp_path / "commands" / "__init__.py")
    assert os.path.exists(tmp_path / "commands" / "health.py")
    
    # Verify main.py content
    main_content = (tmp_path / "main.py").read_text()
    assert "from commands import health" in main_content
    assert "app.add_typer(health.app, name='health')" in main_content
    assert "sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))" in main_content


@patch("httpx.get")
def test_run_creates_agent_sidecars(mock_get, generator, tmp_path):
    mock_spec = {
        "paths": {
            "/companies/{company_id}": {
                "get": {
                    "tags": ["Companies"],
                    "operationId": "get_company_by_id",
                    "summary": "Get company",
                    "parameters": [
                        {
                            "name": "company_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        },
                        {
                            "name": "include_contacts",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "boolean",
                                "default": False,
                                "example": True
                            }
                        }
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/companies": {
                "post": {
                    "tags": ["Companies"],
                    "operationId": "create_company",
                    "summary": "Create company",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "example": "Acme Corp"
                                        },
                                        "website": {
                                            "type": "string",
                                            "examples": ["https://acme.test"]
                                        },
                                        "status": {
                                            "type": "string",
                                            "enum": ["active", "inactive"],
                                            "example": "active"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}}
                }
            }
        }
    }
    mock_get.return_value.json.return_value = mock_spec
    mock_get.return_value.raise_for_status = MagicMock()

    generator.run(output_dir=str(tmp_path))

    manifest_path = tmp_path / "manifest.json"
    schema_dir = tmp_path / "schemas"
    get_schema_path = schema_dir / "companies__get.json"
    create_schema_path = schema_dir / "companies__create.json"

    assert manifest_path.exists()
    assert schema_dir.exists()
    assert get_schema_path.exists()
    assert create_schema_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["version"] == 1
    assert len(manifest["hash"]) == 64
    assert manifest["commands"] == [
        {
            "command": "companies get",
            "module": "companies",
            "name": "get",
            "method": "get",
            "path": "/companies/{company_id}",
            "path_params": ["company_id"],
            "query_params": ["include_contacts"],
            "body": "none",
            "schema": "schemas/companies__get.json"
        },
        {
            "command": "companies create",
            "module": "companies",
            "name": "create",
            "method": "post",
            "path": "/companies",
            "path_params": [],
            "query_params": [],
            "body": "json",
            "schema": "schemas/companies__create.json"
        }
    ]

    get_schema = json.loads(get_schema_path.read_text())
    assert get_schema == {
        "command": "companies get",
        "module": "companies",
        "name": "get",
        "method": "get",
        "path": "/companies/{company_id}",
        "path_params": [
            {"name": "company_id", "type": "int", "required": True}
        ],
        "query_params": [
            {
                "name": "include_contacts",
                "type": "bool",
                "required": False,
                "default": False,
                "example": True
            }
        ],
        "body": {"kind": "none"},
        "response": {"kind": "none"}
    }

    create_schema = json.loads(create_schema_path.read_text())
    assert create_schema == {
        "command": "companies create",
        "module": "companies",
        "name": "create",
        "method": "post",
        "path": "/companies",
        "path_params": [],
        "query_params": [],
        "body": {
            "kind": "json",
            "required": True,
            "fields": [
                {
                    "name": "name",
                    "type": "str",
                    "required": True,
                    "example": "Acme Corp"
                },
                {
                    "name": "website",
                    "type": "str",
                    "required": False,
                    "example": "https://acme.test"
                },
                {
                    "name": "status",
                    "type": "str",
                    "required": False,
                    "enum": ["active", "inactive"],
                    "example": "active"
                }
            ]
        },
        "response": {"kind": "none"}
    }


@patch("httpx.get")
def test_run_creates_skill_reference_docs(mock_get, tmp_path):
    generator = OpenAPICLIGenerator(
        openapi_url="http://mock/openapi.json",
        config_module="my_config",
        cli_name="cos"
    )
    mock_spec = {
        "paths": {
            "/companies": {
                "get": {
                    "tags": ["Companies"],
                    "operationId": "get_all_companies",
                    "summary": "List companies",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "description": "Fuzzy search across company records.",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "size",
                            "in": "query",
                            "required": False,
                            "description": "Number of results.",
                            "schema": {"type": "integer", "default": 20}
                        }
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/companies/{company_id}": {
                "get": {
                    "tags": ["Companies"],
                    "operationId": "get_company_by_id",
                    "summary": "Get company",
                    "parameters": [
                        {
                            "name": "company_id",
                            "in": "path",
                            "required": True,
                            "description": "The company identifier.",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        },
        "components": {
            "schemas": {
                "Company": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string"}
                    }
                },
                "JournalLine": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"},
                        "debit": {"type": "number"},
                        "credit": {"type": "number"},
                        "description": {"type": "string"}
                    }
                }
            }
        }
    }
    mock_get.return_value.json.return_value = mock_spec
    mock_get.return_value.raise_for_status = MagicMock()

    generator.run(output_dir=str(tmp_path))

    commands_reference = tmp_path / "references" / "commands.md"
    schemas_reference = tmp_path / "references" / "schemas.md"

    assert commands_reference.exists()
    assert schemas_reference.exists()

    commands_content = commands_reference.read_text()
    assert "## Companies (`cos companies`)" in commands_content
    assert "`cos companies list [OPTIONS]`" in commands_content
    assert "- `--q TEXT`: Fuzzy search across company records." in commands_content
    assert "- `--size INTEGER`: Number of results." in commands_content
    assert "`cos companies get <COMPANY_ID>`" in commands_content

    schemas_content = schemas_reference.read_text()
    assert "- **Company**: `id, name, email, created_at`" in schemas_content
    assert "- **JournalLine**: `account_id, debit, credit, description`" in schemas_content


@patch("httpx.get")
def test_run_includes_response_metadata_in_command_schema(mock_get, generator, tmp_path):
    mock_spec = {
        "paths": {
            "/companies": {
                "get": {
                    "tags": ["Companies"],
                    "operationId": "get_all_companies",
                    "summary": "List companies",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Company"}
                                            },
                                            "total": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/companies/{company_id}": {
                "get": {
                    "tags": ["Companies"],
                    "operationId": "get_company_by_id",
                    "summary": "Get company",
                    "parameters": [
                        {
                            "name": "company_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Company"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Company": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string"}
                    }
                }
            }
        }
    }
    mock_get.return_value.json.return_value = mock_spec
    mock_get.return_value.raise_for_status = MagicMock()

    generator.run(output_dir=str(tmp_path))

    list_schema = json.loads((tmp_path / "schemas" / "companies__list.json").read_text())
    get_schema = json.loads((tmp_path / "schemas" / "companies__get.json").read_text())

    assert list_schema["response"] == {
        "kind": "collection",
        "content_type": "application/json",
        "path": "items",
        "object": "Company",
        "fields": ["id", "name", "email", "created_at"]
    }
    assert get_schema["response"] == {
        "kind": "object",
        "content_type": "application/json",
        "object": "Company",
        "fields": ["id", "name", "email", "created_at"]
    }
