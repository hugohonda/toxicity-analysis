---
name: commit
description: |
  Guided git-commit workflow with approval gates and conventional-commit enforcement. Commits land on the current branch (including main when that is the working branch); pushing is an opt-in final step that always requires explicit user approval. Write commit messages terse and exact. Conventional Commits format. No fluff. Why over what.
  TRIGGER when: user asks to commit, save work, create a commit, "save these changes", "commit and push",
  or after completing a logical unit of work and wanting it captured.
  SKIP for: amend, rebase, force-push, or branch deletion — those are separate operations.
model: sonnet
---

# Commit

Write commit messages terse and exact. Conventional Commits format. No fluff. Why over what.

## When to Use

Invoke when:
- User asks to commit, save work, or create a commit
- User says "commit this", "save these changes", "commit and push"
- After completing a logical unit of work

Do NOT invoke for amend, rebase, or force-push.

## Workflow

### Step 0: Branch check

```bash
git branch --show-current
```

Show the current branch as part of the commit plan (Step 5). Commits land on the current branch — including `main` when that is the working branch. Do NOT auto-create a feature branch; if the user wants one, they will say so.

Optional branch naming convention when the user asks for one: `feat/add-summarizer`, `fix/schema-validation`, `chore/update-deps`, `docs/update-readme`.

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

> **Branch:** `<current-branch>`
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

### Step 7: Offer push (with explicit approval)

After the commit lands, offer to push the current branch:

> **Next:** push `<current-branch>` to remote? (yes / no)
>
> If `<current-branch>` is `main`: this publishes directly to the default branch.

If the user says yes:

```bash
git push          # if upstream is set
git push -u origin <current-branch>   # first push of a new branch
```

Rules:
- **NEVER push without explicit user approval** — even if the user said "commit and push" up front, confirm the branch and target before running `git push`.
- **NEVER use `--force` or `--force-with-lease`** unless the user has explicitly asked for it in this turn.
- For `main`, do not require a feature branch, but state plainly that the push goes to the default branch so the user has a chance to redirect.
- If the push is rejected (non-fast-forward, hook failure, etc.), surface the error and stop. Do NOT auto-pull or auto-force.

If the user says no, suggest the alternatives:

> Alternatives: `git push` later, `gh pr create`, or keep iterating locally.

## Anti-patterns

- Commit without user approval
- Push without user approval (even when the user asked for "commit and push" — confirm at the push step)
- Auto-create a feature branch when the user did not ask
- Use Co-Authored-By or AI attribution
- Vague messages ("update", "fix", "changes")
- Stage all files without reviewing
- Amend, force push, or skip hooks
