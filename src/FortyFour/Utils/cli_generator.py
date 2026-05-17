import json
import os
import hashlib
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
        config_module: Optional[str] = "config",
        cli_name: Optional[str] = None,
    ):
        self.openapi_url = openapi_url
        self.base_url = base_url
        self.excluded_tags = excluded_tags or ["users", "roles", "profiles", "memberships", "Profiles & Memberships"]
        self.commands_dir = commands_dir
        self.config_module = config_module
        self.cli_name = cli_name

    def fetch_openapi(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetches the OpenAPI JSON specification."""
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def clean_name(self, name: str) -> str:
        """Cleans a string to be used as a valid Python module or command name."""
        return name.lower().replace(" ", "_").replace("-", "_").replace("&", "and")

    def resolve_schema_ref(self, schema: Dict[str, Any], spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolves a local OpenAPI schema reference when present."""
        current = schema or {}
        while "$ref" in current and spec:
            ref_path = current["$ref"].split("/")
            resolved = spec
            for part in ref_path[1:]:
                resolved = resolved.get(part, {})
            current = resolved
        return current

    def unwrap_nullable_schema(self, schema: Dict[str, Any], spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Returns the non-null branch for nullable schemas."""
        current = self.resolve_schema_ref(schema, spec)
        if "anyOf" in current:
            for option in current["anyOf"]:
                option = self.resolve_schema_ref(option, spec)
                if option.get("type") != "null":
                    return option
        return current

    def map_schema_type(self, schema: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> str:
        """Maps OpenAPI schema types to a compact, agent-friendly set."""
        target_schema = self.unwrap_nullable_schema(schema, spec)
        schema_type = target_schema.get("type")
        if schema_type == "integer":
            return "int"
        if schema_type == "number":
            return "float"
        if schema_type == "boolean":
            return "bool"
        if schema_type == "array":
            return "list"
        if schema_type == "object":
            return "obj"
        if schema_type == "string" and (target_schema.get("format") == "binary" or "contentMediaType" in target_schema):
            return "file"
        return "str"

    def extract_example(self, source: Dict[str, Any]) -> Any:
        """Returns a single representative example from OpenAPI example fields."""
        if "example" in source:
            return source["example"]

        examples = source.get("examples")
        if isinstance(examples, list) and examples:
            return examples[0]
        if isinstance(examples, dict):
            first_example = next(iter(examples.values()), None)
            if isinstance(first_example, dict) and "value" in first_example:
                return first_example["value"]
            return first_example

        return None

    def get_cli_prefix(self) -> str:
        """Returns the command prefix used in generated references."""
        return self.cli_name or "python main.py"

    def format_cli_placeholder(self, name: str) -> str:
        """Formats a positional argument name for reference docs."""
        return name.upper().replace("-", "_")

    def format_cli_option_name(self, name: str) -> str:
        """Formats an option name the way Typer exposes it on the CLI."""
        return name.replace("_", "-")

    def format_cli_type_label(self, schema: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> str:
        """Formats a schema type label for command reference docs."""
        mapped = self.map_schema_type(schema, spec)
        labels = {
            "str": "TEXT",
            "int": "INTEGER",
            "float": "NUMBER",
            "bool": "BOOLEAN",
            "list": "JSON",
            "obj": "JSON",
            "file": "FILE",
        }
        return labels.get(mapped, "TEXT")

    def collect_schema_properties(self, schema: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Collects object properties, including simple allOf compositions."""
        target_schema = self.resolve_schema_ref(schema, spec)
        properties: Dict[str, Any] = {}
        for part in target_schema.get("allOf", []):
            properties.update(self.collect_schema_properties(part, spec))
        properties.update(target_schema.get("properties", {}))
        return properties

    def extract_schema_name(self, schema: Dict[str, Any]) -> Optional[str]:
        """Extracts a human-friendly schema name from a schema reference or title."""
        if "$ref" in schema:
            return schema["$ref"].split("/")[-1]
        if "title" in schema:
            return schema["title"]
        for part in schema.get("allOf", []):
            name = self.extract_schema_name(part)
            if name:
                return name
        return None

    def build_response_metadata(self, details: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Builds compact output metadata for a successful OpenAPI response."""
        responses = details.get("responses", {})
        if not responses:
            return {"kind": "none"}

        success_code = None
        for code in ("200", "201", "202", "203", "204"):
            if code in responses:
                success_code = code
                break
        if success_code is None:
            for code in sorted(responses.keys()):
                if str(code).startswith("2"):
                    success_code = code
                    break
        if success_code is None:
            return {"kind": "none"}

        response = self.resolve_schema_ref(responses[success_code], spec)
        content = response.get("content", {})
        if not content:
            return {"kind": "none"}

        content_type = "application/json" if "application/json" in content else next(iter(content), None)
        if not content_type:
            return {"kind": "none"}

        raw_schema = content[content_type].get("schema", {})
        if not raw_schema:
            return {"kind": "none", "content_type": content_type}

        schema = self.unwrap_nullable_schema(raw_schema, spec)
        if schema.get("type") == "array":
            item_schema = schema.get("items", {})
            fields = list(self.collect_schema_properties(item_schema, spec).keys())
            payload = {
                "kind": "collection",
                "content_type": content_type,
            }
            object_name = self.extract_schema_name(item_schema)
            if object_name:
                payload["object"] = object_name
            if fields:
                payload["fields"] = fields
            return payload

        if schema.get("type") == "object":
            properties = self.collect_schema_properties(raw_schema, spec)
            items_schema = properties.get("items")
            if items_schema:
                items_schema = self.unwrap_nullable_schema(items_schema, spec)
                if items_schema.get("type") == "array":
                    item_schema = items_schema.get("items", {})
                    fields = list(self.collect_schema_properties(item_schema, spec).keys())
                    payload = {
                        "kind": "collection",
                        "content_type": content_type,
                        "path": "items",
                    }
                    object_name = self.extract_schema_name(item_schema)
                    if object_name:
                        payload["object"] = object_name
                    if fields:
                        payload["fields"] = fields
                    return payload

            payload = {
                "kind": "object",
                "content_type": content_type,
            }
            object_name = self.extract_schema_name(raw_schema)
            if object_name:
                payload["object"] = object_name
            fields = list(properties.keys())
            if fields:
                payload["fields"] = fields
            return payload

        return {
            "kind": "raw",
            "content_type": content_type,
        }

    def build_param_metadata(self, parameter: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Builds compact metadata for one OpenAPI parameter."""
        schema = parameter.get("schema", {})
        target_schema = self.unwrap_nullable_schema(schema, spec)
        item = {
            "name": parameter["name"],
            "type": self.map_schema_type(target_schema, spec),
            "required": parameter.get("required", False),
        }
        if "default" in target_schema:
            item["default"] = target_schema["default"]
        elif "default" in schema:
            item["default"] = schema["default"]
        if "enum" in target_schema:
            item["enum"] = target_schema["enum"]
        example = self.extract_example(parameter)
        if example is None:
            example = self.extract_example(target_schema)
        if example is not None:
            item["example"] = example
        return item

    def build_body_metadata(self, details: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Builds compact metadata for an OpenAPI request body."""
        request_body = details.get("requestBody")
        if not request_body:
            return {"kind": "none"}

        request_body = self.resolve_schema_ref(request_body, spec)
        content = request_body.get("content", {})
        body_required = request_body.get("required", False)

        if "application/json" in content:
            schema = self.unwrap_nullable_schema(content["application/json"].get("schema", {}), spec)
            required_fields = set(schema.get("required", []))
            fields = []
            for field_name, field_schema in schema.get("properties", {}).items():
                field_schema = self.unwrap_nullable_schema(field_schema, spec)
                field_item = {
                    "name": field_name,
                    "type": self.map_schema_type(field_schema, spec),
                    "required": field_name in required_fields,
                }
                if "default" in field_schema:
                    field_item["default"] = field_schema["default"]
                if "enum" in field_schema:
                    field_item["enum"] = field_schema["enum"]
                example = self.extract_example(field_schema)
                if example is not None:
                    field_item["example"] = example
                fields.append(field_item)
            return {
                "kind": "json",
                "required": body_required,
                "fields": fields,
            }

        if "multipart/form-data" in content:
            schema = self.unwrap_nullable_schema(content["multipart/form-data"].get("schema", {}), spec)
            required_fields = set(schema.get("required", []))
            fields = []
            for field_name, field_schema in schema.get("properties", {}).items():
                field_schema = self.unwrap_nullable_schema(field_schema, spec)
                field_item = {
                    "name": field_name,
                    "type": self.map_schema_type(field_schema, spec),
                    "required": field_name in required_fields,
                }
                if "default" in field_schema:
                    field_item["default"] = field_schema["default"]
                if "enum" in field_schema:
                    field_item["enum"] = field_schema["enum"]
                example = self.extract_example(field_schema)
                if example is not None:
                    field_item["example"] = example
                fields.append(field_item)
            return {
                "kind": "multipart",
                "required": body_required,
                "fields": fields,
            }

        first_content_type = next(iter(content), None)
        if first_content_type:
            return {
                "kind": "raw",
                "required": body_required,
                "content_type": first_content_type,
            }

        return {"kind": "none"}

    def build_command_sidecar(self, module_name: str, command_name: str, path: str, method: str, details: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Builds compact manifest and schema payloads for one generated command."""
        params = details.get("parameters", [])
        path_params = [self.build_param_metadata(p, spec) for p in params if p.get("in") == "path"]
        query_params = [self.build_param_metadata(p, spec) for p in params if p.get("in") == "query"]
        body = self.build_body_metadata(details, spec)
        response = self.build_response_metadata(details, spec)
        schema_relpath = f"schemas/{module_name}__{command_name}.json"
        command_label = f"{module_name} {command_name}"

        return {
            "manifest": {
                "command": command_label,
                "module": module_name,
                "name": command_name,
                "method": method,
                "path": path,
                "path_params": [param["name"] for param in path_params],
                "query_params": [param["name"] for param in query_params],
                "body": body["kind"],
                "schema": schema_relpath,
            },
            "schema": {
                "command": command_label,
                "module": module_name,
                "name": command_name,
                "method": method,
                "path": path,
                "path_params": path_params,
                "query_params": query_params,
                "body": body,
                "response": response,
            },
            "schema_relpath": schema_relpath,
        }

    def build_command_reference(self, module_name: str, command_name: str, details: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Builds one markdown-friendly command reference entry."""
        usage_parts = [self.get_cli_prefix(), module_name, command_name]
        option_lines = []
        has_optional_options = False

        for parameter in details.get("parameters", []):
            description = parameter.get("description", "") or "No description available."
            if parameter.get("required", False):
                placeholder = self.format_cli_placeholder(parameter["name"])
                usage_parts.append(f"<{placeholder}>")
                option_lines.append(f"- `<{placeholder}>`: {description}")
            else:
                has_optional_options = True
                option_name = self.format_cli_option_name(parameter["name"])
                type_label = self.format_cli_type_label(parameter.get("schema", {}), spec)
                option_lines.append(f"- `--{option_name} {type_label}`: {description}")

        request_body = self.resolve_schema_ref(details.get("requestBody", {}), spec)
        if request_body:
            content = request_body.get("content", {})
            if "multipart/form-data" in content:
                usage_parts.append("<FILE_PATH>")
                option_lines.append("- `<FILE_PATH>`: Path to the local file to upload.")
            else:
                has_optional_options = True
                option_lines.append("- `--data JSON`: JSON string for the request body.")

        if has_optional_options:
            usage_parts.append("[OPTIONS]")

        return {
            "summary": details.get("summary", "") or details.get("description", "") or command_name.replace("-", " ").title(),
            "usage": " ".join(usage_parts),
            "options": option_lines,
        }

    def build_commands_reference_doc(self, command_groups: List[Dict[str, Any]]) -> str:
        """Builds a markdown reference for generated commands and flags."""
        prefix = self.get_cli_prefix()
        lines = [
            "# Generated CLI Reference Guide",
            "",
            "Use this guide to construct commands without trial-and-error.",
            "",
            "## Global Options",
            "- `--help`: Show help for any command or subcommand.",
            "",
            "## Command Discovery",
            f"- `{prefix} --help`: List all domains.",
            f"- `{prefix} <domain> --help`: List commands for a domain.",
            f"- `{prefix} <domain> --help 2>&1 | rg -i <keyword>`: Find commands or flags matching a keyword.",
            "",
        ]

        for group in command_groups:
            lines.append(f"## {group['tag']} (`{prefix} {group['module']}`)")
            if group.get("description"):
                lines.append(group["description"])
                lines.append("")
            for command in group["commands"]:
                lines.append(f"### {command['summary']}")
                lines.append(f"`{command['usage']}`")
                for option_line in command["options"]:
                    lines.append(option_line)
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def build_schemas_reference_doc(self, spec: Dict[str, Any]) -> str:
        """Builds a markdown field map from component schemas."""
        lines = [
            "# Generated Field Schemas",
            "",
            "## Minimal Field Map",
            "",
        ]

        schema_items = spec.get("components", {}).get("schemas", {})
        for schema_name in sorted(schema_items):
            properties = self.collect_schema_properties(schema_items[schema_name], spec)
            if not properties:
                continue
            field_list = ", ".join(properties.keys())
            lines.append(f"- **{schema_name}**: `{field_list}`")

        return "\n".join(lines).rstrip() + "\n"

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
            tag_hyphen = tag_l.replace("_", "-")
            if res.startswith(f"{tag_hyphen}-"):
                res = res[len(tag_hyphen)+1:]
            return res
        
        # Fallback to path/method
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        return f"{method}-{'-'.join(parts)}"

    def generate_command_code(self, tag: str, operations: List[Dict[str, Any]], base_url: str, spec: Optional[Dict[str, Any]] = None, tag_description: Optional[str] = None) -> str:
        """Generates the Python code for a Typer command module."""
        help_text = tag_description or f"CLI commands for managing {tag} resources and operations."
        code = [
            "import typer",
            "import httpx",
            "import os",
            "from typing import Optional, List",
            "from rich import print",
            "import json",
            "import sys",
            "",
            f"app = typer.Typer(help={repr(help_text)})"
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
            description = details.get("description", "") or details.get("summary", "")
            
            # Standardized Agentic Docstring
            lines = description.split("\n")
            summary = lines[0].strip() if lines else "No summary available."
            detailed_desc = "\n    ".join([l.strip() for l in lines[1:] if l.strip()]) if len(lines) > 1 else ""
            
            docstring = [f"    \"\"\"", f"    {summary}"]
            if detailed_desc:
                docstring.append("")
                docstring.append(f"    {detailed_desc}")
            
            cmd_name = self.get_command_name(details, path, method, tag)

            params = details.get("parameters", [])
            typer_params = []
            api_params = {"query": [], "path": []}
            param_docs = []
            
            for p in params:
                name = p["name"]
                param_in = p["in"]
                required = p.get("required", False)
                schema = p.get("schema", {})
                param_type = "str"

                target_schema = self.unwrap_nullable_schema(schema, spec)

                type_val = target_schema.get("type")
                if type_val == "integer":
                    param_type = "int"
                elif type_val == "boolean":
                    param_type = "bool"
                elif type_val == "array":
                    param_type = "List[str]"
                
                default = "None"
                param_help = p.get('description', '')
                if param_help:
                    param_docs.append(f"    - {name}: {param_help}")
                
                if not required:
                    if "default" in schema:
                        default = repr(schema["default"])
                    # Wrap array type as Optional when the parameter is not required
                    typed = f"Optional[{param_type}]" if param_type.startswith("List") else param_type
                    typer_params.append(f"{name}: {typed} = typer.Option({default}, help={repr(param_help)})")
                else:
                    typer_params.append(f"{name}: {param_type} = typer.Argument(..., help={repr(param_help)})")
                
                api_params[param_in].append(name)

            request_body = details.get("requestBody")
            is_multipart = False
            multipart_file_fields = []
            if request_body:
                content = request_body.get("content", {})
                if "multipart/form-data" in content:
                    is_multipart = True
                    multipart_schema = self.unwrap_nullable_schema(content["multipart/form-data"].get("schema", {}), spec)
                    for prop_name, prop_schema in multipart_schema.get("properties", {}).items():
                        if prop_schema.get("type") == "string" and ("contentMediaType" in prop_schema or prop_schema.get("format") == "binary"):
                            multipart_file_fields.append(prop_name)
                        else:
                            # Non-file fields go as data
                            pass
                if is_multipart:
                    if multipart_file_fields:
                        typer_params.append("file_path: str = typer.Argument(..., help='Path to the local file to upload')")
                        param_docs.append(f"    - file_path: Path to the local file to upload (sent as '{multipart_file_fields[0]}' field)")
                else:
                    typer_params.append("data: str = typer.Option(None, help='JSON string for request body')")
                    param_docs.append("    - data: JSON string for the request body containing the resource details.")

            if param_docs:
                docstring.append("")
                docstring.extend(param_docs)
            
            docstring.append("    \"\"\"")

            code.append(f"@app.command('{cmd_name}')")
            code.append(f"def {cmd_name.replace('-', '_')}({', '.join(typer_params)}):")
            code.extend(docstring)
            code.append(f"    params = {{}}")
            for p in api_params["query"]:
                code.append(f"    if {p} is not None: params['{p}'] = {p}")
            
            url_expr = f"f'{{BASE_URL}}{path}'"
            for p in api_params["path"]:
                url_expr = url_expr.replace(f"{{{p}}}", f"{{ {p} }}")
            
            code.append(f"    url = {url_expr}")
            
            fetch_call = []
            skip_common_response = False
            if request_body:
                if is_multipart:
                    # Multipart file upload - generates complete inline block
                    skip_common_response = True
                    code.append("    try:")
                    code.append(f"        with open(file_path, 'rb') as f:")
                    code.append(f"            files = {{'{multipart_file_fields[0]}': (os.path.basename(file_path), f, 'application/octet-stream')}}")
                    code.append(f"            response = httpx.{method}(url, params=params, files=files, timeout=TIMEOUT)")
                    code.append(f"    except FileNotFoundError:")
                    code.append(f"        print(f'[red]File not found:[/red] {{file_path}}')")                    
                    code.append(f"        return")
                    code.append(f"    except httpx.RequestError as e:")
                    code.append(f"        print(f'[red]Network error:[/red] {{e}}')")                    
                    code.append(f"        return")
                    code.append(f"    except OSError as e:")
                    code.append(f"        print(f'[red]Error reading file:[/red] {{e}}')")
                    code.append(f"        return")
                    code.append(f"    if response.status_code >= 400:")
                    code.append(f"        print(f'[red]Error {{response.status_code}}:[/red] {{response.text}}')")
                    code.append(f"    else:")
                    code.append(f"        try:")
                    code.append(f"            sys.stdout.write(json.dumps(response.json(), indent=4) + '\\n')")
                    code.append(f"        except Exception:")
                    code.append(f"            sys.stdout.write(str(response.text) + '\\n')")
                else:
                    fetch_call.append(f"httpx.{method}(url, params=params")
                    code.append("    json_data = None")
                    code.append("    if data:")
                    code.append("        try: json_data = json.loads(data)")
                    code.append("        except Exception as e: print(f'[red]Invalid JSON data:[/red] {e}'); return")
                    fetch_call.append(", json=json_data")
                    fetch_call.append(", timeout=TIMEOUT)")
            else:
                fetch_call.append(f"httpx.{method}(url, params=params")
                fetch_call.append(", timeout=TIMEOUT)")
            
            if not skip_common_response:
                code.append("    try:")
                code.append(f"        response = {''.join(fetch_call)}")
                code.append("    except httpx.RequestError as e:")
                code.append("        print(f'[red]Network error:[/red] {e}')")
                code.append("        return")
                code.append("    if response.status_code >= 400:")
                code.append("        print(f'[red]Error {response.status_code}:[/red] {response.text}')")
                code.append("    else:")
                code.append("        try:")
                code.append("            sys.stdout.write(json.dumps(response.json(), indent=4) + '\\n')")
                code.append("        except Exception:")
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
        if not os.path.isdir(target_dir):
            raise ValueError(f"output_dir does not exist or is not a directory: {target_dir}")

        commands_full_path = os.path.join(target_dir, self.commands_dir)
        schemas_full_path = os.path.join(target_dir, "schemas")
        manifest_path = os.path.join(target_dir, "manifest.json")
        references_full_path = os.path.join(target_dir, "references")
        commands_reference_path = os.path.join(references_full_path, "commands.md")
        schemas_reference_path = os.path.join(references_full_path, "schemas.md")
        
        if clean and os.path.exists(commands_full_path):
            print(f"Cleaning directory: {commands_full_path}")
            shutil.rmtree(commands_full_path)
        if clean and os.path.exists(schemas_full_path):
            print(f"Cleaning directory: {schemas_full_path}")
            shutil.rmtree(schemas_full_path)
        if clean and os.path.exists(manifest_path):
            print(f"Removing file: {manifest_path}")
            os.remove(manifest_path)
        if clean and os.path.exists(commands_reference_path):
            print(f"Removing file: {commands_reference_path}")
            os.remove(commands_reference_path)
        if clean and os.path.exists(schemas_reference_path):
            print(f"Removing file: {schemas_reference_path}")
            os.remove(schemas_reference_path)
            
        print(f"Fetching OpenAPI spec from {active_openapi}...")
        spec = self.fetch_openapi(active_openapi)
        
        os.makedirs(commands_full_path, exist_ok=True)
        os.makedirs(schemas_full_path, exist_ok=True)
        os.makedirs(references_full_path, exist_ok=True)
        
        # Ensure the commands directory is a package
        with open(os.path.join(commands_full_path, "__init__.py"), "w") as f:
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
                    
        # Extract tag descriptions if available
        tag_metadata = {t["name"]: t.get("description") for t in spec.get("tags", []) if "name" in t}

        generated_modules = []
        manifest_entries = []
        command_reference_groups = []
        for tag, ops in tags_ops.items():
            module_name = self.clean_name(tag)
            tag_description = tag_metadata.get(tag)
            print(f"Generating commands for {tag} -> {module_name}.py")
            code = self.generate_command_code(tag, ops, base_url=active_base, spec=spec, tag_description=tag_description)
            module_path = os.path.join(commands_full_path, f"{module_name}.py")
            try:
                with open(module_path, "w", encoding="utf-8") as f:
                    f.write(code)
            except OSError as e:
                print(f"[red]Failed to write {module_path}:[/red] {e}")
                continue
            generated_modules.append((tag, module_name))
            command_references = []
            for op in ops:
                command_name = self.get_command_name(op["details"], op["path"], op["method"], tag)
                command_references.append(self.build_command_reference(module_name, command_name, op["details"], spec))
                sidecar = self.build_command_sidecar(
                    module_name=module_name,
                    command_name=command_name,
                    path=op["path"],
                    method=op["method"],
                    details=op["details"],
                    spec=spec,
                )
                schema_path = os.path.join(target_dir, sidecar["schema_relpath"])
                try:
                    with open(schema_path, "w", encoding="utf-8") as f:
                        json.dump(sidecar["schema"], f, indent=2)
                        f.write("\n")
                except OSError as e:
                    print(f"[red]Failed to write {schema_path}:[/red] {e}")
                    continue
                manifest_entries.append(sidecar["manifest"])
            command_reference_groups.append({
                "tag": tag,
                "module": module_name,
                "description": tag_description,
                "commands": command_references,
            })

        try:
            manifest_payload = {"version": 1, "commands": manifest_entries}
            manifest_payload["hash"] = hashlib.sha256(
                json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_payload, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"[red]Failed to write {manifest_path}:[/red] {e}")

        try:
            with open(commands_reference_path, "w", encoding="utf-8") as f:
                f.write(self.build_commands_reference_doc(command_reference_groups))
        except OSError as e:
            print(f"[red]Failed to write {commands_reference_path}:[/red] {e}")

        try:
            with open(schemas_reference_path, "w", encoding="utf-8") as f:
                f.write(self.build_schemas_reference_doc(spec))
        except OSError as e:
            print(f"[red]Failed to write {schemas_reference_path}:[/red] {e}")
            
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
        
        main_path = os.path.join(target_dir, "main.py")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write("\n".join(main_code))
        
        print(f"CLI Generation Complete! Target: {target_dir}")
