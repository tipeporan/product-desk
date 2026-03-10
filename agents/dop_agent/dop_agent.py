#!/usr/bin/env python3
"""
Director of Product Review Agent

Fetches an RFC or PRD from a Google Doc, pulls related Jira context,
and produces a structured review as a seasoned Director of Product.

Usage:
    python dop_agent.py <google-doc-url-or-id>

Environment variables required:
    ANTHROPIC_API_KEY           Your Anthropic API key
    ATLASSIAN_BASE_URL          e.g. https://yourcompany.atlassian.net
    ATLASSIAN_EMAIL             Your Atlassian account email
    ATLASSIAN_API_TOKEN         Your Atlassian API token

Google auth files (in the same folder as this script):
    credentials.json            OAuth2 client credentials from Google Cloud Console
    token.json                  Auto-created on first run after browser auth

To get credentials.json:
    1. Go to https://console.cloud.google.com/
    2. Create a project → Enable "Google Docs API"
    3. APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop app)
    4. Download the JSON and save as credentials.json next to this script
"""

import argparse
import json
import os
import re
import sys

import anthropic
import requests
from requests.auth import HTTPBasicAuth

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Atlassian credentials ──────────────────────────────────────────────────────
ATLASSIAN_BASE_URL = os.environ.get("ATLASSIAN_BASE_URL", "").rstrip("/")
ATLASSIAN_EMAIL = os.environ.get("ATLASSIAN_EMAIL", "")
ATLASSIAN_API_TOKEN = os.environ.get("ATLASSIAN_API_TOKEN", "")

# ── Google auth ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GOOGLE_SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]
_CREDENTIALS_FILE = os.path.join(_SCRIPT_DIR, "credentials.json")
_TOKEN_FILE = os.path.join(_SCRIPT_DIR, "token.json")

client = anthropic.Anthropic()

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Alex, a seasoned Director of Product with 12+ years of experience \
at high-growth tech companies. You are known for being direct, incisive, and deeply \
strategic — you push PMs to think rigorously and raise the bar on every document they write.

When reviewing a PRD or RFC you evaluate it across seven lenses:

1. **Problem Clarity** — Is the problem specific, well-evidenced, and quantified? \
Vague problem statements are a red flag.
2. **Solution Soundness** — Is the proposed solution the right one? Have alternatives \
been considered and dismissed with good reasoning?
3. **Evidence & Validation** — Is there data, research, or analogous cases that give \
confidence this will work? Assumptions should be explicit and labeled.
4. **Success Metrics** — Are outcomes measurable? Is there a primary KPI with a clear \
target, leading indicators, and guardrails?
5. **Business Impact** — Is there a three-scenario model (pessimistic / realistic / \
optimistic)? Are key assumptions laid out using the formula: \
Impact = Users Affected × Current Rate × Expected Lift × Value per Action?
6. **Strategic Fit** — Does this clearly connect to company or product strategy? \
Does it leverage existing strengths?
7. **Execution Realism** — Is the scope right for the team and timeline? Are the top \
risks identified with credible mitigations?

## Your Review Format

Always produce a review with this exact structure:

---

## Director of Product Review

**Document:** [title]
**Author:** [if found in the document]
**Reviewed by:** Alex (Director of Product)
**Verdict:** ✅ Approved | ⚠️ Revise & Resubmit | ❌ Not Ready

---

### Scorecard

| Dimension | Score (1–5) | Quick Take |
|-----------|-------------|------------|
| Problem Clarity | X/5 | [one line] |
| Solution Soundness | X/5 | [one line] |
| Evidence & Validation | X/5 | [one line] |
| Success Metrics | X/5 | [one line] |
| Business Impact | X/5 | [one line] |
| Strategic Fit | X/5 | [one line] |
| Execution Realism | X/5 | [one line] |
| **Overall** | **X/5** | |

---

### Key Questions Before This Can Move Forward

1. [Most critical unanswered question]
2. [Second most critical question]
3. [Up to 5 questions total]

---

### Detailed Feedback

#### Problem
[2–4 sentences of specific, direct feedback. Call out what's missing or weak. \
Acknowledge what's strong.]

#### Solution & Alternatives
[2–4 sentences]

#### Evidence
[2–4 sentences]

#### Metrics
[2–4 sentences]

#### Business Impact
[2–4 sentences — specifically comment on whether the three-scenario model is present \
and whether the formula Impact = Users × Rate × Lift × Value is applied]

#### Strategic Fit
[2–4 sentences]

#### Execution & Risks
[2–4 sentences]

---

### What I'd Change Before Resubmitting

- [ ] [Most important change, specific and actionable]
- [ ] [Second change]
- [ ] [Up to 5 items max]

---

## Tone Guidelines
- Be direct and honest — do not soften critical feedback with excessive praise
- Be specific — point to exact sections, missing data, or weak arguments
- Be constructive — frame problems as things to fix, not personal failures
- Do not rubber-stamp mediocre work — if it needs to be revised, say so clearly
"""

# ── Tool definitions ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "get_google_doc",
        "description": (
            "Fetch a Google Doc by its URL or document ID. "
            "Returns the document title and full plain-text content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_ref": {
                    "type": "string",
                    "description": "Google Doc URL or document ID.",
                }
            },
            "required": ["doc_ref"],
        },
    },
    {
        "name": "search_confluence",
        "description": (
            "Search Confluence for pages related to the RFC/PRD being reviewed "
            "(e.g. strategy docs, prior PRDs, OKRs, design docs)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text."},
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 5).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_jira_issue",
        "description": (
            "Fetch a Jira issue by its key (e.g. PROJ-123) to understand linked "
            "tickets, acceptance criteria, or prior decisions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "The Jira issue key, e.g. PROJ-123.",
                }
            },
            "required": ["issue_key"],
        },
    },
    {
        "name": "search_jira_issues",
        "description": (
            "Search Jira for issues related to the RFC/PRD "
            "(e.g. linked epics, past initiatives in the same area)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": (
                        "JQL query string, e.g. "
                        "'project = PROJ AND labels = onboarding ORDER BY created DESC'."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10).",
                },
            },
            "required": ["jql"],
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────────────

# ── Google Docs ────────────────────────────────────────────────────────────────

def _get_google_docs_service():
    """Return an authenticated Google Docs API service, running OAuth if needed."""
    creds = None
    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, _GOOGLE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Google credentials not found at {_CREDENTIALS_FILE}.\n"
                    "Download OAuth2 credentials from Google Cloud Console and "
                    "save as credentials.json next to this script."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_FILE, _GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("docs", "v1", credentials=creds)


def _extract_doc_id(url_or_id: str) -> str:
    """Extract Google Doc ID from a URL, or return as-is."""
    m = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url_or_id)
    if m:
        return m.group(1)
    return url_or_id.strip()


def _doc_content_to_text(doc: dict) -> str:
    """Convert the Google Docs API document body to plain text."""
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        # Paragraph
        if "paragraph" in element:
            para_text = ""
            for elem in element["paragraph"].get("elements", []):
                if "textRun" in elem:
                    para_text += elem["textRun"].get("content", "")
            text_parts.append(para_text)
        # Table
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                row_parts = []
                for cell in row.get("tableCells", []):
                    cell_text = ""
                    for cell_elem in cell.get("content", []):
                        if "paragraph" in cell_elem:
                            for e in cell_elem["paragraph"].get("elements", []):
                                if "textRun" in e:
                                    cell_text += e["textRun"].get("content", "")
                    row_parts.append(cell_text.strip())
                text_parts.append(" | ".join(row_parts))
    return "".join(text_parts)


def get_google_doc(doc_ref: str) -> dict:
    doc_id = _extract_doc_id(doc_ref)
    try:
        service = _get_google_docs_service()
        doc = service.documents().get(documentId=doc_id).execute()
    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Google Docs API error: {e}"}
    content = _doc_content_to_text(doc)
    return {
        "doc_id": doc_id,
        "title": doc.get("title", "Untitled"),
        "url": f"https://docs.google.com/document/d/{doc_id}",
        "content": content[:10000],  # cap to keep within context budget
    }


def search_confluence(query: str, limit: int = 5) -> dict:
    url = f"{ATLASSIAN_BASE_URL}/wiki/rest/api/content/search"
    params = {
        "cql": f'text ~ "{query}" AND type = page',
        "limit": limit,
    }
    resp = requests.get(url, params=params, auth=_atlassian_auth(), timeout=15)
    if not resp.ok:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    results = resp.json().get("results", [])
    return {
        "pages": [
            {
                "id": p["id"],
                "title": p["title"],
                "url": f"{ATLASSIAN_BASE_URL}/wiki{p.get('_links', {}).get('webui', '')}",
            }
            for p in results
        ]
    }


def get_jira_issue(issue_key: str) -> dict:
    url = f"{ATLASSIAN_BASE_URL}/rest/api/3/issue/{issue_key}"
    params = {
        "fields": "summary,description,status,priority,labels,issuetype,assignee"
    }
    resp = requests.get(url, params=params, auth=_atlassian_auth(), timeout=15)
    if not resp.ok:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    data = resp.json()
    fields = data.get("fields", {})
    # Extract plain text from Atlassian Document Format description
    desc = ""
    if fields.get("description"):
        for block in fields["description"].get("content", []):
            for inline in block.get("content", []):
                if inline.get("type") == "text":
                    desc += inline.get("text", "")
    return {
        "key": data.get("key"),
        "summary": fields.get("summary"),
        "status": fields.get("status", {}).get("name"),
        "type": fields.get("issuetype", {}).get("name"),
        "priority": fields.get("priority", {}).get("name"),
        "labels": fields.get("labels", []),
        "description": desc[:2000],
    }


def search_jira_issues(jql: str, limit: int = 10) -> dict:
    url = f"{ATLASSIAN_BASE_URL}/rest/api/3/search"
    payload = {
        "jql": jql,
        "maxResults": limit,
        "fields": ["summary", "status", "issuetype", "priority", "labels"],
    }
    resp = requests.post(
        url, json=payload, auth=_atlassian_auth(), timeout=15
    )
    if not resp.ok:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    issues = resp.json().get("issues", [])
    return {
        "issues": [
            {
                "key": i["key"],
                "summary": i["fields"].get("summary"),
                "status": i["fields"].get("status", {}).get("name"),
                "type": i["fields"].get("issuetype", {}).get("name"),
            }
            for i in issues
        ]
    }


def _dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "get_google_doc":
        return get_google_doc(tool_input["doc_ref"])
    if tool_name == "search_confluence":
        return search_confluence(tool_input["query"], tool_input.get("limit", 5))
    if tool_name == "get_jira_issue":
        return get_jira_issue(tool_input["issue_key"])
    if tool_name == "search_jira_issues":
        return search_jira_issues(tool_input["jql"], tool_input.get("limit", 10))
    return {"error": f"Unknown tool: {tool_name}"}


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_review(doc_ref: str) -> None:
    """Run the Director of Product review for the given Google Doc."""
    if not all([ATLASSIAN_BASE_URL, ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN]):
        print(
            "❌  Missing Atlassian credentials.\n"
            "    Set ATLASSIAN_BASE_URL, ATLASSIAN_EMAIL, and ATLASSIAN_API_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"🔍  Reviewing: {doc_ref}\n")

    messages = [
        {
            "role": "user",
            "content": (
                f"Please review the following PRD or RFC from Google Docs. "
                f"The document reference is: {doc_ref}\n\n"
                "Start by fetching the document content. Then search for up to 3 pieces "
                "of relevant context (related strategy docs, OKRs, past PRDs, or "
                "linked Jira epics) that would make your review more informed. "
                "Finally, produce your full Director of Product review."
            ),
        }
    ]

    # Agentic loop with streaming
    while True:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            for event in stream:
                # Stream text deltas to stdout as they arrive
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    print(event.delta.text, end="", flush=True)

                # Show tool calls in progress
                elif (
                    event.type == "content_block_start"
                    and event.content_block.type == "tool_use"
                ):
                    print(
                        f"\n  → {event.content_block.name}(",
                        end="",
                        flush=True,
                    )
                elif (
                    event.type == "content_block_stop"
                    and hasattr(event, "index")
                ):
                    pass  # closing paren printed after dispatch

            response = stream.get_final_message()

        if response.stop_reason == "end_turn":
            print()  # final newline
            break

        if response.stop_reason == "tool_use":
            # Append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    input_preview = json.dumps(block.input, ensure_ascii=False)[:100]
                    print(f"\n  → {block.name}({input_preview})")
                    result = _dispatch_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason — bail out
            print(f"\n⚠️  Unexpected stop reason: {response.stop_reason}", file=sys.stderr)
            break


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Director of Product Review Agent — reviews a Google Doc PRD/RFC"
    )
    parser.add_argument(
        "doc",
        help="Google Doc URL or document ID to review",
    )
    args = parser.parse_args()
    run_review(args.doc)


if __name__ == "__main__":
    main()
