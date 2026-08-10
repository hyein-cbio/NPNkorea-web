import pytest

from npnkorea import LonLat, NPNKoreaError, to_npn, to_wgs


def test_to_wgs_supports_hangul_and_romanized_inputs() -> None:
    point = to_wgs("다사 5396 5207")
    assert point.lon == pytest.approx(126.9787, abs=5e-5)
    assert point.lat == pytest.approx(37.56684, abs=1e-5)

    point = to_wgs("DaSa53965207")
    assert point.lon == pytest.approx(126.9787, abs=5e-5)
    assert point.lat == pytest.approx(37.56684, abs=1e-5)


def test_to_npn_converts_known_points() -> None:
    code = to_npn(LonLat(lon=126.978422, lat=37.566742))
    assert code == "다사 5393 5205"

    code = to_npn([LonLat(lon=126.978422, lat=37.566742)], output="abc")
    assert code == ["DaSa 5393 5205"]


def test_to_npn_rejects_projected_out_of_grid_points() -> None:
    with pytest.raises(NPNKoreaError, match="outside the supported NPN grid after projection"):
        to_npn(LonLat(lon=124.000001, lat=33.0))


def test_round_trip_within_supported_korea_bounds() -> None:
    codes = ["다사 5396 5207", "마라 4347 8827", "다다 0694 0013"]
    points = to_wgs(codes)
    round_trip = to_npn(points)
    assert round_trip == codes


def test_to_wgs_supports_compact_and_vectorized_inputs() -> None:
    points = to_wgs(["다사53965207", "MaRa43478827", "dada06940013"])

    assert len(points) == 3
    assert points[0].lon == pytest.approx(126.9787, abs=5e-5)
    assert points[0].lat == pytest.approx(37.56684, abs=1e-5)
    assert points[1].lon == pytest.approx(129.0756, abs=5e-5)
    assert points[1].lat == pytest.approx(35.17949, abs=1e-5)
    assert points[2].lon == pytest.approx(126.49827, abs=5e-5)
    assert points[2].lat == pytest.approx(33.48897, abs=1e-5)


def test_to_wgs_validates_input_strings() -> None:
    with pytest.raises(NPNKoreaError, match="must be a string or a sequence of strings"):
        to_wgs(1)

    with pytest.raises(NPNKoreaError, match="must contain only strings"):
        to_wgs(["다사 5396 5207", None])

    with pytest.raises(NPNKoreaError, match="must be valid NPN strings"):
        to_wgs("   ")

    with pytest.raises(NPNKoreaError, match="must be valid NPN strings"):
        to_wgs("DS 5396 5207")

    with pytest.raises(NPNKoreaError, match="must be valid NPN strings"):
        to_wgs("다사 539 5207")

    with pytest.raises(NPNKoreaError, match="must use valid NPN letter pairs"):
        to_wgs("갸사 5396 5207")


def test_to_wgs_rejects_codes_outside_supported_korea_bounds() -> None:
    with pytest.raises(NPNKoreaError, match="outside the supported Korea bounds"):
        to_wgs("하하 9999 9999")


def test_to_wgs_returns_empty_list_for_empty_input() -> None:
    assert to_wgs([]) == []


def test_to_npn_supports_single_and_vectorized_inputs() -> None:
    points = [
        LonLat(lon=126.978422, lat=37.566742),
        LonLat(lon=129.075642, lat=35.179554),
        LonLat(lon=126.4982702, lat=33.4889944),
    ]

    assert to_npn(points) == ["다사 5393 5205", "마라 4347 8827", "다다 0694 0013"]
    assert to_npn(points, output="abc") == ["DaSa 5393 5205", "MaRa 4347 8827", "DaDa 0694 0013"]


def test_to_npn_accepts_two_point_batches_without_fallback_magic() -> None:
    points = [
        LonLat(lon=126.978422, lat=37.566742),
        LonLat(lon=129.075642, lat=35.179554),
    ]

    assert to_npn(points) == ["다사 5393 5205", "마라 4347 8827"]


def test_to_npn_validates_input_points() -> None:
    with pytest.raises(NPNKoreaError, match="LonLat or a sequence of LonLat values"):
        to_npn(1)

    with pytest.raises(NPNKoreaError, match="LonLat or a sequence of LonLat values"):
        to_npn({"x": 126.9, "y": 37.5})

    with pytest.raises(NPNKoreaError, match="Batch inputs must contain only LonLat values"):
        to_npn([{"lon": 126.9, "lat": 37.5}])

    with pytest.raises(NPNKoreaError, match="Batch inputs must contain only LonLat values"):
        to_npn([(126.978422, 37.566742), (129.075642, 35.179554)])

    with pytest.raises(NPNKoreaError, match="`lon` and `lat` must be finite"):
        to_npn(LonLat(lon=126.9, lat=float("nan")))

    with pytest.raises(NPNKoreaError, match="`lon` must be between 124 and 133"):
        to_npn(LonLat(lon=140.0, lat=37.5))

    with pytest.raises(NPNKoreaError, match="`lat` must be between 32 and 39"):
        to_npn(LonLat(lon=126.9, lat=32.0))

    with pytest.raises(NPNKoreaError, match="must be either 'han' or 'abc'"):
        to_npn(LonLat(lon=126.9, lat=37.5), output="latin")


def test_to_npn_returns_empty_list_for_empty_input() -> None:
    assert to_npn([]) == []
