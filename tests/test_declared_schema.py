from pathlib import Path

import yaml

from netdiag.cli import main, validate_declared

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "declared.template.yaml"


def write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "declared.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def template() -> dict:
    return yaml.safe_load(TEMPLATE.read_text())


def test_template_is_valid():
    assert validate_declared(TEMPLATE) == []


def test_missing_prod_differences_is_rejected(tmp_path):
    data = template()
    del data["prod_differences"]
    assert validate_declared(write(tmp_path, data))


def test_full_dependency_requires_port_protocol_tls_auth(tmp_path):
    data = template()
    del data["dependencies"][0]["port"]
    assert validate_declared(write(tmp_path, data))


def test_data_store_requires_service(tmp_path):
    data = template()
    del data["dependencies"][0]["service"]
    assert validate_declared(write(tmp_path, data))


def test_purpose_only_entry_cannot_carry_other_fields(tmp_path):
    data = template()
    data["dependencies"].append({"name": "queue", "purpose": "Sends events", "port": 443})
    assert validate_declared(write(tmp_path, data))


def test_ip_address_endpoint_is_rejected(tmp_path):
    data = template()
    data["dependencies"][1]["endpoint"] = "10.1.2.3"
    assert validate_declared(write(tmp_path, data))


def test_unknown_auth_value_is_rejected(tmp_path):
    data = template()
    data["dependencies"][1]["auth"] = "basic"
    assert validate_declared(write(tmp_path, data))


def test_cli_validate_exit_codes(tmp_path):
    assert main(["validate", str(TEMPLATE)]) == 0
    data = template()
    del data["owner_team"]
    assert main(["validate", str(write(tmp_path, data))]) == 1
