import base64
import httpx
from fastapi import HTTPException
import pytest

from app.core.config import Settings
from app.modules.studio.router import GenerateImagesRequest, generate_images


PHOTO = base64.b64encode(b"\x89PNG\r\n\x1a\nsmall-test-image").decode()


def request(**changes) -> GenerateImagesRequest:
    values = {
        "image_base64": PHOTO, "image_mime_type": "image/png",
        "product_name": "Anillo de plata", "product_description": "Plata lisa",
        "style": "Minimalista", "scene": "Mesa de piedra clara", "lighting": "Natural",
        "aspect_ratio": "4:5", "variations": 2,
    }
    return GenerateImagesRequest(**(values | changes))


def test_studio_sends_reference_and_exact_requested_count() -> None:
    observed = []

    def respond(req: httpx.Request) -> httpx.Response:
        observed.append(req)
        return httpx.Response(200, json={"data": [{"b64_json": "aW1hZ2Ux"}, {"b64_json": "aW1hZ2Uy"}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = generate_images(request(), Settings(openai_api_key="test-only", _env_file=None), client)

    assert len(result.images) == 2
    assert [image.image_base64 for image in result.images] == ["aW1hZ2Ux", "aW1hZ2Uy"]
    assert observed[0].url.path == "/v1/images/edits"
    body = observed[0].content
    assert b'name="n"' in body and b"\r\n2\r\n" in body
    assert b"1024x1280" in body
    assert b"gpt-image-2" in body
    assert b"small-test-image" in body
    assert b"Mesa de piedra clara" in body


def test_studio_rejects_invalid_image_before_paid_call() -> None:
    calls = 0

    def respond(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        try:
            generate_images(request(image_base64=base64.b64encode(b"not-png").decode()), Settings(openai_api_key="test-only", _env_file=None), client)
            assert False, "Expected validation error"
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 422
    assert calls == 0


def test_studio_accepts_jpeg_with_matching_mime_without_paid_call() -> None:
    observed = []

    def respond(req: httpx.Request) -> httpx.Response:
        observed.append(req)
        return httpx.Response(200, json={"data": [{"b64_json": "aW1hZ2U="}]})

    jpeg = base64.b64encode(b"\xff\xd8\xffsmall-test-image").decode()
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = generate_images(request(image_base64=jpeg, image_mime_type="image/jpeg", variations=1),
                                 Settings(openai_api_key="test-only", _env_file=None), client)
    assert len(result.images) == 1
    assert b'image/jpeg' in observed[0].content


def test_studio_without_key_does_not_call_provider() -> None:
    with pytest.raises(HTTPException) as error:
        generate_images(request(), Settings(openai_api_key=None, _env_file=None))
    assert error.value.status_code == 503


def test_studio_provider_failure_has_no_sensitive_details() -> None:
    def respond(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "private provider detail"}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(HTTPException) as error:
            generate_images(request(), Settings(openai_api_key="test-only", _env_file=None), client)
    assert error.value.status_code == 503
    assert "private provider detail" not in error.value.detail
