import os
import shutil
import pytest
import sys
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
