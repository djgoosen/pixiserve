import sys
import types
from types import SimpleNamespace

# Minimal celery stub so worker modules can import in test env.
if "celery" not in sys.modules:
    celery_mod = types.ModuleType("celery")

    class _TaskWrapper:
        def __init__(self, fn):
            self._fn = fn
            self.run = fn

        def __call__(self, *args, **kwargs):
            return self._fn(*args, **kwargs)

    def _shared_task(*_args, **_kwargs):
        def _decorator(fn):
            return _TaskWrapper(fn)

        return _decorator

    celery_mod.shared_task = _shared_task
    celery_mod.chain = lambda *steps: SimpleNamespace(apply_async=lambda: SimpleNamespace(id="noop"), steps=steps)
    celery_mod.group = lambda *steps: ("group", steps)
    celery_mod.chord = lambda *steps: ("chord", steps)
    class _FakeCelery:
        def __init__(self, *args, **kwargs):
            self.conf = SimpleNamespace(
                update=lambda **_kw: None,
                task_queues={},
            )

    celery_mod.Celery = _FakeCelery
    sys.modules["celery"] = celery_mod

if "PIL" not in sys.modules:
    pil_mod = types.ModuleType("PIL")
    image_mod = types.ModuleType("PIL.Image")
    image_mod.Image = object
    image_mod.Resampling = SimpleNamespace(LANCZOS=1)
    pil_mod.Image = image_mod
    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = image_mod

from app.workers.tasks import ml_pipeline


class _SigTask:
    def __init__(self, name: str):
        self.name = name

    def s(self, *args):
        return (self.name, args)


def test_process_asset_queues_image_pipeline(monkeypatch):
    captured = {}

    monkeypatch.setattr(ml_pipeline, "extract_exif", _SigTask("extract_exif"))
    monkeypatch.setattr(ml_pipeline, "generate_thumbnails", _SigTask("generate_thumbnails"))
    monkeypatch.setattr(ml_pipeline, "process_extraction_results", _SigTask("process_extraction_results"))
    monkeypatch.setattr(ml_pipeline, "update_asset_metadata", _SigTask("update_asset_metadata"))

    def _group(*steps):
        captured["group"] = steps
        return ("group", steps)

    def _chain(*steps):
        captured["chain"] = steps

        class _Workflow:
            def apply_async(self):
                return SimpleNamespace(id="wf-123")

        return _Workflow()

    monkeypatch.setattr(ml_pipeline, "group", _group)
    monkeypatch.setattr(ml_pipeline, "chain", _chain)

    result = ml_pipeline.process_asset.run(
        None,
        "asset-1",
        "/tmp/img.jpg",
        "image",
        "owner-1",
    )

    assert result["task_ids"]["pipeline"] == "wf-123"
    assert "group" in captured
    assert captured["group"][0][0] == "extract_exif"
    assert captured["group"][1][0] == "generate_thumbnails"
    assert captured["chain"][-1][0] == "update_asset_metadata"


def test_apply_processing_results_to_asset_updates_preview_and_is_idempotent():
    asset = SimpleNamespace(
        captured_at=None,
        latitude=None,
        longitude=None,
        width=None,
        height=None,
        duration_seconds=None,
        exif_data=None,
        thumb_path=None,
        preview_path=None,
    )
    processing_results = {
        "exif": {},
        "thumbnails": {
            "thumb": "thumbs/a_thumb.webp",
            "preview": "thumbs/a_preview.webp",
        },
        "original_size": (1200, 800),
    }

    ml_pipeline.apply_processing_results_to_asset(asset, processing_results)
    first_thumb = asset.thumb_path
    first_preview = asset.preview_path
    first_size = (asset.width, asset.height)

    ml_pipeline.apply_processing_results_to_asset(asset, processing_results)

    assert first_thumb == "thumbs/a_thumb.webp"
    assert first_preview == "thumbs/a_preview.webp"
    assert first_size == (1200, 800)
    assert asset.thumb_path == first_thumb
    assert asset.preview_path == first_preview
    assert (asset.width, asset.height) == first_size
