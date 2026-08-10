import pytest

from npnkorea import LonLat, NPNKoreaError, to_npn, to_wgs


def test_public_api_exports() -> None:
    assert LonLat is not None
    assert NPNKoreaError is not None
    assert callable(to_npn)
    assert callable(to_wgs)


def test_api_entrypoint_invokes_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    uvicorn = pytest.importorskip("uvicorn")

    from npnkorea.web import main as web_main

    captured: dict[str, object] = {}

    def fake_run(app: str, host: str, port: int, reload: bool) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(uvicorn, "run", fake_run)

    web_main.main()

    assert captured == {
        "app": "npnkorea.web.main:app",
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
    }
