from .policy import decide


def register(ctx):
    ctx.register_hook('pre_tool_call',decide)
    ctx.register_system_prompt_section('landmarksignal.review',
        'For LandmarkSignal board work: Ready is the native execution queue. GitHub intake selects planning work; it does not itself approve execution. Use the assigned native workspace and actual task/run IDs. Preserve GitHub Priority, Execution Order and Sprint. Finish implementation with kanban_request_review and actual artifact/test evidence, never kanban_complete. Lee approves Complete from the dashboard. If incomplete, kanban_block with a specific reason. The old foreground-only entry restriction has been removed; do not request it. Never claim demo output is a verified live integration. Merges, deployment and production infrastructure changes still require Lee approval.',
        max_chars=1500)
