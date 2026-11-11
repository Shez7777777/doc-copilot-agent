"""LangGraph wiring. The graph pauses (interrupt) whenever it needs the user:
to ask for missing fields, and once more to confirm before generating the file.

    pick_template -> extract -> check --missing--> ask ----┐
                        ^         \--complete--> review ---┼--> render
                        └──────────────────────────────────┘
"""
import re
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import steps
from .templates import load_templates, render_docx

YES = re.compile(r"^\s*(y|yes|yep|ok|okay|looks good|go ahead|confirm(ed)?)\b", re.I)


class DocState(TypedDict, total=False):
    conversation: list[str]
    template_id: str | None
    raw: dict
    values: dict
    missing: list[str]
    errors: dict
    output_path: str
    message: str


def build_graph(llm, out_dir="output", templates=None):
    templates = templates or load_templates()

    def pick(state: DocState):
        tid = steps.pick_template(llm, state["conversation"][0], templates)
        if tid is None:
            names = ", ".join(t.title for t in templates.values())
            return {"template_id": None, "message": f"I can only draft these right now: {names}."}
        return {"template_id": tid, "raw": {}}

    def extract(state: DocState):
        t = templates[state["template_id"]]
        found = steps.extract_fields(llm, t, state["conversation"])
        return {"raw": {**state.get("raw", {}), **found}}

    def check(state: DocState):
        values, missing, errors = steps.check_fields(templates[state["template_id"]], state["raw"])
        return {"values": values, "missing": missing, "errors": errors}

    def ask(state: DocState):
        t = templates[state["template_id"]]
        answer = interrupt({"question": steps.follow_up_question(t, state["missing"], state["errors"])})
        return {"conversation": state["conversation"] + [answer]}

    def review(state: DocState):
        t = templates[state["template_id"]]
        answer = interrupt({"question": steps.summary(t, state["values"])})
        if YES.match(answer):
            return {"message": "confirmed"}
        return {"conversation": state["conversation"] + [answer], "message": "changes requested"}

    def render(state: DocState):
        t = templates[state["template_id"]]
        name = state["values"].get("employee_name") or state["values"].get("candidate_name") or state["values"].get("party_b", "")
        slug = re.sub(r"[^a-z0-9]+", "_", f"{t.id}_{name}".lower()).strip("_")
        path = render_docx(t, state["values"], Path(out_dir) / f"{slug}.docx")
        return {"output_path": str(path), "message": f"Done, saved to {path}"}

    g = StateGraph(DocState)
    for name, fn in [("pick", pick), ("extract", extract), ("check", check),
                     ("ask", ask), ("review", review), ("render", render)]:
        g.add_node(name, fn)
    g.add_edge(START, "pick")
    g.add_conditional_edges("pick", lambda s: "extract" if s.get("template_id") else END)
    g.add_edge("extract", "check")
    g.add_conditional_edges("check", lambda s: "ask" if s["missing"] else "review")
    g.add_edge("ask", "extract")
    g.add_conditional_edges("review", lambda s: "render" if s["message"] == "confirmed" else "extract")
    g.add_edge("render", END)
    return g.compile(checkpointer=InMemorySaver())
