from docx import Document

from doccopilot import steps
from doccopilot.templates import load_templates, parse_date, render_docx

TEMPLATES = load_templates()


def test_templates_load_and_placeholders_match_fields():
    import string
    for t in TEMPLATES.values():
        used = {name for block in t.body for _, name, _, _ in string.Formatter().parse(block) if name}
        assert used <= set(t.field_names) | {"today"}, t.id


def test_parse_date_accepts_common_formats():
    assert str(parse_date("2026-08-25")) == "2026-08-25"
    assert str(parse_date("25/08/2026")) == "2026-08-25"
    assert str(parse_date("August 25, 2026")) == "2026-08-25"
    assert parse_date("next tuesday") is None


def test_check_fields_reports_missing_and_bad_values():
    t = TEMPLATES["offer_letter"]
    values, missing, errors = steps.check_fields(t, {"candidate_name": "Ali", "hr_contact_email": "nope",
                                                     "start_date": "soon"})
    assert values == {"candidate_name": "Ali"}
    assert "hr_contact_email" in errors and "start_date" in errors
    assert "company_name" in missing


def test_extract_ignores_unknown_fields(fake_llm):
    llm = fake_llm("nda", [{"party_a": "Acme", "favourite_colour": "blue"}])
    assert steps.extract_fields(llm, TEMPLATES["nda"], ["NDA with Acme"]) == {"party_a": "Acme"}


def test_pick_template_rejects_unknown_id(fake_llm):
    assert steps.pick_template(fake_llm("lease_agreement", []), "rent my flat", TEMPLATES) is None


def test_render_fills_every_placeholder(tmp_path):
    t = TEMPLATES["experience_letter"]
    values = {n: f"<{n}>" for n in t.field_names}
    path = render_docx(t, values, tmp_path / "letter.docx")
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "<employee_name>" in text and "{" not in text
