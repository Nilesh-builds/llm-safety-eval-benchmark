import json

from src.run_metadata import build_manifest, sha256_file, write_manifest


def test_manifest_records_input_hash_and_can_be_written(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("benchmark", encoding="utf-8")
    destination = tmp_path / "run" / "manifest.json"

    manifest = build_manifest([source], [source], run_id="run-001")
    write_manifest(manifest, destination)

    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run-001"
    assert saved["inputs"][str(source)] == sha256_file(source)
