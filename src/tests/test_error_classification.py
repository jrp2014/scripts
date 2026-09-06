"""Unit tests for error classification and package attribution logic."""

import pytest

from check_models import (
    _attribute_error_to_package,
    _build_canonical_error_code,
    _build_error_signature,
    _classify_error,
)


@pytest.mark.parametrize(
    ("message", "expected_type"),
    [
        # Critical errors
        ("[metal::malloc] Attempting to allocate...", "OOM"),
        ("maximum allowed buffer size exceeded", "OOM"),
        (
            (
                "[METAL] Command buffer execution failed: Insufficient Memory "
                "(00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)."
            ),
            "OOM",
        ),
        ("Operation timeout", "Timeout"),
        (
            "Model loading failed: Server disconnected without sending a response.",
            "Network Error",
        ),
        # Dependency/Version errors
        ("ImportError: cannot import name 'foo'", "Lib Version"),
        ("requires packages X. pip install X", "Missing Dep"),
        # API Mismatches
        ("got an unexpected keyword argument 'images'", "API Mismatch"),
        ("TypeError: _batch_encode_plus() got an unexpected keyword", "API Mismatch"),
        # Config/Validation errors
        ("does not appear to have a file named config.json", "Config Missing"),
        ("ValueError: chat_template is not set", "No Chat Template"),
        # Upstream mlx-vlm raises "Model type {x} not supported." — must beat
        # the generic Weight Mismatch / Model Error buckets.
        ("Model type llava_qwen2 not supported. Error: no module", "Unsupported Arch"),
        ("ValueError: Model type foo not supported.", "Unsupported Arch"),
        ("ValueError: Missing 5 parameters:", "Weight Mismatch"),
        # MLX/Core errors
        ("std::bad_cast", "Type Cast Error"),
        # Specific component errors
        ("Unrecognized image_processor", "Processor Error"),
        ("Tokenizer class Tokenizer404 does not exist", "Tokenizer Error"),
        # Generic
        ("Model generation failed", "Model Error"),
        ("Something went wrong", "Error"),
    ],
)
def test_classify_error(message: str, expected_type: str) -> None:
    """Verify that error messages are correctly classified."""
    assert _classify_error(message) == expected_type


@pytest.mark.parametrize(
    ("message", "traceback", "expected_package"),
    [
        # MLX Core
        ("std::bad_cast", None, "mlx"),
        ("metal::malloc failed", "mlx/core/memory.cpp", "mlx"),
        ("Error", "mlx/python/mlx/ops.py line 42", "mlx"),
        # MLX-VLM
        ("ValueError: Load check failed", "mlx_vlm/utils.py", "mlx-vlm"),
        ("apply_chat_template failed", None, "mlx-vlm"),
        # Transformers
        ("ImportError: cannot import name", "transformers/models/auto.py", "transformers"),
        ("got an unexpected keyword argument", "transformers/tokenization.py", "transformers"),
        # Model/Config
        ("missing parameters", None, "model-config"),
        ("chat_template is not set", None, "model-config"),
        # HuggingFace
        ("does not appear to have a file", "huggingface_hub/utils.py", "huggingface-hub"),
        (
            "Model loading failed: Server disconnected without sending a response.",
            "mlx_vlm/utils.py caused by httpcore.RemoteProtocolError",
            "unknown",
        ),
        # Wrapped upstream failures should prefer the deeper traceback owner
        (
            "Model generation failed: Failed to process inputs with error: can only concatenate str",
            (
                "Traceback (most recent call last):\n"
                '  File "mlx_vlm/utils.py", line 873, in process_inputs_with_fallback\n'
                '  File "transformers/models/florence2/processing_florence2.py", line 185, in __call__\n'
                'TypeError: can only concatenate str (not "NoneType") to str\n\n'
                "The above exception was the direct cause of the following exception:\n\n"
                '  File "mlx_vlm/generate.py", line 515, in stream_generate\n'
                "ValueError: Failed to process inputs with error: can only concatenate str\n"
            ),
            "transformers",
        ),
        # A repo's trust_remote_code module (transformers dynamic-module cache)
        # owns the failure even when transformers frames surround it.
        (
            "ImportError: cannot import name 'DefaultFastImageProcessorKwargs'",
            (
                '  File "transformers/dynamic_module_utils.py", line 309, in get_class_in_module\n'
                '  File ".cache/huggingface/modules/transformers_modules/_8d30a0e4/71940f1d/'
                'image_processing_siglip2_fast.py", line 7, in <module>\n'
            ),
            "model-repo-code",
        ),
        (
            "Model loading failed: cannot import name 'X'",
            (
                '  File "transformers_modules/_abc/processing_custom.py", line 3, in <module>\n'
                "The above exception was the direct cause of the following exception:\n"
                '  File "mlx_vlm/utils.py", line 1212, in load\n'
            ),
            "model-repo-code",
        ),
        # Unknown
        ("Random error", "unknown_lib/main.py", "unknown"),
    ],
)
def test_attribute_error(message: str, traceback: str | None, expected_package: str) -> None:
    """Verify that errors are attributed to the correct package."""
    assert _attribute_error_to_package(message, traceback) == expected_package


def test_build_canonical_error_code_stable_tokens() -> None:
    """Canonical code should include package, phase, and stage in stable form."""
    code = _build_canonical_error_code(
        error_stage="API Mismatch",
        error_package="transformers",
        failure_phase="decode",
    )
    assert code == "TRANSFORMERS_DECODE_API_MISMATCH"


def test_error_signature_normalizes_numeric_variants() -> None:
    """Numeric differences in shape errors should map to the same signature."""
    code = _build_canonical_error_code(
        error_stage="Model Error",
        error_package="mlx-vlm",
        failure_phase="decode",
    )
    sig_a = _build_error_signature(
        error_code=code,
        error_message="[broadcast_shapes] Shapes (3,1,2048) and (3,1,6065) mismatch",
        error_traceback=None,
    )
    sig_b = _build_error_signature(
        error_code=code,
        error_message="[broadcast_shapes] Shapes (984,2048) and (1,0,2048) mismatch",
        error_traceback=None,
    )
    assert sig_a == sig_b
