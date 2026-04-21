from viz_sys_conferences.registry import generate_targets


def test_no_duplicate_targets():
    targets = generate_targets(2006, 2026)
    pairs = [(t.conference, t.year) for t in targets]
    assert len(pairs) == len(set(pairs)), "Duplicate (conference, year) pairs found"


def test_osdi_even_years_only():
    targets = [t for t in generate_targets(2006, 2026) if t.conference == "OSDI"]
    for t in targets:
        assert t.year % 2 == 0, f"OSDI has odd year {t.year}"


def test_sosp_odd_years_only():
    targets = [t for t in generate_targets(2006, 2026) if t.conference == "SOSP"]
    for t in targets:
        assert t.year % 2 == 1, f"SOSP has even year {t.year}"


def test_sosp_starts_at_2013():
    """SOSP before 2013 returns 404 at sigops.org."""
    targets = [t for t in generate_targets(2006, 2026) if t.conference == "SOSP"]
    years = [t.year for t in targets]
    assert 2007 not in years
    assert 2011 not in years
    assert 2013 in years


def test_eurosys_no_2020():
    """EuroSys 2020 was cancelled (COVID) and must not appear."""
    targets = [t for t in generate_targets(2006, 2026) if t.conference == "EuroSys"]
    years = [t.year for t in targets]
    assert 2020 not in years


def test_eurosys_2022_override_url():
    targets = [t for t in generate_targets(2022, 2022) if t.conference == "EuroSys"]
    assert len(targets) == 1
    assert "index.html" in targets[0].url


def test_eurosys_2026_preliminary_url():
    targets = [t for t in generate_targets(2026, 2026) if t.conference == "EuroSys"]
    assert len(targets) == 1
    assert "preliminary-program.html" in targets[0].url


def test_nsdi_annual():
    """NSDI URLs exist from 2012; older years return 404."""
    targets = [t for t in generate_targets(2012, 2020) if t.conference == "NSDI"]
    years = [t.year for t in targets]
    assert years == list(range(2012, 2021))


def test_atc_annual():
    """ATC URLs exist from 2012; older years return 404."""
    targets = [t for t in generate_targets(2012, 2020) if t.conference == "ATC"]
    years = [t.year for t in targets]
    assert years == list(range(2012, 2021))


def test_usenix_url_format():
    targets = [t for t in generate_targets(2024, 2025) if t.conference == "OSDI"]
    assert any("osdi24" in t.url for t in targets)


def test_sosp_toc_url_for_2021_2023():
    targets = [t for t in generate_targets(2021, 2023) if t.conference == "SOSP"]
    for t in targets:
        assert "toc.html" in t.url, f"SOSP {t.year} should use toc.html, got {t.url}"


def test_all_conferences_present():
    targets = generate_targets(2010, 2026)
    conferences = {t.conference for t in targets}
    assert conferences == {"OSDI", "NSDI", "ATC", "SOSP", "EuroSys"}
