# Doc Copilot

A LangGraph agent that drafts business documents by talking to you. You say what you
need ("experience letter for Sara, data analyst, Jan 2025 to June 2026"), it figures out
which template that is, pulls out the details you already gave, asks only for what's
missing, shows you a summary to confirm, and then writes a `.docx`.

I built something similar at work with Copilot Studio and Power Automate. This is my own
version in plain Python so I could control the flow and test it properly.

```
pick template ─► extract fields ─► validate ──missing──► ask user (pause) ─┐
                      ▲                 │                                    │
                      │                 └─complete─► confirm (pause) ─yes─► write .docx
                      └────────────── answers / corrections ◄───────────────┘
```

## How it works

- **Graph, not one big prompt.** Each step is a LangGraph node. The two places where the
  user has to answer use `interrupt()`, and the state is kept by a checkpointer, so the
  conversation can pause and resume (in the terminal, Streamlit, or behind an API).
- **The LLM only does language work.** It picks the template and extracts values as JSON.
  Validation is normal code: dates are parsed and normalised, numbers and emails checked.
  When something is invalid the follow-up question says why.
- **Corrections loop back.** At the confirmation step you can just type "the title should be
  Senior Data Analyst" and it re-extracts, re-validates and shows the summary again.
- **Templates are JSON.** Fields (name, label, type) plus body paragraphs with
  `{placeholders}`. A test checks every placeholder in a template has a matching field.
- Works with any OpenAI-compatible model. I use Groq with `llama-3.3-70b-versatile` in JSON mode.

Templates included: experience letter, job offer letter, mutual NDA. Adding one is a new
file in `templates/`.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env          # add a Groq API key

python -m doccopilot          # chat in the terminal
streamlit run app.py          # or in the browser
pytest -q                     # no API key needed, tests use a fake LLM
```

Example session:

```
What document do you need?
> experience letter for Sara Khan, data analyst at Northwind Labs since 6 Jan 2025

To finish the experience letter I still need:
- Last working day
- Main duties (one or two sentences)
- Name of the person signing
- Title of the person signing

> last day 30 June 2026, she built the weekly sales dashboards. Omar Ali, HR Manager signs

Here's what I'll put in the experience letter:
- Company name: Northwind Labs
- Employee's full name: Sara Khan
...
Reply 'yes' to generate it, or tell me what to change.

> yes
Done, saved to output/experience_letter_sara_khan.docx
```

## Files

```
doccopilot/
  templates.py   load templates, validate values, render .docx
  steps.py       LLM calls (pick, extract) and the deterministic checks/questions
  graph.py       LangGraph state machine with interrupts
  __main__.py    terminal chat
templates/       JSON templates
app.py           Streamlit chat
tests/
```

## Next

- clause library + retrieval, so it can suggest NDA clauses instead of a fixed text
- PDF export
- a small eval set of requests to measure extraction accuracy per model
