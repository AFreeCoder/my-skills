# Release Scope Audit

Read this when the release-context audit finds unapproved or unrelated commits in `<remote>/<release-branch>..candidate`, commits inherited from a local release branch, or a dirty worktree.

## Inherited Commits

If the candidate inherited unpublished commits from a local release branch, every inherited commit is part of the release candidate. The full range is valid only when those commits were explicitly approved before the release audit as one named release batch. Otherwise the candidate must be rebuilt. Never hide inherited commits behind the newest feature name, and never grant retroactive batch approval during the audit.

## Common Rationalizations

| Rationalization | Why it fails |
|---|---|
| "Local main is newer" | Newness is not deployment authorization; audit from the fetched remote baseline. |
| "Those inherited commits will ship soon anyway" | They remain out of scope unless already approved in a named release batch. |
| "All tests pass, so approve the mixed range now" | Tests do not define release authorization. |
| "The dirty files will not be staged" | Release evidence must come from a clean worktree to be auditable. |

## Rebuilding a Clean Candidate

1. Create a clean release worktree from the fetched remote release baseline.
2. Bring in only changes that have pre-existing approval evidence.
3. Rerun every required check there.
4. Continue the release workflow with the rebuilt candidate. Never push the original mixed-scope branch as-is.

## Dirty Worktree with Approved Scope

If the history scope is approved but the current worktree is dirty, perform release verification in the same kind of clean release worktree so the release evidence stays isolated and auditable. Preserve uncommitted files; they never enter the release candidate and are never counted as released.
