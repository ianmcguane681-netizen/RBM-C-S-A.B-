"""A static-site connector must render the dashboard without Python or redirects."""
from pathlib import Path


ROOT = Path("index.html").read_text(encoding="utf-8")
SCRIPT = Path("backend/static/app.js").read_text(encoding="utf-8")


def test_root_is_the_dashboard_not_a_redirect_to_an_internal_file():
    assert "http-equiv=\"refresh\"" not in ROOT
    assert "NEXUS" in ROOT
    assert 'href="backend/static/styles.css"' in ROOT
    assert 'src="backend/static/app.js"' in ROOT


def test_failed_api_fetch_renders_explicit_offline_state():
    catch = SCRIPT.split("catch (error)", 1)[1]

    assert "renderOverview(offlineOverview)" in catch
    assert "renderConnectors(offlineConnectors)" in catch
    assert "Offline layout preview" in catch
    assert 'cost_basis:null' in SCRIPT
