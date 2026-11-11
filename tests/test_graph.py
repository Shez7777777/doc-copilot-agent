import pytest

pytest.importorskip("langgraph.types", exc_type=ImportError)

from langgraph.types import Command  # noqa: E402

from doccopilot.graph import build_graph  # noqa: E402

FIRST = {"company_name": "Northwind Labs", "employee_name": "Sara Khan", "job_title": "Data Analyst",
         "start_date": "2025-01-06"}
SECOND = {"end_date": "2026-06-30", "duties": "Built weekly sales dashboards.",
          "signatory_name": "Omar Ali", "signatory_title": "HR Manager"}


def run(graph, first_message, answers):
    config = {"configurable": {"thread_id": "t1"}}
    questions = []
    result = graph.invoke({"conversation": [first_message]}, config)
    for a in answers:
        assert "__interrupt__" in result
        questions.append(result["__interrupt__"][0].value["question"])
        result = graph.invoke(Command(resume=a), config)
    return result, questions


def test_asks_for_missing_fields_then_renders(fake_llm, tmp_path):
    llm = fake_llm("experience_letter", [FIRST, SECOND])
    graph = build_graph(llm, out_dir=tmp_path)
    result, questions = run(graph, "experience letter for Sara", ["she left on 30 June 2026 ...", "yes"])
    assert "Last working day" in questions[0]
    assert "Here's what I'll put" in questions[1]
    assert result["output_path"].endswith(".docx")


def test_change_request_goes_back_to_extraction(fake_llm, tmp_path):
    llm = fake_llm("experience_letter", [{**FIRST, **SECOND}, {"job_title": "Senior Data Analyst"}])
    graph = build_graph(llm, out_dir=tmp_path)
    result, _ = run(graph, "experience letter", ["title should be Senior Data Analyst", "yes"])
    assert result["values"]["job_title"] == "Senior Data Analyst"


def test_unsupported_document_ends_politely(fake_llm, tmp_path):
    graph = build_graph(fake_llm("none", []), out_dir=tmp_path)
    result, _ = run(graph, "write me a will", [])
    assert "I can only draft" in result["message"]
