# Plan: Use Web VS Code as the Git Diff Experience in V1

Context
- V1 (agent-sdk) should not re-implement a bespoke "Changes" viewer. We already run OpenVSCode Server in the backend; its built-in Git SCM and diff editor are superior and allow inline edits.
- In V1 we will not carry forward the old "Changes" tab. VS Code web becomes the diff experience.
- Verification: The runtime bundles Git-related extensions (git, git-base, github). We verified presence under `/openhands/.openvscode-server/extensions`.

Goals
- Replace "Changes" with an embedded web VS Code diff experience.
- Make the diff view immediate and user-friendly (no hunt-and-click in the Explorer).
- Keep implementation simple and incremental, with clear fallbacks only if VS Code is disabled entirely.

Non-Goals
- Do not re-create a custom diff viewer in the web FE.
- No fallback to a legacy "Changes" tab in V1 when VS Code is unavailable.

High-Level Design
1) Backend: web VS Code service (done)
   - Endpoints: `/api/vscode/status`, `/api/vscode/url` (returns tokenized URL)
   - Config: `vscode_port` (implemented) and URL-encoded folder parameter (implemented)
   - Start on server startup; stop on shutdown

2) Frontend (placeholder until full V1 FE exists)
   - Minimal demo: either
     - Add a redirect endpoint `/vscode` returning the tokenized URL (so users can open VS Code directly), or
     - Serve a tiny static page that calls `/api/vscode/url` and embeds the URL in an iframe.

3) "Immediate diff" UX inside VS Code
   - Provide a tiny VS Code extension (OpenVSCode compatible) that, on startup:
     - Obtains the Git extension API (vscode.git)
     - Enumerates changed files (working tree and/or index)
     - Opens `vscode.diff` editors for a limited number (e.g., first 10)
     - Focuses the SCM view (`workbench.view.scm`) and selects the first diff
   - Control via `.vscode/openhands.json`, e.g. `{ "showDiffOnStartup": true, "limit": 10 }`
   - Future: support toggling HEAD vs index comparisons

4) Packaging the extension
   - Include the extension in the OpenVSCode Server environment (e.g., under `/openhands/.openvscode-server/extensions` or using `--extensions-dir`).
   - Keep it minimal and isolated; no external services needed.

5) Security and embedding
   - Continue using tokenized URL (`?tkn=...`) and configured port.
   - When embedding in an iframe (future FE), ensure CSP/headers permit framing from our FE host.

User Flow
- User opens the "Diff" tab in the app (V1 FE) which embeds/switches to the web VS Code instance.
- VS Code loads, extension activates, SCM focuses and diff editors open automatically.
- User reviews and edits inline; staging/committing handled by VS Code’s SCM.

Phased Implementation
- Phase 1: Backend ready + simple demo
  - [x] `vscode_port` config + folder URL-encoding
  - [x] Add static HTML demo that embeds/opens the VS Code URL (see examples/25_vscode_diff_demo)
- Phase 2: Auto-open diffs
  - [ ] Create minimal `openhands-diff` extension
  - [ ] Agent-server writes `.vscode/openhands.json` to signal diff mode when appropriate
  - [ ] Extension opens diffs on startup, focuses SCM, caps number of editors
- Phase 3: Polish
  - [ ] Configurable comparison target (HEAD vs index)
  - [ ] Multi-repo selection if needed
  - [ ] Optional in-editor "diff dashboard" webview that still launches native diff editors

Activation, Triggers, and Live Updates
- Extension activation (once per window/session):
  - activationEvents: ["onStartupFinished", "workspaceContains:**/.git", "onExtension:vscode.git" (optional)].
  - These only load the extension; they do not re-fire repeatedly. After activation, the extension stays active.
- Re-triggering the "show diffs now" behavior:
  - The extension sets a file watcher on `**/.vscode/openhands.json`.
  - Agent-server writes/updates this JSON when the app navigates to the Diff experience, including a fresh `nonce`.
  - The extension reads the JSON, compares `nonce` to its last processed value (stored in `globalState`), and if new, opens diffs again (idempotent).
  - Provide a manual command (e.g., `openhands.showDiffNow`) as an additional trigger.
  - Debounce file-watch events (~250ms) to avoid double triggers on save.
- Live updates in VS Code:
  - Open diff editors refresh as files change (right side is working tree). If comparing against HEAD, the left side is static by definition; against INDEX, the left side updates as you stage/unstage.
  - The SCM view automatically reflects new/removed/modified files without reopening anything.
  - New changed files won’t auto-open diff tabs unless a new `nonce` is emitted; they will appear in SCM and can be opened by the user or by re-trigger.



Risks and Mitigations
- VS Code server fails to start: For V1, we accept that the diff tab is unavailable rather than recreating a fallback viewer.
- Too many changes opening too many tabs: cap to a reasonable limit and show SCM.
- Multi-repo complexity: default to first/active repository; add selection later if needed.

Acceptance Criteria
- When launching the VS Code diff experience:
  - VS Code web loads and shows SCM.
  - A limited number of diff editors open automatically.
  - User can edit in place; SCM operations (stage/commit) work.
  - No separate "Changes" viewer exists in V1.

Open Questions
- Triggering conditions for auto-diff (always, or only when FE navigates to a dedicated Diff view)? Proposal: FE writes `.vscode/openhands.json` to signal intent.
- Where to host the extension in production packaging (baked into the server image vs mounted directory)?
