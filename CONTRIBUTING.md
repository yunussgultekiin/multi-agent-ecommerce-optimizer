# GitHub Workflow Guide — BİRİNCİYİZ Team

> BTK Hackathon 2026 | AI-Driven E-Commerce Intelligence Platform

---

## Branch Strategy

```
main   →  Demo / presentation. Must always be in a working state.
dev    →  Daily development. Everyone pushes here.
```

### Rules

- All development happens on the `dev` branch
- Direct pushes to `main` are **not allowed**
- Merges to `main` are done only before demos/milestones, by the project lead
- Always run `git pull` before pushing to `dev`

```bash
# Start of day
git checkout dev
git pull origin dev

# End of day
git add .
git commit -m "feat(api): add rate limiting to quota service"
git push origin dev
```

---

## Commit Format — Conventional Commits

The jury will review the commit history. Every commit must be meaningful.

```
<type>(<scope>): <what you did>
```

### Type Reference

| Type | When to use |
|---|---|
| `feat` | New feature added |
| `fix` | Bug fixed |
| `refactor` | Code rewritten without behaviour change |
| `test` | Test added or updated |
| `docs` | Documentation updated |
| `chore` | Dependency, config, or environment change |
| `ci` | GitHub Actions / deploy change |
| `perf` | Performance improvement |

### Scope Reference (Project-Specific)

| Scope | Maps to |
|---|---|
| `gateway` | FastAPI Gateway |
| `auth` | Auth & Tenant Service |
| `quota` | Quota Service |
| `task` | Task Service |
| `broker` | Redis + Celery Async Event Broker |
| `agent` | LangChain AI Agent Controller |
| `llm` | LLM Reasoning Engine (Gemini) |
| `scraper` | Web Scraper — Jina AI Reader |
| `vision` | Vision Tool — Gemini Vision |
| `sentiment` | Sentiment Tool |
| `scoring` | Scoring Engine |
| `rag` | RAG Context — ChromaDB |
| `ml` | Competitor ML Prediction Model |
| `db` | PostgreSQL / database layer |
| `cache` | Redis caching layer |
| `frontend` | Next.js Web Client |
| `ci` | GitHub Actions / Heroku deploy |

### Examples

```bash
# Good commits
git commit -m "feat(agent): integrate ReAct executor with scraper tool"
git commit -m "fix(quota): resolve rate limit not resetting after TTL"
git commit -m "feat(rag): add ChromaDB collection for competitor embeddings"
git commit -m "refactor(gateway): extract auth middleware from route handler"
git commit -m "feat(scoring): implement deterministic scoring engine logic"
git commit -m "fix(broker): resolve celery task not retrying on timeout"
git commit -m "chore(deps): upgrade langchain to 0.2.0"
git commit -m "ci: add heroku deployment trigger on main push"
git commit -m "feat(frontend): add analysis result dashboard component"
git commit -m "feat(llm): add gemini 1.5 pro prompt template for product analysis"

# Bad commits — avoid these
git commit -m "fixed"
git commit -m "update"
git commit -m "final version"
git commit -m "aaa"
```

---

## Merging to Main

Before a demo or milestone, the project lead runs:

```bash
git checkout main
git pull origin main
git merge dev
git push origin main
```

**When to merge:**
- Before a presentation / demo
- When a significant module is complete
- When everyone has confirmed they are ready

---

## Quick Summary

```
work on dev  →  write meaningful commits  →  push to dev
                                                   ↓
                                        merge to main before demo
```

1. Start the day with `git pull`
2. Use `type(scope): description` format for all commit messages
3. Never commit API keys or secrets
4. `main` must always be in a working state
5. If you hit a conflict, flag it — resolve it together