# Native Jeeves project tools

Lee authorized removing the custom foreground-only execution restriction so normal Hermes project work can use native tools. `setup_jeeves_native_tools.ps1` supersedes the read-boundary repair for this operating mode.

The installed execution plugin remains registered, but its policy permits ordinary native tool calls. Card reads, workspace work, delegation and native lifecycle reporting use Hermes's own handlers and existing approval configuration. The explicit Issue 19 foreground acceptance scope remains tool-free. The custom mutex gate no longer controls ordinary native execution; configured concurrency limits remain, and this installer does not claim global cross-profile mutex enforcement.

The installer backs up and replaces only recognized execution-policy copies, preserves their existing permissions and configuration bytes, and reloads only the verified standalone browser dashboard. It refuses a running LandmarkSignal task. It does not unblock, promote, claim, retry or dispatch any task. Existing chats in other runtimes need a new runtime session to load the new plugin code.

Ready is the native execution queue and can dispatch automatically. Lee decides when work enters that queue. Existing operating instructions still require human review and explicit approval for merges, deployment, costs and production infrastructure changes. These are operating rules, not guarantees enforced by this now-permissive hook. Standard Hermes approvals remain configured; the installer does not enable approval bypass.

Windows installation and the next actual worker run must be confirmed from their reports. The three policy checks verify normal tool access and the retained explicit acceptance restriction; dashboard HTTP availability does not prove a completed worker run.
