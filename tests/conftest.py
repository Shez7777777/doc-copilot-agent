import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeLLM:
    """Returns canned JSON. `extractions` is consumed one per extract call."""

    def __init__(self, template_id, extractions):
        self.template_id = template_id
        self.extractions = list(extractions)

    def json(self, system, user):
        if "pick the right document template" in system:
            return {"template_id": self.template_id, "why": "test"}
        return {"fields": self.extractions.pop(0) if self.extractions else {}}


@pytest.fixture
def fake_llm():
    return FakeLLM
