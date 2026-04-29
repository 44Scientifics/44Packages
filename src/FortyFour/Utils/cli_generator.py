import json
import os
import httpx
import shutil
from typing import Dict, List, Any, Optional

class OpenAPICLIGenerator:
    """
    A reusable utility to generate Typer-based CLI command modules from an OpenAPI specification.
    """
    
    def __init__(
        self, 
        openapi_url: Optional[str] = None,
        base_url: Optional[str] = None,
        excluded_tags: Optional[List[str]] = None,
        commands_dir: str = "commands",
        config_module: Optional[str] = "config"
    ):
        self.openapi_url = openapi_url
        self.base_url = base_url
        self.excluded_tags = excluded_tags or ["users", "roles", "profiles", "memberships", "Profiles & Memberships"]
        self.commands_dir = commands_dir
        self.config_module = config_module

    def fetch_openapi(self, url: str) -> Dict[str, Any]:
        """Fetches the OpenAPI JSON specification."""
        response = httpx.get(url)
        response.raise_for_status()
        return response.json()

    def clean_name(self, name: str) -> str:
        """Cleans a string to be used as a valid Python module or command name."""
        return name.lower().replace(" ", "_").replace("-", "_").replace("&", "and")

    def get_command_name(self, operation: Dict[str, Any], path: str, method: str, tag: str) -> str:
        """Maps an OpenAPI operation to an intuitive CLI command name (list, get, create, etc.)."""
        op_id = operation.get("operationId", "")
        tag_l = tag.lower().replace(" ", "_")
        
        # Precise CRUD mappings with singular/plural support
        resource = tag_l.rstrip('s')
        if tag_l.endswith('ies'):
            resource = tag_l[:-3] + 'y'
        
        if op_id == f"get_all_{tag_l}": return "list"
        if op_id in [f"get_{tag_l}_by_id", f"get_{resource}_by_id"]: return "get"
        if op_id in [f"create_{tag_l}", f"create_{resource}"]: return "create"
        if op_id in [f"update_{tag_l}", f"update_{resource}"]: return "update"
        if op_id in [f"delete_{tag_l}", f"delete_{resource}"]: return "delete"

        # Fallback to general patterns if no exact match (but avoid collisions with CRUD)
        if op_id:
            res = op_id.replace("_", "-")
            # Strip redundant tag prefix if it starts with it
            if res.startswith(f"{tag_l}-"):
                res = res[len(tag_l)+1:]
            return res
        
        # Fallback to path/method
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        return f"{method}-{'-'.join(parts)}"

    def generate_command_code(self, tag: str, operations: List[Dict[str, Any]], base_url: str) -> str:
        """Generates the Python code for a Typer command module."""
        code = [
            "import typer",
            "import httpx",
            "from typing import Optional, List",
            "from rich import print",
            "import json",
            "import sys",
            "",
            f"app = typer.Typer(help='Manage CRUD Operations for {tag}')"
        ]
        if self.config_module:
            code.append(f"from {self.config_module} import BASE_URL, TIMEOUT")
        else:
            code.append(f"BASE_URL = '{base_url}'")
            code.append("TIMEOUT = 30")
        code.append("")

        for op in operations:
            path = op["path"]
            method = op["method"]
            details = op["details"]
            description = details.get("description", "")
            first_line_desc = description.split("\n")[0].strip()
            
            cmd_name = self.get_command_name(details, path, method, tag)

            params = details.get("parameters", [])
            typer_params = []
            api_params = {"query": [], "path": []}
            
            for p in params:
                name = p["name"]
                param_in = p["in"]
                required = p.get("required", False)
                schema = p.get("schema", {})
                param_type = "str"
                
                target_schema = schema
                if "anyOf" in schema:
                    for s in schema["anyOf"]:
                        if s.get("type") != "null":
                            target_schema = s
                            break
                
                type_val = target_schema.get("type")
                if type_val == "integer":
                    param_type = "int"
                elif type_val == "boolean":
                    param_type = "bool"
                elif type_val == "array":
                    param_type = "List[str]"
                
                default = "None"
                help_text = p.get('description', '')
                if not required:
                    if "default" in schema:
                        default = repr(schema["default"])
                    typer_params.append(f"{name}: {param_type} = typer.Option({default}, help={repr(help_text)})")
                else:
                    typer_params.append(f"{name}: {param_type} = typer.Argument(..., help={repr(help_text)})")
                
                api_params[param_in].append(name)

            request_body = details.get("requestBody")
            if request_body:
                typer_params.append("data: str = typer.Option(None, help='JSON string for request body')")

            code.append(f"@app.command('{cmd_name}')")
            code.append(f"def {cmd_name.replace('-', '_')}({', '.join(typer_params)}):")
            code.append(f"    \"\"\"{first_line_desc}\"\"\"")
            code.append(f"    params = {{}}")
            for p in api_params["query"]:
                code.append(f"    if {p} is not None: params['{p}'] = {p}")
            
            url_expr = f"f'{{BASE_URL}}{path}'"
            for p in api_params["path"]:
                url_expr = url_expr.replace(f"{{{p}}}", f"{{ {p} }}")
            
            code.append(f"    url = {url_expr}")
            
            fetch_call = [f"httpx.{method}(url, params=params"]
            if request_body:
                code.append("    json_data = None")
                code.append("    if data:")
                code.append("        try: json_data = json.loads(data)")
                code.append("        except Exception as e: print(f'[red]Invalid JSON data:[/red] {e}'); return")
                fetch_call.append(", json=json_data")
            fetch_call.append(", timeout=TIMEOUT)")
            
            code.append(f"    response = {''.join(fetch_call)}")
            code.append("    if response.status_code >= 400:")
            code.append("        print(f'[red]Error {response.status_code}:[/red] {response.text}')")
            code.append("    else:")
            code.append("        try:")
            code.append("            sys.stdout.write(json.dumps(response.json(), indent=4) + '\\n')")
            code.append("        except:")
            code.append("            sys.stdout.write(str(response.text) + '\\n')")
            code.append("")
            
        return "\n".join(code)

    def run(self, openapi_url: Optional[str] = None, base_url: Optional[str] = None, output_dir: Optional[str] = None, clean: bool = True):
        """Executes the generation process."""
        active_openapi = openapi_url or self.openapi_url
        active_base = base_url or self.base_url
        
        if not active_openapi:
            raise ValueError("openapi_url must be provided either in __init__ or run()")
        
        # If no base_url, try to infer it from openapi_url (strip the last part)
        if not active_base:
            active_base = active_openapi.rsplit('/', 1)[0]
            print(f"Inferred base_url: {active_base}")

        target_dir = output_dir or os.getcwd()
        commands_full_path = os.path.join(target_dir, self.commands_dir)
        
        if clean and os.path.exists(commands_full_path):
            print(f"Cleaning directory: {commands_full_path}")
            shutil.rmtree(commands_full_path)
            
        print(f"Fetching OpenAPI spec from {active_openapi}...")
        spec = self.fetch_openapi(active_openapi)
        
        if not os.path.exists(commands_full_path):
            os.makedirs(commands_full_path)
        
        # Ensure the commands directory is a package
        init_path = os.path.join(commands_full_path, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("")
            
        tags_ops = {}
        
        for path, path_item in spec.get("paths", {}).items():
            for method, op in path_item.items():
                if method not in ["get", "post", "put", "patch", "delete"]:
                    continue
                
                tags = op.get("tags", ["default"])
                for tag in tags:
                    if tag in self.excluded_tags or tag.lower() in [t.lower() for t in self.excluded_tags]:
                        continue
                    
                    if tag not in tags_ops:
                        tags_ops[tag] = []
                    
                    tags_ops[tag].append({
                        "path": path,
                        "method": method,
                        "details": op
                    })
                    
        generated_modules = []
        for tag, ops in tags_ops.items():
            module_name = self.clean_name(tag)
            print(f"Generating commands for {tag} -> {module_name}.py")
            code = self.generate_command_code(tag, ops, base_url=active_base)
            with open(os.path.join(commands_full_path, f"{module_name}.py"), "w") as f:
                f.write(code)
            generated_modules.append((tag, module_name))
            
        # Update main.py in the target directory
        print(f"Updating main.py in {target_dir}...")
        main_code = [
            "import typer",
            "import importlib",
            "import os",
            "import sys",
            "",
            "# Ensure the root directory is in the path so config can be imported from submodules",
            "sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))",
            "",
            "app = typer.Typer(help='CLI generated from OpenAPI')",
            ""
        ]
        
        for tag, module_name in generated_modules:
            main_code.append(f"from {self.commands_dir} import {module_name}")
            main_code.append(f"app.add_typer({module_name}.app, name='{module_name}')")
            main_code.append("")
            
        main_code.append("if __name__ == '__main__':")
        main_code.append("    app()")
        
        with open(os.path.join(target_dir, "main.py"), "w") as f:
            f.write("\n".join(main_code))
        
        print(f"CLI Generation Complete! Target: {target_dir}")
