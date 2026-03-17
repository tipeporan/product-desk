# Product Desk

Skills to help product managers work smarter with AI. Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Available Tools

### DoP RFC Review

A **Director of Product** that reviews your RFCs with the rigor of a senior product leader. It evaluates documents across seven dimensions — Problem Clarity, Solution Soundness, Evidence & Validation, Success Metrics, Business Impact, Strategic Fit, and Execution Realism — and produces a structured scorecard with actionable feedback.

You can provide your RFC in whichever way works best for you:

1. **Google Doc URL** — share a link like `https://docs.google.com/document/d/...` (requires [Google Docs MCP server](https://github.com/anthropics/claude-code) configured)
2. **Local file path** — point to a file on disk, e.g. `/path/to/rfc.md`
3. **Paste the content** — copy and paste the RFC text directly

Available as:

- **Claude Code Skill** — invoke with `/review-rfc` inside Claude Code
---

## Installation

### Claude Code Skill

1. Clone this repository:

```bash
git clone https://github.com/tipeporan/product-desk.git
cd product-desk
```

2. That's it. Open Claude Code in the repo directory and the skill is ready:

```
/review-rfc <paste your RFC content here>
```

The skill fetches its review framework from GitHub at runtime, so no additional files are needed locally.

> **Tip:** To pre-approve the skill and avoid permission prompts, add this to your `.claude/settings.local.json`:
>
> ```json
> {
>   "permissions": {
>     "allow": [
>       "Skill(review-rfc)",
>       "WebFetch(domain:raw.githubusercontent.com)"
>     ]
>   }
> }
> ```

### Cursor

1. Download the [`review-rfc.mdc`](cursor-rules/review-rfc.mdc) file from this repository.

2. Copy it into your project's `.cursor/rules/` directory:

```bash
# Create the directory if it doesn't exist
mkdir -p .cursor/rules

# Copy the rule file
cp path/to/review-rfc.mdc .cursor/rules/
```

3. In Cursor chat, reference `@review-rfc` and paste your RFC content.

---

## Repository Structure

```
product-desk/
├── .claude/skills/review-rfc/   # Claude Code skill definition
├── cursor-rules/                # Ready-to-use Cursor rule files
├── frameworks/                  # Review frameworks and scoring rubrics
├── templates/                   # Document templates
└── best-practices/              # Product management best practices
```

