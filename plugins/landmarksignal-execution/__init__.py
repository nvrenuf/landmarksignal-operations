from .policy import decide


def register(ctx):
    ctx.register_hook("pre_tool_call", decide)
