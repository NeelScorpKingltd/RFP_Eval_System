"""FR-UI-02..07 Streamlit gate and results smoke flows."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from rfp_eval.db.repositories import CriteriaRepo
from rfp_eval.db.schema import init_and_seed_db
from rfp_eval.domain.models import ProcurementRisk
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.orchestration.runner import run_evaluation
from rfp_eval.services.negotiation import generate_and_store_playbook
from tests.integration.test_fr_pipe_01_graph import deps, reply, request
from tests.unit.test_fr_neg_01_agent import playbook_reply

APP = Path(__file__).resolve().parents[2] / "app.py"


def test_fr_ui_02_04_weight_gate_disables_evaluate(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "ui.db"
    init_and_seed_db(path)
    criteria = CriteriaRepo(path).list_all()
    criteria[0].weight = 25
    CriteriaRepo(path).save(criteria)
    monkeypatch.setenv("RFP_DB_PATH", str(path))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert any("95.00%" in item.value for item in app.warning)
    demo = next(item for item in app.checkbox if item.label == "Use Free Default Demo Model")
    assert demo.disabled
    app.session_state["workflow_stage"] = 3
    app.session_state["workflow_view"] = 3
    app.run()
    assert not app.exception
    assert next(item for item in app.button if item.label == "Evaluate").disabled


def test_fr_ui_02_description_requires_unlock_and_save(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "ui.db"
    monkeypatch.setenv("RFP_DB_PATH", str(path))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert not app.text_area
    unlock = next(item for item in app.checkbox if item.label == "Unlock 'What to assess' editing")
    unlock.check().run()
    assert not app.exception
    app.text_area[0].set_value("Assess architecture, integration, and migration evidence").run()
    assert CriteriaRepo(path).list_all()[0].description == (
        "Architecture, integration, and technical fit"
    )
    next(item for item in app.button if item.label == "Save criteria").click().run()
    assert not app.exception
    saved = CriteriaRepo(path).list_all()[0]
    assert saved.description == "Assess architecture, integration, and migration evidence"
    assert saved.name == "Technical Capability"
    assert saved.max_score == 10


def test_fr_ui_10_stage_lock_advances_after_criteria_save(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "ui.db"))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert next(item for item in app.button if "2 · Suppliers" in item.label).disabled
    next(item for item in app.button if item.label == "Save criteria").click().run()
    assert not app.exception
    assert app.session_state["workflow_stage"] == 2
    assert next(item for item in app.button if "1 · Criteria" in item.label).disabled


def test_fr_ui_03_demo_load_and_supplier_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "ui.db"))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.session_state["workflow_stage"] = 2
    app.session_state["workflow_view"] = 2
    app.run()
    next(item for item in app.button if item.label == "Load demo suppliers").click().run()
    assert not app.exception
    assert len(app.session_state["suppliers"]) == 4
    first_name = next(item for item in app.text_input if item.label == "Supplier name")
    first_name.set_value("").run()
    assert any("needs a name" in item.value for item in app.warning)


def test_fr_ui_04_07_leaderboard_and_run_details(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "evaluation.db"
    dependencies = deps(tmp_path, FakeLLMClient([reply(8), reply(7)]))
    result = run_evaluation(request(), dependencies)
    result.evaluations["Apex Systems"].procurement_risks.append(
        ProcurementRisk(
            risk_category="Technical",
            severity="High",
            issue="Integration evidence needs clarification.",
            verbatim_excerpt="Integration approach is under review.",
        )
    )
    charts: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setattr("streamlit.bar_chart", lambda data, **kwargs: charts.append((data, kwargs)))
    monkeypatch.setenv("RFP_DB_PATH", str(path))
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.session_state["run_result"] = result
    app.session_state["workflow_stage"] = 4
    app.session_state["workflow_view"] = 4
    app.run()
    assert not app.exception
    assert any(item.label == "Compare a criterion with the peer best" for item in app.selectbox)
    assert len(charts) == 2
    assert charts[0][1]["y"] == ["Supplier", "Peer best"]
    assert charts[1][1]["y"] == "Risks"
    assert charts[1][0][0]["Risks"] == 1
    next(item for item in app.button if "3 · Run & leaderboard" in item.label).click().run()
    assert not app.exception
    assert not any(item.label == "Evaluate" for item in app.button)
    assert any(item.label == "Leader PPI" for item in app.metric)
    app.session_state["workflow_stage"] = 3
    app.session_state["workflow_view"] = 3
    app.run()
    assert not app.exception
    assert "Apex Systems" in app.dataframe[0].value["Supplier"].tolist()
    app.session_state["workflow_stage"] = 4
    app.session_state["workflow_view"] = 4
    app.run()
    assert not app.exception
    next(item for item in app.button if "5 · Playbook & details" in item.label).click().run()
    assert not app.exception
    assert any(result.rfp_run_id in item.value for item in app.text)


def test_fr_ui_07_saved_playbook_matrix_renders(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "evaluation.db"
    fake = FakeLLMClient([reply(8), reply(7), playbook_reply()])
    dependencies = deps(tmp_path, fake)
    result = run_evaluation(request(), dependencies)
    generate_and_store_playbook(result, fake, dependencies.result_repo)
    monkeypatch.setenv("RFP_DB_PATH", str(path))
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.session_state["run_result"] = result
    app.session_state["workflow_stage"] = 4
    app.session_state["workflow_view"] = 5
    app.run()
    assert not app.exception
    assert any("Target concession" in item.value for item in app.caption)
    assert any("PRIORITY 1" in item.value for item in app.caption)


def test_fr_ui_04_evaluate_button_runs_fake_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "evaluation.db"))
    fake = FakeLLMClient([reply(8), reply(7), reply(6), reply(5)])
    monkeypatch.setattr("rfp_eval.ui.screens.run.get_llm_client", lambda *args: fake)
    monkeypatch.setattr("rfp_eval.ui.sidebar.probe_llm", lambda _: (True, "Connection verified."))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    next(item for item in app.text_input if item.label == "API key").set_value("fake-key").run()
    app.session_state["workflow_stage"] = 2
    app.session_state["workflow_view"] = 2
    app.run()
    next(item for item in app.button if item.label == "Load demo suppliers").click().run()
    assert not next(
        item for item in app.button if item.label == "Save suppliers & continue"
    ).disabled
    app.session_state["workflow_stage"] = 3
    app.session_state["workflow_view"] = 3
    app.run()
    evaluate = next(item for item in app.button if item.label == "Evaluate")
    assert not evaluate.disabled
    evaluate.click().run()
    assert not app.exception
    assert len(fake.calls) == 4
    assert len(app.session_state["run_result"].ranking.suppliers) == 4


def test_fr_llm_02_key_check_runs_once_and_blocks_invalid_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "ui.db"))
    calls: list[str] = []

    def reject(settings) -> tuple[bool, str]:
        calls.append(settings.provider.value)
        return False, "OpenAI: check your API key."

    monkeypatch.setattr("rfp_eval.ui.sidebar.probe_llm", reject)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    next(item for item in app.text_input if item.label == "API key").set_value("invalid-key").run()
    assert not app.exception
    assert calls == ["openai"]
    assert any("Unavailable" in item.value for item in app.error)
    app.run()
    assert calls == ["openai"]


def test_fr_val_04_fault_toggle_accepts_verified_byok(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setattr("rfp_eval.ui.sidebar.probe_llm", lambda _: (True, "Connection verified."))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    toggle = next(item for item in app.checkbox if item.label == "Simulate Malformed LLM Output")
    assert toggle.disabled
    next(item for item in app.text_input if item.label == "API key").set_value("fake-key").run()
    toggle = next(item for item in app.checkbox if item.label == "Simulate Malformed LLM Output")
    assert not toggle.disabled
    toggle.check().run()
    assert not app.exception
    assert any("skip the cache" in item.value for item in app.warning)


def test_fr_ui_07_history_load_and_cancel_preserve_saved_run(tmp_path: Path, monkeypatch) -> None:
    dependencies = deps(tmp_path, FakeLLMClient([reply(8), reply(7)]))
    completed = run_evaluation(request(), dependencies)
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "evaluation.db"))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    next(item for item in app.button if item.label == "Previous runs").click().run()
    assert not app.exception
    assert any(completed.rfp_run_id in item.value for item in app.text)
    next(item for item in app.button if item.label == "Load results").click().run()
    assert app.session_state["run_result"].rfp_run_id == completed.rfp_run_id
    assert app.session_state["workflow_stage"] == 4
    next(item for item in app.button if item.label == "Cancel run").click().run()
    assert app.session_state["workflow_stage"] == 1
    assert "run_result" not in app.session_state
    assert dependencies.run_repo.get(completed.rfp_run_id) is not None
