---
name: commit
description: |
  Guided git-commit workflow with approval gates and conventional-commit enforcement. Write commit messages terse and exact. Conventional Commits format. No fluff. Why over what.
  TRIGGER when: user asks to commit, save work, create a commit, "save these changes",
  or after completing a logical unit of work and wanting it captured.
  SKIP for: push, amend, rebase, force-push, or branch deletion — those are separate operations.
model: sonnet
---

# Commit

Write commit messages terse and exact. Conventional Commits format. No fluff. Why over what.

## When to Use

Invoke when:
- User asks to commit, save work, or create a commit
- User says "commit this", "save these changes"
- After completing a logical unit of work

Do NOT invoke for git push, amend, or rebase.

## Workflow

### Step 0: Branch check

```bash
git branch --show-current
```

If on `main`, create a new branch before committing:
```bash
git checkout -b <type>/<short-description>
```

Branch naming: `feat/add-summarizer`, `fix/schema-validation`, `chore/update-deps`, `docs/update-readme`.

### Step 1: Check status

```bash
git status
git diff --stat
```

If no changes, inform user and stop.

### Step 2: Review changes

Present summary:
> Changes in X files: Y insertions, Z deletions

Understand what changed before proceeding.

### Step 3: Determine commit type

| Type | Use for |
|------|---------|
| `feat:` | New features, new services |
| `fix:` | Bug fixes |
| `docs:` | Documentation only |
| `chore:` | Tooling, dependencies, config |
| `refactor:` | Code restructuring |
| `test:` | Tests |

### Step 4: Draft commit message

Format: `<type>(<scope>): <imperative summary> — <scope> optional`

Rules:
- Lowercase, no period, imperative mood
- ≤50 chars when possible, hard cap 72
- No trailing period
- Body optional — explain WHY, not WHAT
- Match project convention for capitalization after the colon

### Step 5: Present commit plan

> **Proposed commit:**
> ```
> feat: add summarizer agent
> ```
> **Files:** list of files
>
> Ready to commit?

Wait for user approval before proceeding.

### Step 6: Stage and commit

```bash
git add <specific-files>
git commit -m "<type>: <subject>"
```

Rules:
- **NEVER use Co-Authored-By** — simple commit format only
- **NEVER use --amend or --no-verify**
- **NEVER use "Generated with Claude Code" or any AI attribution**
- **Never use Emoji**
- Stage specific files, not `git add .`

Confirm: `Committed: <hash> - "<message>"`

### Step 7: Suggest next steps

> Next: `git push`, continue working, or `gh pr create`

Do NOT push automatically.

## Anti-patterns

- Commit without user approval
- Use Co-Authored-By or AI attribution
- Vague messages ("update", "fix", "changes")
- Stage all files without reviewing
- Amend, force push, or skip hooks
