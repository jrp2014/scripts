"""Tests for model discovery and filtering."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

# HF cache environment is configured by conftest.py (early env setup + autouse fixture).
import pytest
from huggingface_hub.errors import CacheNotFound

import check_models
from tools import safe_io

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class _FakeCacheFile:
    file_path: str


@dataclass(frozen=True)
class _FakeCacheRef:
    files: tuple[_FakeCacheFile, ...]


@dataclass(frozen=True)
class _FakeCacheRepo:
    repo_id: str
    repo_type: str
    refs: dict[str, _FakeCacheRef]


@dataclass(frozen=True)
class _FakeCacheInfo:
    repos: tuple[_FakeCacheRepo, ...]


@dataclass(frozen=True)
class _FakeIntegrityRepo:
    repo_id: str
    size_on_disk: int = 2_000_000
    nb_files: int = 3


@dataclass(frozen=True)
class _FakeIntegrityCacheInfo:
    repos: tuple[_FakeIntegrityRepo, ...]
    warnings: tuple[Exception, ...] = ()


def _fake_cache_repo(
    repo_id: str,
    files: tuple[str, ...],
    *,
    repo_type: str = "model",
    include_main: bool = True,
) -> _FakeCacheRepo:
    refs = {"main": _FakeCacheRef(tuple(_FakeCacheFile(path) for path in files))}
    if not include_main:
        refs = {}
    return _FakeCacheRepo(repo_id=repo_id, repo_type=repo_type, refs=refs)


def test_get_cached_model_ids_returns_list() -> None:
    """Should return a list of model IDs from cache."""
    try:
        model_ids = check_models.get_cached_model_ids()
        assert isinstance(model_ids, list)
        # May be empty if no models cached
        for model_id in model_ids:
            assert isinstance(model_id, str)
    except CacheNotFound:
        pytest.skip("HuggingFace cache directory not found (expected in CI)")


def test_get_cached_model_ids_matches_mlx_vlm_server_cache_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Automatic cache discovery should match mlx-vlm's supported-model filter."""
    cache_info = _FakeCacheInfo(
        repos=(
            _fake_cache_repo(
                "org/supported-model",
                ("config.json", "tokenizer_config.json", "model.safetensors"),
            ),
            _fake_cache_repo(
                "org/supported-sharded-model",
                ("config.json", "tokenizer_config.json", "model.safetensors.index.json"),
            ),
            _fake_cache_repo("org/no-tokenizer", ("config.json", "model.safetensors")),
            _fake_cache_repo(
                "org/no-weights",
                ("config.json", "tokenizer_config.json", "pytorch_model.bin"),
            ),
            _fake_cache_repo(
                "org/no-main-ref",
                ("config.json", "tokenizer_config.json", "model.safetensors"),
                include_main=False,
            ),
            _fake_cache_repo(
                "org/dataset-cache",
                ("config.json", "tokenizer_config.json", "model.safetensors"),
                repo_type="dataset",
            ),
        )
    )
    monkeypatch.setattr(
        check_models,
        "_get_hf_cache_info_cached",
        lambda **_: cache_info,
    )

    assert check_models.get_cached_model_ids() == [
        "org/supported-model",
        "org/supported-sharded-model",
    ]


def test_cached_model_eligibility_reports_skip_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported cached repos should carry maintainer-readable skip reasons."""
    cache_info = _FakeCacheInfo(
        repos=(
            _fake_cache_repo("org/no-tokenizer", ("config.json", "model.safetensors")),
            _fake_cache_repo(
                "org/no-weights",
                ("config.json", "tokenizer_config.json", "pytorch_model.bin"),
            ),
            _fake_cache_repo(
                "org/no-main-ref",
                ("config.json", "tokenizer_config.json", "model.safetensors"),
                include_main=False,
            ),
        )
    )
    monkeypatch.setattr(
        check_models,
        "_get_hf_cache_info_cached",
        lambda **_: cache_info,
    )

    entries = {
        entry.repo_id: entry
        for entry in check_models.get_cached_model_eligibility()
        if not entry.supported
    }

    assert entries["org/no-tokenizer"].reasons == ("missing tokenizer_config.json",)
    assert entries["org/no-weights"].reasons == ("missing safetensors weights",)
    assert entries["org/no-main-ref"].reasons == ("missing main revision in cache",)


def test_auto_cache_discovery_logs_skipped_models(caplog: pytest.LogCaptureFixture) -> None:
    """Unspecified model runs should highlight cached models skipped by discovery."""
    eligibility = (
        check_models.CachedModelEligibility(
            repo_id="org/supported-model",
            supported=True,
            reasons=(),
        ),
        check_models.CachedModelEligibility(
            repo_id="org/no-tokenizer",
            supported=False,
            reasons=("missing tokenizer_config.json",),
        ),
    )

    with caplog.at_level(logging.INFO, logger=check_models.logger.name):
        selected = check_models._supported_cached_model_ids_with_skipped_logging(eligibility)

    assert selected == ["org/supported-model"]
    assert "Skipped 1 cached repo(s) that default discovery will not run" in caplog.text
    assert "org/no-tokenizer: cache layout: missing tokenizer_config.json" in caplog.text


def test_cache_integrity_uses_exact_repo_id_matching(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A similarly named cache entry must not be treated as the requested model."""
    cache_info = _FakeIntegrityCacheInfo(
        repos=(_FakeIntegrityRepo("org/model-extra"),),
    )
    monkeypatch.setattr(check_models, "_get_hf_cache_info_cached", lambda **_: cache_info)

    with caplog.at_level(logging.DEBUG, logger=check_models.logger.name):
        check_models._check_hf_cache_integrity("org/model")

    assert "Model org/model not found in HF cache" in caplog.text
    assert "HF Cache Info for org/model-extra" not in caplog.text


def test_cache_integrity_reports_matching_scan_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A corrupt repo omitted from repos should still produce an actionable warning."""
    cache_info = _FakeIntegrityCacheInfo(
        repos=(),
        warnings=(
            RuntimeError("Snapshots dir doesn't exist in cached repo: /cache/models--org--model"),
        ),
    )
    monkeypatch.setattr(check_models, "_get_hf_cache_info_cached", lambda **_: cache_info)

    with caplog.at_level(logging.WARNING, logger=check_models.logger.name):
        check_models._check_hf_cache_integrity("org/model")

    assert "Cache Warning: Hugging Face reported corruption for org/model" in caplog.text
    assert "Snapshots dir doesn't exist" in caplog.text


def test_validate_model_identifier_accepts_valid_huggingface_format() -> None:
    """Should accept standard HuggingFace model identifiers."""
    # Should not raise
    check_models.validate_model_identifier("mlx-community/Qwen2-VL-2B-Instruct-4bit")
    check_models.validate_model_identifier("microsoft/Phi-3-vision-128k-instruct")
    check_models.validate_model_identifier("apple/OpenELM-270M")


def test_validate_model_identifier_accepts_local_paths(tmp_path: Path) -> None:
    """Should accept valid local paths."""
    # Create a dummy model directory
    model_dir = tmp_path / "local_model"
    model_dir.mkdir()
    check_models.validate_model_identifier(str(model_dir))


def test_validate_model_identifier_rejects_empty_string() -> None:
    """Should reject empty model identifier."""
    with pytest.raises(ValueError, match="Model identifier cannot be empty"):
        check_models.validate_model_identifier("")


def test_validate_model_identifier_rejects_whitespace_only() -> None:
    """Should reject whitespace-only identifiers."""
    with pytest.raises(ValueError, match="Model identifier cannot be empty"):
        check_models.validate_model_identifier("   ")
    with pytest.raises(ValueError, match="Model identifier cannot be empty"):
        check_models.validate_model_identifier("\t\n")


def test_validate_kv_params_valid_combinations() -> None:
    """Should accept valid KV cache parameter combinations."""
    # Should not raise
    check_models.validate_kv_params(kv_bits=None, max_kv_size=None)
    check_models.validate_kv_params(kv_bits=4, max_kv_size=1024)
    check_models.validate_kv_params(kv_bits=8, max_kv_size=2048)
    check_models.validate_kv_params(kv_bits=3.5, max_kv_size=2048)


def test_validate_kv_params_rejects_invalid_bits() -> None:
    """Should reject invalid kv_bits values."""
    with pytest.raises(ValueError, match="kv_bits must be"):
        check_models.validate_kv_params(kv_bits=16, max_kv_size=1024)


def test_validate_kv_params_rejects_negative_size() -> None:
    """Should reject negative max_kv_size."""
    with pytest.raises(ValueError, match="max_kv_size must be > 0"):
        check_models.validate_kv_params(kv_bits=4, max_kv_size=-100)


def test_validate_kv_params_rejects_zero_size() -> None:
    """Should reject zero max_kv_size."""
    with pytest.raises(ValueError, match="max_kv_size must be > 0"):
        check_models.validate_kv_params(kv_bits=4, max_kv_size=0)


# ---------------------------------------------------------------------------
# Architecture pre-check (upstream --check-arch tier)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeSnapshotRef:
    snapshot_path: str


@dataclass(frozen=True)
class _FakeSnapshotRepo:
    repo_id: str
    repo_type: str
    refs: dict[str, _FakeSnapshotRef]


@pytest.fixture(name="_clear_arch_caches")
def _clear_arch_caches_fixture() -> Iterator[None]:
    """Isolate the memoized installed-package probes between tests."""
    _clear_arch_caches()
    yield
    _clear_arch_caches()


def _clear_arch_caches() -> None:
    """Clear every memoised upstream-source probe (tests may have patched some away)."""
    for name in (
        "_installed_mlx_vlm_model_types",
        "_mlx_vlm_model_remapping",
        "_mlx_vlm_drafter_model_types",
        "_mlx_vlm_image_generation_model_types",
    ):
        clear = getattr(getattr(check_models, name), "cache_clear", None)
        if clear is not None:
            clear()


def _fake_mlx_vlm_package(tmp_path: Path, model_types: tuple[str, ...], remapping: str) -> Path:
    package_dir = tmp_path / "mlx_vlm"
    for model_type in model_types:
        (package_dir / "models" / model_type).mkdir(parents=True)
    (package_dir / "models" / "__pycache__").mkdir(exist_ok=True)
    safe_io.write_text_no_follow(package_dir / "utils.py", remapping)
    return package_dir


@pytest.mark.usefixtures("_clear_arch_caches")
def test_installed_mlx_vlm_model_types_scans_package_dirs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Model-type discovery must scan package folders without importing mlx."""
    package_dir = _fake_mlx_vlm_package(
        tmp_path,
        ("qwen2_vl", "fastvlm"),
        "MODEL_REMAPPING = {'llava_qwen2': 'fastvlm'}\n",
    )
    fake_spec = SimpleNamespace(submodule_search_locations=[str(package_dir)])
    monkeypatch.setattr(check_models, "find_spec", lambda _name: fake_spec)

    assert check_models._installed_mlx_vlm_model_types() == frozenset({"qwen2_vl", "fastvlm"})
    assert check_models._mlx_vlm_model_remapping() == {"llava_qwen2": "fastvlm"}


@pytest.mark.usefixtures("_clear_arch_caches")
def test_drafter_and_image_generation_types_are_parsed_from_upstream_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drafter and image-producing families come from mlx-vlm's own source, unimported."""
    package_dir = _fake_mlx_vlm_package(tmp_path, ("qwen2_vl", "flux2", "bonsai"), "")
    drafters = package_dir / "speculative" / "drafters"
    (drafters / "gemma4_dspark").mkdir(parents=True)
    safe_io.write_text_no_follow(
        drafters / "__init__.py",
        'KNOWN_DRAFTER_KINDS = {"dflash", "mtp"}\n'
        'DRAFTER_KIND_BY_MODEL_TYPE = {"gemma4_dspark": "dflash", "qwen3_5_mtp": "mtp"}\n',
    )
    safe_io.write_text_no_follow(
        package_dir / "models" / "flux2" / "model.py",
        "from typing import ClassVar\n\n\nclass Model:\n"
        "    is_image_generation_model: ClassVar[bool] = True\n\n\n"
        "class EditModel(Model):\n    is_image_edit_model = True\n",
    )
    safe_io.write_text_no_follow(
        package_dir / "models" / "bonsai" / "model.py",
        'class Model:\n    model_type = "bonsai_image"\n    is_image_generation_model: ClassVar[bool] = True\n',
    )
    safe_io.write_text_no_follow(
        package_dir / "models" / "qwen2_vl" / "model.py",
        "class Model:\n    is_image_generation_model = False\n",
    )
    fake_spec = SimpleNamespace(submodule_search_locations=[str(package_dir)])
    monkeypatch.setattr(check_models, "find_spec", lambda _name: fake_spec)

    assert check_models._mlx_vlm_drafter_model_types() == frozenset(
        {"gemma4_dspark", "qwen3_5_mtp"}
    )
    assert check_models._mlx_vlm_image_generation_model_types() == frozenset(
        {"flux2", "bonsai", "bonsai_image"}
    )


@pytest.mark.usefixtures("_clear_arch_caches")
def test_installed_mlx_vlm_model_types_handles_missing_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing mlx_vlm installation must yield indeterminate, not a crash."""
    monkeypatch.setattr(check_models, "find_spec", lambda _name: None)

    assert check_models._installed_mlx_vlm_model_types() is None
    assert check_models._mlx_vlm_model_remapping() == {}


@pytest.mark.parametrize(
    ("model_type", "expected_resolved", "expected_supported"),
    [
        ("qwen2_vl", "qwen2_vl", True),
        ("llava_qwen2", "fastvlm", True),  # alias resolves via MODEL_REMAPPING
        ("totally_new_arch", "totally_new_arch", False),
    ],
)
def test_model_arch_precheck_resolves_aliases_against_installed_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_type: str,
    expected_resolved: str,
    expected_supported: bool,
) -> None:
    """The pre-check must mirror upstream --check-arch semantics."""
    snapshot = tmp_path / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text(json.dumps({"model_type": model_type}), encoding="utf-8")
    repo = _FakeSnapshotRepo(
        repo_id="org/model",
        repo_type="model",
        refs={"main": _FakeSnapshotRef(snapshot_path=str(snapshot))},
    )
    monkeypatch.setattr(
        check_models,
        "_installed_mlx_vlm_model_types",
        lambda: frozenset({"qwen2_vl", "fastvlm"}),
    )
    monkeypatch.setattr(
        check_models,
        "_mlx_vlm_model_remapping",
        lambda: {"llava_qwen2": "fastvlm"},
    )

    result = check_models._model_arch_precheck(repo)

    assert result == (model_type, expected_resolved, expected_supported)


def test_model_arch_precheck_is_indeterminate_without_config_or_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing config or missing installed mlx-vlm must never claim a verdict."""
    no_snapshot_repo = _FakeSnapshotRepo(repo_id="org/none", repo_type="model", refs={})
    assert check_models._model_arch_precheck(no_snapshot_repo) == (None, None, None)

    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    (snapshot / "config.json").write_text(json.dumps({"model_type": "qwen2_vl"}), "utf-8")
    repo = _FakeSnapshotRepo(
        repo_id="org/model",
        repo_type="model",
        refs={"main": _FakeSnapshotRef(snapshot_path=str(snapshot))},
    )
    monkeypatch.setattr(check_models, "_installed_mlx_vlm_model_types", lambda: None)
    monkeypatch.setattr(check_models, "_mlx_vlm_model_remapping", dict)

    assert check_models._model_arch_precheck(repo) == ("qwen2_vl", "qwen2_vl", None)


def test_arch_precheck_summary_renders_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    """The per-model fact renders yes/no with alias resolution, or omits itself."""
    monkeypatch.setattr(
        check_models,
        "_arch_precheck_for_model",
        lambda _model: ("llava_qwen2", "fastvlm", True),
    )
    assert (
        check_models._arch_precheck_summary("org/model")
        == "yes (model_type llava_qwen2 via fastvlm)"
    )

    monkeypatch.setattr(
        check_models,
        "_arch_precheck_for_model",
        lambda _model: ("new_arch", "new_arch", False),
    )
    assert check_models._arch_precheck_summary("org/model") == "no (model_type new_arch)"

    monkeypatch.setattr(
        check_models,
        "_arch_precheck_for_model",
        lambda _model: (None, None, None),
    )
    assert check_models._arch_precheck_summary("org/model") is None


# --- Capability-aware discovery (upstream alignment design §1-3) ---------------


def _capability_for(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config: dict[str, object] | None,
    model_index: dict[str, object] | None = None,
) -> check_models.ImageCapability:
    """Classify a fake repo whose config.json / model_index.json are supplied inline."""

    def _read(_repo: object, file_name: str) -> dict[str, object] | None:
        if file_name == "config.json":
            return config
        if file_name == "model_index.json":
            return model_index
        return None

    monkeypatch.setattr(check_models, "_read_cached_repo_json", _read)
    return check_models._classify_image_capability(object())


VLM_CONFIG: dict[str, object] = {
    "model_type": "qwen3_vl",
    "architectures": ["Qwen3VLForConditionalGeneration"],
    "vision_config": {"depth": 24},
    "image_token_id": 151655,
    "id2label": {"0": "LABEL_0"},  # present on real VLMs; must not read as reranker
}


class TestImageCapabilityClassifier:
    """Tri-state capability classification with explicit evidence."""

    def test_vlm_config_is_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A config with vision evidence is a positive image-to-text verdict."""
        cap = _capability_for(monkeypatch, config=VLM_CONFIG)

        assert cap.verdict == "yes"
        assert cap.purpose == "image_to_text"
        assert "image_token_id" in cap.evidence[0]
        assert cap.skip_reason is None

    def test_text_only_config_is_no(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A generative config with no modality evidence is text-only."""
        cap = _capability_for(
            monkeypatch,
            config={"model_type": "afm7", "architectures": ["Afm7ForCausalLM"]},
        )

        assert cap.verdict == "no"
        assert cap.purpose == "text_only"
        assert cap.skip_reason == (
            "model purpose: text-only generation "
            "(model_type=afm7; no vision_config/image token keys)"
        )

    @pytest.mark.parametrize(
        ("config", "model_index", "purpose"),
        [
            (
                {"model_type": "bert", "mlx_embeddings": {"kind": "embedding"}},
                None,
                "embedding",
            ),
            (
                {
                    "model_type": "xlm_roberta",
                    "architectures": ["XLMRobertaForSequenceClassification"],
                },
                None,
                "reranker",
            ),
            (
                {"model_type": "qwen3", "speculators_model_type": "eagle3"},
                None,
                "speculative_drafter",
            ),
            (
                {"model_type": "flux"},
                {"_class_name": "FluxPipeline"},
                "image_or_video_generation",
            ),
            (
                {
                    "model_type": "voice_gen",
                    "architectures": ["VoiceGenForConditionalGeneration"],
                    "audio_config": {"sample_rate": 16000},
                },
                None,
                "audio_or_other_generation",
            ),
        ],
    )
    def test_non_image_kinds_are_no_with_distinct_reasons(
        self,
        monkeypatch: pytest.MonkeyPatch,
        config: dict[str, object],
        model_index: dict[str, object] | None,
        purpose: str,
    ) -> None:
        """Each non-image model kind yields a distinct explicit skip reason."""
        cap = _capability_for(monkeypatch, config=config, model_index=model_index)

        assert cap.verdict == "no"
        assert cap.purpose == purpose
        assert cap.evidence
        assert cap.skip_reason is not None
        assert cap.skip_reason.startswith("model purpose: ")

    def test_null_vision_config_is_not_positive_evidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A null/empty image key carries no evidence; the verdict is not yes."""
        cap = _capability_for(
            monkeypatch,
            config={
                "model_type": "textish",
                "architectures": ["TextishForCausalLM"],
                "vision_config": None,
                "image_grid_pinpoints": [],
            },
        )

        assert cap.verdict != "yes"
        assert cap.purpose == "text_only"

    def test_null_key_beside_real_vision_keys_still_yes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FastVLM shape: image_grid_pinpoints null but genuine vision keys present."""
        cap = _capability_for(
            monkeypatch,
            config={
                "model_type": "llava_qwen2",
                "architectures": ["LlavaQwen2ForCausalLM"],
                "image_grid_pinpoints": None,
                "mm_vision_select_layer": -2,
                "vision_config": {"hidden_size": 1024},
            },
        )

        assert cap.verdict == "yes"

    def test_image_evidence_without_generative_arch_is_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Image keys but no text-generating architecture: run, but not confident."""
        cap = _capability_for(
            monkeypatch,
            config={
                "model_type": "mystery_vision",
                "architectures": ["MysteryVisionModel"],
                "vision_config": {"hidden_size": 768},
            },
        )

        assert cap.verdict == "unknown"
        assert any("no generative-text architecture" in e for e in cap.evidence)

    @pytest.mark.parametrize(
        "architecture",
        [
            "SegformerForSemanticSegmentation",
            "DetrForObjectDetection",
            "ViTForImageClassification",
            "CLIPModel",
        ],
    )
    def test_non_generative_image_architectures_are_no(
        self, monkeypatch: pytest.MonkeyPatch, architecture: str
    ) -> None:
        """Image-consuming but non-text-generating models are confidently excluded."""
        cap = _capability_for(
            monkeypatch,
            config={
                "model_type": "vision_thing",
                "architectures": [architecture],
                "vision_config": {"hidden_size": 768},
            },
        )

        assert cap.verdict == "no"
        assert cap.purpose == "image_understanding_non_generative"
        assert architecture in cap.evidence[0]

    def test_id2label_alone_does_not_mean_reranker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Real VLM configs carry id2label; only sequence-classifier signals count."""
        cap = _capability_for(
            monkeypatch,
            config={"model_type": "mystery", "id2label": {"0": "x"}, "num_labels": 1},
        )

        assert cap.purpose != "reranker"

    def test_unfamiliar_config_is_unknown_and_selected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Insufficient evidence yields unknown, which default discovery still runs."""
        cap = _capability_for(monkeypatch, config={"model_type": "brand_new_arch"})

        assert cap.verdict == "unknown"
        assert cap.skip_reason is None
        entry = check_models.CachedModelEligibility(
            repo_id="org/new", supported=True, capability=cap
        )
        assert entry.selected is True
        assert entry.skip_reasons == ()

    def test_missing_config_is_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No readable config cannot be classified and stays unknown."""
        cap = _capability_for(monkeypatch, config=None)

        assert cap.verdict == "unknown"
        assert cap.evidence == ("no readable config.json",)


class TestCapabilityAwareSelection:
    """Discovery skips only confident non-image repos and reports every skip."""

    def _entries(self) -> tuple[check_models.CachedModelEligibility, ...]:
        yes = check_models.ImageCapability(
            "yes", "image_to_text", ("image-input keys: vision_config",)
        )
        no = check_models.ImageCapability(
            "no", "text_only", ("model_type=afm7", "no vision_config/image token keys")
        )
        unknown = check_models.ImageCapability("unknown", "unknown", ("model_type=new",))
        return (
            check_models.CachedModelEligibility("org/vlm", supported=True, capability=yes),
            check_models.CachedModelEligibility("org/text-only", supported=True, capability=no),
            check_models.CachedModelEligibility("org/new-arch", supported=True, capability=unknown),
            check_models.CachedModelEligibility(
                "org/bad-layout",
                supported=False,
                reasons=("missing tokenizer_config.json",),
                capability=yes,
            ),
        )

    def test_selection_runs_yes_and_unknown_and_skips_no(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Default discovery runs yes+unknown, skips no, and names every skip."""
        with caplog.at_level(logging.WARNING):
            selected = check_models._supported_cached_model_ids_with_skipped_logging(
                self._entries()
            )

        assert selected == ["org/new-arch", "org/vlm"]
        text = caplog.text
        # Every skipped repo is named with a concrete reason.
        assert "org/text-only: model purpose: text-only generation" in text
        assert "org/bad-layout: cache layout: missing tokenizer_config.json" in text
        # Unknown is a warning on a selected model, not an exclusion.
        assert "unknown image capability" in text
        assert "org/new-arch" in text

    def test_combined_skip_reasons_layout_and_capability(self) -> None:
        """Layout and capability reasons are both reported, in that order."""
        entry = check_models.CachedModelEligibility(
            "org/both",
            supported=False,
            reasons=("missing config.json",),
            capability=check_models.ImageCapability(
                "no", "embedding", ("mlx_embeddings.kind=embedding",)
            ),
        )

        assert entry.selected is False
        assert entry.skip_reasons == (
            "cache layout: missing config.json",
            "model purpose: embedding model (mlx_embeddings.kind=embedding)",
        )

    def test_explicit_models_override_with_visible_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Explicit --models runs a non-image repo but keeps the classification visible."""
        monkeypatch.setattr(check_models, "get_cached_model_eligibility", self._entries)

        with caplog.at_level(logging.WARNING):
            check_models._warn_explicit_non_image_models(["org/text-only", "org/vlm"])

        assert "org/text-only classifies as non-image" in caplog.text
        assert "org/vlm classifies" not in caplog.text

    def test_explicit_models_with_incomplete_snapshots_are_warned_about(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Explicit --models bypasses the layout check, so the run says what it will fetch."""
        partial = check_models.CachedModelEligibility(
            "org/partial",
            supported=False,
            reasons=("missing tokenizer_config.json", "missing safetensors weights"),
        )
        entries = (*self._entries(), partial)
        monkeypatch.setattr(check_models, "get_cached_model_eligibility", lambda: entries)

        with caplog.at_level(logging.WARNING):
            warned = check_models._warn_explicit_incomplete_cache(
                ["org/partial", "org/vlm", "org/not-cached"]
            )

        assert warned == 1
        assert "org/partial: its cached main revision fails" in caplog.text
        assert "missing tokenizer_config.json; missing safetensors weights" in caplog.text
        assert "may need to download files for it" in caplog.text
        assert "hf download org/partial`" in caplog.text
        assert "org/vlm: its cached" not in caplog.text
        assert "org/not-cached" not in caplog.text

        # An explicit --revision may already be complete: the advice names it
        # and the warning promises nothing about what will be downloaded.
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            check_models._warn_explicit_incomplete_cache(
                ["org/partial"], requested_revision="abc123"
            )
        assert "may need to download files for the requested revision abc123" in caplog.text
        assert "hf download org/partial --revision abc123`" in caplog.text
        assert "will be fetched" not in caplog.text

    def test_cache_discovery_records_retain_classification(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Retained metadata keeps classification, evidence, and decision per repo."""
        monkeypatch.setattr(check_models, "get_cached_model_eligibility", self._entries)

        records = check_models._cache_discovery_records()

        by_id = {r["repo_id"]: r for r in records}
        assert by_id["org/text-only"]["selected"] is False
        assert by_id["org/text-only"]["capability_verdict"] == "no"
        assert by_id["org/text-only"]["model_purpose"] == "text_only"
        assert by_id["org/text-only"]["skip_reasons"] == [
            "model purpose: text-only generation (model_type=afm7; no vision_config/image token keys)"
        ]
        assert by_id["org/vlm"]["selected"] is True
        assert by_id["org/new-arch"]["capability_verdict"] == "unknown"


# --- Nativ-informed discovery hardening ---------------------------------------


def _revision(
    commit_hash: str,
    snapshot_path: str,
    *,
    refs: tuple[str, ...] = (),
    last_modified: float = 0.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        commit_hash=commit_hash,
        snapshot_path=snapshot_path,
        refs=refs,
        last_modified=last_modified,
    )


class TestSnapshotRevisionResolution:
    """Snapshot resolution mirrors the loader: ref/hash, then main, then labelled fallback."""

    @staticmethod
    def _install_cache(monkeypatch: pytest.MonkeyPatch, revisions: list[SimpleNamespace]) -> None:
        repo = SimpleNamespace(repo_id="org/m", revisions=revisions)
        monkeypatch.setattr(
            check_models,
            "_get_hf_cache_info_cached",
            lambda **_: SimpleNamespace(repos=(repo,)),
        )

    def test_requested_hash_prefix_wins_over_newer_snapshots(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An explicit --revision resolves to its own snapshot, not the newest one."""
        self._install_cache(
            monkeypatch,
            [
                _revision("aaaa1111bbbb", "/snap/old", last_modified=1.0),
                _revision("cccc2222dddd", "/snap/new", refs=("main",), last_modified=9.0),
            ],
        )
        resolved = check_models._resolve_model_snapshot("org/m", "aaaa1111")
        assert resolved is not None
        assert resolved.path == Path("/snap/old")
        assert resolved.source == "requested-revision"

    def test_ref_name_resolves_and_unresolvable_request_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A cached ref name matches; a revision absent from the cache never misreports."""
        self._install_cache(
            monkeypatch,
            [_revision("aaaa1111bbbb", "/snap/tagged", refs=("v1.0", "main"))],
        )
        resolved = check_models._resolve_model_snapshot("org/m", "v1.0")
        assert resolved is not None
        assert resolved.source == "requested-revision"
        assert check_models._resolve_model_snapshot("org/m", "not-cached") is None

    def test_main_ref_beats_newest_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without a request, the cached main ref wins even when another snapshot is newer."""
        self._install_cache(
            monkeypatch,
            [
                _revision("aaaa1111bbbb", "/snap/main", refs=("main",), last_modified=1.0),
                _revision("cccc2222dddd", "/snap/detached", last_modified=9.0),
            ],
        )
        resolved = check_models._resolve_model_snapshot("org/m")
        assert resolved is not None
        assert resolved.path == Path("/snap/main")
        assert resolved.source == "refs/main"

    def test_newest_fallback_is_labelled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no main ref, the recency fallback is used and says so."""
        self._install_cache(
            monkeypatch,
            [
                _revision("aaaa1111bbbb", "/snap/older", last_modified=1.0),
                _revision("cccc2222dddd", "/snap/newer", last_modified=9.0),
            ],
        )
        resolved = check_models._resolve_model_snapshot("org/m")
        assert resolved is not None
        assert resolved.path == Path("/snap/newer")
        assert resolved.source == "newest-snapshot"

    def test_provenance_records_resolution_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """model_provenance carries revision_source so reports can show the basis."""
        self._install_cache(
            monkeypatch,
            [_revision("aaaa1111bbbb", "/cache/snapshots/aaaa1111bbbb", refs=("main",))],
        )
        record = check_models._collect_model_provenance("org/m")
        assert record["resolved_revision"] == "aaaa1111bbbb"
        assert record.get("revision_source") == "refs/main"


class TestWeightShardValidation:
    """A safetensors index only counts when every referenced shard is present."""

    @staticmethod
    def _snapshot_with_shards(tmp_path: Path, *, missing: int) -> Path:
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        names = [f"model-{i:05d}-of-00003.safetensors" for i in range(1, 4)]
        index = {"weight_map": {f"layer{i}": name for i, name in enumerate(names)}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        for name in names[: len(names) - missing]:
            safe_io.write_text_no_follow(snapshot / name, "weights")
        return snapshot

    def test_complete_and_incomplete_snapshots(self, tmp_path: Path) -> None:
        """Missing shards are counted with a bounded sample; complete is clean."""
        complete = self._snapshot_with_shards(tmp_path / "ok", missing=0)
        status = check_models._weight_shard_status(complete)
        assert status is not None
        assert (status.missing, status.total) == (0, 3)

        partial = self._snapshot_with_shards(tmp_path / "partial", missing=2)
        status = check_models._weight_shard_status(partial)
        assert status is not None
        assert (status.missing, status.total) == (2, 3)
        assert len(status.missing_sample) == 2
        assert all(name.endswith(".safetensors") for name in status.missing_sample)

    def test_symlinked_real_cache_layout_validates_clean(self, tmp_path: Path) -> None:
        """Index and shards symlinked into blobs/ — every ordinary HF cache — pass.

        Regression: the no-follow reader treated the symlinked index as
        unreadable, so shard validation failed closed and discovery skipped
        every sharded model in a real cache.
        """
        repo_root = tmp_path / "models--org--m"
        blobs = repo_root / "blobs"
        snapshot = repo_root / "snapshots" / "abc"
        blobs.mkdir(parents=True)
        snapshot.mkdir(parents=True)
        names = [f"model-{i:05d}-of-00002.safetensors" for i in (1, 2)]
        index = {"weight_map": {f"layer{i}": name for i, name in enumerate(names)}}
        safe_io.write_text_no_follow(blobs / "indexblob", json.dumps(index))
        (snapshot / "model.safetensors.index.json").symlink_to(blobs / "indexblob")
        for i, name in enumerate(names):
            safe_io.write_text_no_follow(blobs / f"shard{i}", "weights")
            (snapshot / name).symlink_to(blobs / f"shard{i}")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.index_error is None
        assert (status.missing, status.total) == (0, 2)

    def test_shard_symlink_escaping_the_repo_counts_as_missing(self, tmp_path: Path) -> None:
        """Containment still holds: a shard resolving outside the repo is missing."""
        snapshot = self._snapshot_with_shards(tmp_path, missing=1)
        outside = tmp_path / "outside-blob"
        safe_io.write_text_no_follow(outside, "weights")
        (snapshot / "model-00003-of-00003.safetensors").symlink_to(outside)

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_stale_index_beside_complete_family_is_runnable(self, tmp_path: Path) -> None:
        """A re-sharded checkpoint with a stale index passes (loader ignores the index).

        Real-cache case: mlx-community/Apriel-1.5-15b-Thinker-6bit-MLX ships a
        7-shard index beside a complete 3-shard family; mlx-vlm globs the
        shards and loads it fine.
        """
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        stale_names = [f"model-{i:05d}-of-00007.safetensors" for i in range(1, 8)]
        index = {"weight_map": {f"layer{i}": name for i, name in enumerate(stale_names)}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        for i in (1, 2, 3):
            safe_io.write_text_no_follow(
                snapshot / f"model-{i:05d}-of-00003.safetensors", "weights"
            )

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 0

    def test_incomplete_family_does_not_override_the_index(self, tmp_path: Path) -> None:
        """A partial alternative family is still an interrupted download."""
        snapshot = self._snapshot_with_shards(tmp_path, missing=1)
        # One stray shard of a different, incomplete family must not rescue it.
        safe_io.write_text_no_follow(snapshot / "model-00001-of-00009.safetensors", "weights")
        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_partial_indexed_subset_is_never_rescued(self, tmp_path: Path) -> None:
        """When any indexed shard exists, the loader uses that (incomplete) subset.

        mlx-vlm falls back to globbing only when none of the indexed shards
        exist; a partial indexed subset is loaded as-is and cannot supply the
        missing weights — so a complete alternative family must not rescue it.
        """
        snapshot = self._snapshot_with_shards(tmp_path, missing=1)
        for i in (1, 2):
            safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00002.safetensors", "alt")
        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_stale_index_beside_loose_single_file_is_runnable(self, tmp_path: Path) -> None:
        """A re-shard to a single model.safetensors also satisfies the glob fallback."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        stale = [f"model-{i:05d}-of-00002.safetensors" for i in (1, 2)]
        index = {"weight_map": {f"layer{i}": name for i, name in enumerate(stale)}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        safe_io.write_text_no_follow(snapshot / "model.safetensors", "weights")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 0

    def test_unrelated_stem_family_does_not_rescue_a_stale_index(self, tmp_path: Path) -> None:
        """Only a complete family with the model stem (or a loose file) rescues."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        index = {"weight_map": {"layer0": "model-00001-of-00002.safetensors"}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        safe_io.write_text_no_follow(snapshot / "foreign-00001-of-00001.safetensors", "weights")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_misnumbered_family_does_not_rescue(self, tmp_path: Path) -> None:
        """The rescuing family needs the exact 1..N part set, not just N files."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        index = {"weight_map": {"layer0": "model-00001-of-00009.safetensors"}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        for i in (2, 3, 4):
            safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00003.safetensors", "w")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_malformed_index_with_complete_weights_takes_the_glob_fallback(
        self, tmp_path: Path
    ) -> None:
        """The loader swallows index errors and globs; a complete set is runnable."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", "{not json")
        for i in (1, 2):
            safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00002.safetensors", "w")

        assert check_models._weight_shard_status(snapshot) is None

    def test_adapter_file_alone_does_not_rescue_a_broken_index(self, tmp_path: Path) -> None:
        """Auxiliary safetensors (LoRA adapters) cannot vouch for a full checkpoint."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", "{not json")
        safe_io.write_text_no_follow(snapshot / "adapter_model.safetensors", "lora")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.index_error is not None

    def test_adapter_file_does_not_rescue_a_stale_index(self, tmp_path: Path) -> None:
        """A stale index with only an adapter on disk stays an incomplete download."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        index = {"weight_map": {"layer0": "model-00001-of-00002.safetensors"}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        safe_io.write_text_no_follow(snapshot / "adapter_model.safetensors", "lora")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_mixed_shard_series_do_not_rescue_a_stale_index(self, tmp_path: Path) -> None:
        """Two complete series stand for two builds; the glob would merge them.

        Mirrors Blaizzy/nativ#370: the rescuing set must stand on its own —
        mixed series (leftovers of another build) are rejected.
        """
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        index = {"weight_map": {"layer0": "model-00001-of-00009.safetensors"}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        for i in (1, 2):
            safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00002.safetensors", "a")
        for i in (1, 2, 3):
            safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00003.safetensors", "b")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_extra_files_beside_a_complete_series_do_not_rescue(self, tmp_path: Path) -> None:
        """An adapter or loose checkpoint beside the series breaks stand-alone-ness."""
        for extra in ("adapter_model.safetensors", "model.safetensors"):
            repo_root = tmp_path / f"models--org--{extra.split('.')[0]}"
            snapshot = repo_root / "snapshots" / "abc"
            snapshot.mkdir(parents=True)
            index = {"weight_map": {"layer0": "model-00001-of-00009.safetensors"}}
            safe_io.write_text_no_follow(
                snapshot / "model.safetensors.index.json", json.dumps(index)
            )
            for i in (1, 2):
                safe_io.write_text_no_follow(snapshot / f"model-{i:05d}-of-00002.safetensors", "w")
            safe_io.write_text_no_follow(snapshot / extra, "x")

            status = check_models._weight_shard_status(snapshot)
            assert status is not None
            assert status.missing == 1, extra

    def test_consolidated_file_alone_does_not_satisfy_the_fallback(self, tmp_path: Path) -> None:
        """The loader's glob excludes consolidated.safetensors, so it cannot rescue."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        index = {"weight_map": {"layer0": "model-00001-of-00001.safetensors"}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        safe_io.write_text_no_follow(snapshot / "consolidated.safetensors", "weights")

        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_empty_shard_counts_as_missing(self, tmp_path: Path) -> None:
        """A zero-byte shard is an interrupted download, not a weight file."""
        snapshot = self._snapshot_with_shards(tmp_path, missing=0)
        (snapshot / "model-00001-of-00003.safetensors").write_bytes(b"")
        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.missing == 1

    def test_layout_validator_notes_missing_shards(self, tmp_path: Path) -> None:
        """Explicit runs retain the attempt but record the incomplete download."""
        snapshot = self._snapshot_with_shards(tmp_path, missing=1)
        (snapshot / "config.json").write_text("{}")
        (snapshot / "tokenizer_config.json").write_text("{}")
        (snapshot / "preprocessor_config.json").write_text("{}")
        notes = check_models._validate_model_artifact_layout(
            model_identifier="org/m", snapshot_path=snapshot, tokenizer=None
        )
        assert any("1 of 3 weight shards missing" in note for note in notes)

    def test_incomplete_cache_load_failure_is_indeterminate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A model_load failure on a half-downloaded snapshot is environmental."""
        snapshot = self._snapshot_with_shards(tmp_path, missing=2)
        monkeypatch.setattr(
            check_models, "_resolve_model_snapshot_path", lambda *_a, **_k: snapshot
        )
        result = check_models.PerformanceResult(
            model_name="org/m",
            success=False,
            generation=None,
            failure_phase="model_load",
            error_type="FileNotFoundError",
        )
        assert check_models._is_incomplete_cache_failure(result) is True
        assert check_models._execution_status(result) == "indeterminate"
        assert "incomplete cached snapshot" in check_models._indeterminate_reason(result)


class TestTemplateThinkingMarkers:
    """Discovery-time detection of thinking-capable chat templates."""

    def test_jinja_template_with_markers(self, tmp_path: Path) -> None:
        """A chat_template.jinja containing <think> declares thinking."""
        (tmp_path / "chat_template.jinja").write_text("{% if x %}<think>{% endif %}")
        assert check_models._template_declares_thinking(tmp_path) is True

    def test_tokenizer_config_template_without_markers(self, tmp_path: Path) -> None:
        """A plain template is a definite False, not unknown."""
        (tmp_path / "tokenizer_config.json").write_text(
            json.dumps({"chat_template": "{{ messages }}"})
        )
        assert check_models._template_declares_thinking(tmp_path) is False

    def test_kimi_style_marker_in_config_template(self, tmp_path: Path) -> None:
        """Non-ASCII markers (Kimi's ◁think▷) are recognised in JSON templates."""
        (tmp_path / "tokenizer_config.json").write_text(
            json.dumps({"chat_template": "... ◁think▷ ..."})
        )
        assert check_models._template_declares_thinking(tmp_path) is True

    def test_no_template_is_none(self, tmp_path: Path) -> None:
        """No template found anywhere means unknown, never False."""
        assert check_models._template_declares_thinking(tmp_path) is None
        assert check_models._template_declares_thinking(None) is None


class TestEmbeddingLayoutSignal:
    """Sentence-transformers layouts are embeddings regardless of config wording."""

    def test_layout_files_classify_as_embedding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """modules.json / pooling configs are an unambiguous embedding signal."""
        (tmp_path / "modules.json").write_text("[]")
        (tmp_path / "1_Pooling").mkdir()
        (tmp_path / "1_Pooling" / "config.json").write_text("{}")
        monkeypatch.setattr(check_models, "_hf_cache_main_snapshot_path", lambda _repo: tmp_path)
        signal = check_models._embedding_layout_signal(object())
        assert signal is not None
        assert (signal.verdict, signal.purpose) == ("no", "embedding")
        assert any("modules.json" in item for item in signal.evidence)

    def test_absent_layout_is_no_signal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without layout files the classifier falls through to config evidence."""
        monkeypatch.setattr(check_models, "_hf_cache_main_snapshot_path", lambda _repo: tmp_path)
        assert check_models._embedding_layout_signal(object()) is None


class TestShardIndexFailsClosed:
    """An index that exists but cannot be validated is evidence, not a pass."""

    def test_unreadable_index_fails_closed(self, tmp_path: Path) -> None:
        """Corrupt JSON in the index marks the snapshot invalid, not runnable."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", "{not json")
        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.index_error is not None
        assert "unreadable safetensors index" in status.index_error

    def test_index_without_weight_map_fails_closed(self, tmp_path: Path) -> None:
        """A parseable index missing weight_map is equally invalid."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", "{}")
        status = check_models._weight_shard_status(snapshot)
        assert status is not None
        assert status.index_error == "safetensors index has no weight_map object"

    def test_invalid_index_load_failure_is_indeterminate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """model_load failure on a corrupt-index snapshot is environmental too."""
        repo_root = tmp_path / "models--org--m"
        snapshot = repo_root / "snapshots" / "abc"
        snapshot.mkdir(parents=True)
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", "{not json")
        captured: list[tuple[str, str | None]] = []

        def _resolve(model: str, revision: str | None = None) -> Path:
            captured.append((model, revision))
            return snapshot

        monkeypatch.setattr(check_models, "_resolve_model_snapshot_path", _resolve)
        result = check_models.PerformanceResult(
            model_name="org/m",
            success=False,
            generation=None,
            failure_phase="model_load",
            requested_revision="my-branch",
        )
        assert check_models._is_incomplete_cache_failure(result) is True
        # The classifier inspects the snapshot the run actually requested.
        assert captured == [("org/m", "my-branch")]


def test_shard_skip_reason_carries_single_cache_layout_prefix() -> None:
    """skip_reasons prefixes layout reasons once; the shard reason must not re-prefix."""
    entry = check_models.CachedModelEligibility(
        repo_id="org/m",
        supported=False,
        reasons=("2 of 3 weight shards missing (e.g. model-00001-of-00003.safetensors)",),
    )
    assert entry.skip_reasons[0].startswith("cache layout: 2 of 3")
    assert "cache layout: cache layout" not in entry.skip_reasons[0]


class TestModelBurdenFacts:
    """The burden collector reports source-labelled facts only — no fit verdicts."""

    @staticmethod
    def _snapshot(tmp_path: Path) -> Path:
        snapshot = tmp_path / "repo" / "snapshots" / "abc123"
        snapshot.mkdir(parents=True)
        return snapshot

    def _install_snapshot(self, monkeypatch: pytest.MonkeyPatch, snapshot: Path | None) -> None:
        monkeypatch.setattr(
            check_models,
            "_resolve_model_snapshot_path",
            lambda *_args, **_kwargs: snapshot,
        )

    def test_config_sourced_facts_win_over_name_estimate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Config parameter count, quantization, and nested context length are labelled."""
        snapshot = self._snapshot(tmp_path)
        config = {
            "num_parameters": 8_030_000_000,
            "quantization": {"bits": 4, "group_size": 64, "mode": "affine"},
            "text_config": {"max_position_embeddings": 131_072},
        }
        safe_io.write_text_no_follow(snapshot / "config.json", json.dumps(config))
        safe_io.write_text_no_follow(snapshot / "model-00001-of-00002.safetensors", "aa")
        safe_io.write_text_no_follow(snapshot / "model-00002-of-00002.safetensors", "bbb")
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("org/Some-7B-4bit")
        assert burden is not None
        assert burden.parameter_count == 8_030_000_000
        assert burden.parameter_count_source == "num_parameters"
        assert burden.quantization_bits == 4
        assert burden.quantization_group_size == 64
        assert burden.quantization_mode == "affine"
        assert burden.context_length == 131_072
        assert burden.context_length_source == "text_config.max_position_embeddings"
        assert burden.weight_bytes == 5

    def test_name_estimate_fallback_is_labelled_and_skips_bit_suffixes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Without config params, the size token in the name is used — '4bit' is not one."""
        snapshot = self._snapshot(tmp_path)
        safe_io.write_text_no_follow(snapshot / "config.json", json.dumps({}))
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("mlx-community/Qwen2-VL-7B-Instruct-4bit")
        assert burden is not None
        assert burden.parameter_count == 7_000_000_000
        assert burden.parameter_count_source == "name-estimate"
        assert burden.quantization_bits is None
        assert burden.context_length is None
        # No weight files in this snapshot: absence is None, never zero.
        assert burden.weight_bytes is None

    def test_million_scale_and_fractional_size_tokens(self) -> None:
        """M-scale and fractional size tokens parse; the largest token wins."""
        assert check_models._parameter_counts_from_name("org/nano-350M")[0] == 350_000_000
        assert check_models._parameter_counts_from_name("org/big-2.7b-chat")[0] == 2_700_000_000
        assert check_models._parameter_counts_from_name("org/no-size-here")[0] is None

    def test_fractional_sizes_do_not_truncate(self) -> None:
        """Decimal arithmetic: 4.1 is inexact in binary and float-int truncated.

        Mirrors ml-explore/mlx-lm#1726, which fixed the same defect in
        mlx-lm's _parse_size.
        """
        assert check_models._parameter_counts_from_name("org/model-4.1B")[0] == 4_100_000_000
        assert check_models._parameter_counts_from_name("org/tiny-8.2M")[0] == 8_200_000
        assert check_models._parameter_counts_from_name("org/mid-16.9b")[0] == 16_900_000_000

    def test_moe_names_report_total_not_activated_parameters(self) -> None:
        """MoE names carry total and activated sizes; the total is the plain token."""
        moe = check_models._parameter_counts_from_name("mlx-community/Qwen3-30B-A3B-Instruct-4bit")[
            0
        ]
        assert moe == 30_000_000_000
        assert check_models._parameter_counts_from_name(
            "mlx-community/Qwen3-30B-A3B-Instruct-4bit"
        ) == (30_000_000_000, 3_000_000_000)
        assert check_models._parameter_counts_from_name(
            "mlx-community/gemma-4-26b-a4b-it-4bit"
        ) == (
            26_000_000_000,
            4_000_000_000,
        )

    def test_active_only_names_leave_the_total_unknown(self) -> None:
        """An A3B token states active parameters only; it must not become a 3B checkpoint."""
        name = "mlx-community/Kimi-VL-A3B-Thinking-2506-8bit"
        assert check_models._parameter_counts_from_name(name)[0] is None
        assert check_models._parameter_counts_from_name(name) == (None, 3_000_000_000)
        # A capital A that is simply the last letter of a word is not a designation.
        assert check_models._parameter_counts_from_name("org/LLaVA-3B") == (3_000_000_000, None)

    def test_active_only_burden_reports_active_count_separately(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Burden facts keep the active count apart from an unknown total."""
        snapshot = self._snapshot(tmp_path)
        safe_io.write_text_no_follow(snapshot / "config.json", json.dumps({}))
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("mlx-community/Kimi-VL-A3B-Thinking-2506-8bit")
        assert burden is not None
        assert burden.parameter_count is None
        assert burden.active_parameter_count == 3_000_000_000
        assert burden.parameter_count_source == "name-estimate"
        rows = dict(
            check_models._model_burden_rows(
                check_models.PerformanceResult(
                    model_name="org/m", generation=None, success=True, model_burden=burden
                )
            )
        )
        assert "Parameter count" not in rows
        assert rows["Active parameter count"] == (
            "3.00B (name-estimate; total not stated in the name)"
        )

    def test_weight_bytes_ignores_shards_escaping_the_repo_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A symlinked shard resolving outside the repo never counts toward weight bytes."""
        snapshot = self._snapshot(tmp_path)
        outside = tmp_path / "outside.safetensors"
        safe_io.write_text_no_follow(outside, "stolen-bytes")
        (snapshot / "model.safetensors").symlink_to(outside)
        safe_io.write_text_no_follow(snapshot / "real.safetensors", "abcd")
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("org/m")
        assert burden is not None
        assert burden.weight_bytes == 4

    def test_invalid_utf8_config_degrades_to_no_config_facts(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A corrupt (non-UTF-8) config blob must not crash the best-effort reader."""
        snapshot = self._snapshot(tmp_path)
        (snapshot / "config.json").write_bytes(b"\xff\xfe broken \xff")
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("org/corrupt-2B")
        assert burden is not None
        assert burden.context_length is None
        # Name estimate still applies; only the config-sourced facts are lost.
        assert burden.parameter_count_source == "name-estimate"

    def test_weight_bytes_follow_loader_selection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Checkpoint bytes count only the files the loader would select.

        An adapter beside an indexed checkpoint and a consolidated file are
        swept up by a bare glob but never loaded as the checkpoint.
        """
        snapshot = self._snapshot(tmp_path)
        safe_io.write_text_no_follow(snapshot / "config.json", json.dumps({}))
        names = [f"model-{i:05d}-of-00002.safetensors" for i in (1, 2)]
        index = {"weight_map": {f"layer{i}": name for i, name in enumerate(names)}}
        safe_io.write_text_no_follow(snapshot / "model.safetensors.index.json", json.dumps(index))
        safe_io.write_text_no_follow(snapshot / names[0], "aa")
        safe_io.write_text_no_follow(snapshot / names[1], "bbb")
        safe_io.write_text_no_follow(snapshot / "adapter_model.safetensors", "0123456789")
        safe_io.write_text_no_follow(snapshot / "consolidated.safetensors", "0123456789")
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("org/m")
        assert burden is not None
        assert burden.weight_bytes == 5

    def test_unresolvable_snapshot_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No cached snapshot means no burden facts, not a partial record."""
        self._install_snapshot(monkeypatch, None)
        refreshes: list[bool] = []

        def record_and_miss(*, refresh: bool = False) -> SimpleNamespace:
            refreshes.append(refresh)
            return SimpleNamespace(repos=())

        monkeypatch.setattr(check_models, "_get_hf_cache_info_cached", record_and_miss)
        assert check_models._collect_model_burden("org/uncached") is None
        # The miss triggered exactly one refreshed rescan before giving up.
        assert refreshes == [True]

    def test_cold_download_retries_with_refreshed_cache_scan(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A snapshot downloaded during this run is found after one cache refresh."""
        snapshot = self._snapshot(tmp_path)
        safe_io.write_text_no_follow(
            snapshot / "config.json", json.dumps({"max_position_embeddings": 4096})
        )
        state = {"refreshed": False}

        def fake_cache_info(*, refresh: bool = False) -> SimpleNamespace:
            if refresh:
                state["refreshed"] = True
            return SimpleNamespace(repos=())

        monkeypatch.setattr(check_models, "_get_hf_cache_info_cached", fake_cache_info)
        monkeypatch.setattr(
            check_models,
            "_resolve_model_snapshot_path",
            lambda *_a, **_k: snapshot if state["refreshed"] else None,
        )

        burden = check_models._collect_model_burden("org/just-downloaded")
        assert burden is not None
        assert burden.context_length == 4096

    def test_real_hf_cache_symlink_layout_is_readable(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Snapshot files symlinked into blobs/ (the real HF layout) must be read.

        Regression: the cached Qwen/Qwen3-VL-2B-Instruct config declares
        text_config.max_position_embeddings, but the no-follow reader rejected
        the config symlink and dropped the context length entirely.
        """
        repo_root = tmp_path / "models--Qwen--Qwen3-VL-2B-Instruct"
        blobs = repo_root / "blobs"
        snapshot = repo_root / "snapshots" / "abc123"
        blobs.mkdir(parents=True)
        snapshot.mkdir(parents=True)
        config = {"text_config": {"max_position_embeddings": 262_144}}
        safe_io.write_text_no_follow(blobs / "cfgblob", json.dumps(config))
        safe_io.write_text_no_follow(blobs / "weightblob", "12345678")
        (snapshot / "config.json").symlink_to(blobs / "cfgblob")
        (snapshot / "model.safetensors").symlink_to(blobs / "weightblob")
        self._install_snapshot(monkeypatch, snapshot)

        burden = check_models._collect_model_burden("Qwen/Qwen3-VL-2B-Instruct")
        assert burden is not None
        assert burden.context_length == 262_144
        assert burden.context_length_source == "text_config.max_position_embeddings"
        assert burden.parameter_count == 2_000_000_000
        assert burden.parameter_count_source == "name-estimate"
        assert burden.weight_bytes == 8


@pytest.mark.usefixtures("_clear_arch_caches")
def test_drafter_checkpoints_are_flagged_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """A speculative-decoding draft model is excluded with its evidence, never crashed."""
    monkeypatch.setattr(
        check_models, "_mlx_vlm_drafter_model_types", lambda: frozenset({"qwen3_5_mtp"})
    )
    monkeypatch.setattr(check_models, "_mlx_vlm_image_generation_model_types", frozenset)
    by_table = _capability_for(
        monkeypatch, config={"model_type": "qwen3_5_mtp", "architectures": ["Qwen3_5MTP"]}
    )
    assert (by_table.verdict, by_table.purpose) == ("no", "speculative_drafter")
    assert "is an mlx-vlm drafter" in by_table.evidence[0]

    by_projector = _capability_for(
        monkeypatch,
        config={
            "model_type": "gemma4",
            "architectures": ["Gemma4ForConditionalGeneration"],
            "vision_config": {"depth": 4},
            "dflash_config": {"projector_type": "dspark"},
        },
    )
    assert (by_projector.verdict, by_projector.purpose) == ("no", "speculative_drafter")

    by_architecture = _capability_for(
        monkeypatch,
        config={"model_type": "gemma4_dspark", "architectures": ["Gemma4DSparkForCausalLM"]},
    )
    assert (by_architecture.verdict, by_architecture.purpose) == ("no", "speculative_drafter")
    assert "skip" in (by_architecture.skip_reason or "") or by_architecture.skip_reason
    assert by_architecture.skip_reason is not None
    assert "speculative drafter" in by_architecture.skip_reason


@pytest.mark.usefixtures("_clear_arch_caches")
def test_image_generation_families_are_flagged_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Upstream's image-producing loaders are excluded even without pipeline config keys."""
    monkeypatch.setattr(check_models, "_mlx_vlm_drafter_model_types", frozenset)
    monkeypatch.setattr(
        check_models, "_mlx_vlm_image_generation_model_types", lambda: frozenset({"flux2"})
    )
    monkeypatch.setattr(check_models, "_mlx_vlm_model_remapping", lambda: {"flux_2": "flux2"})
    generation = _capability_for(
        monkeypatch, config={"model_type": "flux_2", "architectures": ["Flux2Transformer"]}
    )
    assert (generation.verdict, generation.purpose) == ("no", "image_or_video_generation")
    assert "is_image_generation_model" in generation.evidence[0]

    # A genuine VLM whose family is not flagged is untouched by the new rules.
    vlm = _capability_for(monkeypatch, config=VLM_CONFIG)
    assert (vlm.verdict, vlm.purpose) == ("yes", "image_to_text")
