import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y"]


@dataclass
class Template:
    id: str
    title: str
    description: str
    fields: list[dict]
    body: list[str]

    @property
    def field_names(self):
        return [f["name"] for f in self.fields]


def load_templates(folder: Path = TEMPLATE_DIR) -> dict[str, Template]:
    out = {}
    for p in sorted(folder.glob("*.json")):
        t = Template(**json.loads(p.read_text(encoding="utf-8")))
        out[t.id] = t
    return out


def parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def clean_value(field: dict, value) -> tuple[str | None, str | None]:
    """Return (normalised value, error message)."""
    if value is None or str(value).strip() == "":
        return None, None
    value = str(value).strip()
    kind = field.get("type", "text")
    if kind == "date":
        d = parse_date(value)
        if d is None:
            return None, f"couldn't read '{value}' as a date"
        return d.strftime("%d %B %Y"), None
    if kind == "number":
        try:
            n = float(value)
        except ValueError:
            return None, f"'{value}' is not a number"
        return (str(int(n)) if n.is_integer() else str(n)), None
    if kind == "email" and not EMAIL_RE.match(value):
        return None, f"'{value}' doesn't look like an email address"
    return value, None


def render_docx(template: Template, values: dict, out_path: Path) -> Path:
    data = dict(values, today=date.today().strftime("%d %B %Y"))
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(template.title, level=1)
    for block in template.body:
        doc.add_paragraph(block.format(**data))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path
