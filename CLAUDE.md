# Product Desk

This is a **product leadership workspace** — a collection of AI-powered skills, frameworks, and templates that help a senior product manager work faster and decide better.

## What This Repo Is

Product Desk is NOT a software project. It's a working desk for product work: reviewing RFCs, co-authoring documents, estimating impact, stress-testing strategy, and running data analyses. Think of it as a toolkit where each folder serves a specific purpose in the product management workflow.

## Project Structure

```
.claude/skills/       → Claude Code skills (review-rfc, doc-coauthoring)
frameworks/           → Reusable evaluation and strategy frameworks
templates/            → Document templates (status reports, presentations)
best-practices/       → Product management guidance and methods
reviews/              → Archive of past RFC/PRD reviews
```

## Key Skills

### `/review-rfc` — RFC Review as Director of Product
Reviews RFCs across 7 structured dimensions (Problem Clarity, Solution Soundness, Evidence & Validation, Success Metrics, Business Impact, Strategic Fit, Execution Realism). Produces a scored verdict: Approved, Revise & Resubmit, or Not Ready. See `frameworks/dop-review-framework.md` for the full rubric.

### `/doc-coauthoring` — Structured Document Co-Authoring
Three-stage workflow (Context Gathering → Refinement & Structure → Reader Testing) for writing proposals, specs, decision docs, and similar structured content.

## Core Frameworks

- **DOP Review Framework** (`frameworks/dop-review-framework.md`) — 7-dimension scoring rubric for evaluating product proposals
- **Impact Estimation** (`frameworks/impact-estimation-framework.md`) — Three-scenario ROI modeling with the formula: `Impact = Users Affected × Current Rate × Expected Lift × Value per Action`
- **Rumelt Strategy Kernel** (`frameworks/rumelt-strategy-kernel.md`) — Strategic analysis framework
- **Devil's Advocate** (`best-practices/devils-advocate-strategy.md`) — Method for stress-testing decisions

## How to Work Here

- **Be direct and rigorous.** This workspace values incisive feedback and structured thinking over vague encouragement. Never rubber-stamp mediocre work.
- **Use the frameworks.** When reviewing documents or estimating impact, always apply the relevant framework rather than giving ad-hoc opinions.
- **Lean on existing skills.** Before building something new, check if there's already a skill or framework that covers the need.
- **Output should be actionable.** Every review, analysis, or document produced should end with clear next steps or a concrete recommendation.

## Conventions

- Frameworks live in `frameworks/`, templates in `templates/`, best practices in `best-practices/`
- Skills for Claude Code go in `.claude/skills/<skill-name>/SKILL.md`
- Past reviews are archived in `reviews/`
