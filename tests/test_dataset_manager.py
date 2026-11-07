from pathlib import Path
from src import dataset_manager


def test_download_selects_legislation_and_regulations_by_default(tmp_path, monkeypatch):
    legal = tmp_path / "open"; constitution = tmp_path / "constitution"
    db = tmp_path / "data" / "index.sqlite3"
    monkeypatch.setattr(dataset_manager, "OPEN_INDIA_LAW_DIR", legal)
    monkeypatch.setattr(dataset_manager, "CONSTITUTION_DIR", constitution)
    monkeypatch.setattr(dataset_manager, "DATABASE_PATH", db)
    calls = {}
    def fake_snapshot(**kwargs):
        calls["snapshot"] = kwargs
        legal.mkdir(parents=True, exist_ok=True)
        return str(legal)
    def fake_hf(**kwargs):
        calls.setdefault("constitution", []).append(kwargs["filename"])
        constitution.mkdir(parents=True, exist_ok=True)
        p = constitution / kwargs["filename"]
        p.write_text("{}", encoding="utf-8")
        return str(p)
    monkeypatch.setattr(dataset_manager, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(dataset_manager, "hf_hub_download", fake_hf)
    manifest = dataset_manager.download_datasets()
    assert calls["snapshot"]["allow_patterns"] == ["in_*_legislation.parquet", "in_*_regulations.parquet"]
    assert "in_*_judgments.parquet" not in calls["snapshot"]["allow_patterns"]
    assert set(calls["constitution"]) == set(dataset_manager.CONSTITUTION_FILES)
    assert manifest["judgments_included"] is False
    assert (tmp_path / "data" / "download_manifest.json").exists()


def test_judgments_are_only_included_when_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_manager, "OPEN_INDIA_LAW_DIR", tmp_path / "open")
    monkeypatch.setattr(dataset_manager, "CONSTITUTION_DIR", tmp_path / "constitution")
    monkeypatch.setattr(dataset_manager, "DATABASE_PATH", tmp_path / "data" / "index.sqlite3")
    calls = {}
    monkeypatch.setattr(dataset_manager, "snapshot_download", lambda **kwargs: calls.setdefault("patterns", kwargs["allow_patterns"]) or str(tmp_path))
    def fake_hf(**kwargs):
        p=tmp_path/"constitution"/kwargs["filename"]; p.parent.mkdir(exist_ok=True); p.write_text("{}")
        return str(p)
    monkeypatch.setattr(dataset_manager, "hf_hub_download", fake_hf)
    dataset_manager.download_datasets(include_judgments=True)
    assert "in_*_judgments.parquet" in calls["patterns"]
