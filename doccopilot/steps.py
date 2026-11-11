"""The individual steps of the copilot. Kept free of LangGraph so they're easy to test."""
import json
import os

from .templates import Template, clean_value

PICK_PROMPT = """You pick the right document template for a request.
Templates:
{options}

Reply with JSON only: {{"template_id": "<one of the ids above, or none>", "why": "<short reason>"}}"""

EXTRACT_PROMPT = """You fill in fields for a "{title}" from what the user has said.
Fields:
{fields}

Rules:
- Only use information the user actually gave. If a field wasn't mentioned, leave it out.
- Keep the user's wording for names and duties; write dates as YYYY-MM-DD when you can.
- If the user corrects an earlier value, use the newest one.

Reply with JSON only, e.g. {{"fields": {{"field_name": "value"}}}}"""


class JsonLLM:
    """Small wrapper around an OpenAI-compatible endpoint in JSON mode (Groq by default)."""

    def __init__(self, model=None):
        from openai import OpenAI
        self.client = OpenAI(base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                             api_key=os.getenv("LLM_API_KEY"))
        self.model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    def json(self, system: str, user: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return json.loads(resp.choices[0].message.content)


def pick_template(llm, request: str, templates: dict[str, Template]) -> str | None:
    options = "\n".join(f"- {t.id}: {t.title}. {t.description}" for t in templates.values())
    out = llm.json(PICK_PROMPT.format(options=options), request)
    tid = out.get("template_id")
    return tid if tid in templates else None


def extract_fields(llm, template: Template, conversation: list[str]) -> dict:
    fields = "\n".join(f"- {f['name']} ({f['type']}): {f['label']}" for f in template.fields)
    user = "\n".join(f"User: {m}" for m in conversation)
    out = llm.json(EXTRACT_PROMPT.format(title=template.title, fields=fields), user)
    raw = out.get("fields", {}) if isinstance(out, dict) else {}
    return {k: v for k, v in raw.items() if k in template.field_names}


def check_fields(template: Template, raw: dict) -> tuple[dict, list[str], dict]:
    """Validate raw values. Returns (clean values, missing field names, errors by field)."""
    values, missing, errors = {}, [], {}
    for f in template.fields:
        value, err = clean_value(f, raw.get(f["name"]))
        if err:
            errors[f["name"]] = err
        if value is None:
            missing.append(f["name"])
        else:
            values[f["name"]] = value
    return values, missing, errors


def follow_up_question(template: Template, missing: list[str], errors: dict) -> str:
    labels = {f["name"]: f["label"] for f in template.fields}
    lines = [f"- {labels[n]}" + (f" ({errors[n]})" if n in errors else "") for n in missing]
    return f"To finish the {template.title.lower()} I still need:\n" + "\n".join(lines)


def summary(template: Template, values: dict) -> str:
    labels = {f["name"]: f["label"] for f in template.fields}
    rows = "\n".join(f"- {labels[k]}: {values[k]}" for k in template.field_names)
    return f"Here's what I'll put in the {template.title.lower()}:\n{rows}\n\nReply 'yes' to generate it, or tell me what to change."
