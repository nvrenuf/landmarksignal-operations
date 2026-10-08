"""Use native Hermes tools and approvals for Lee's project workflow.

The explicit Issue 19 foreground acceptance scope remains tool-free.
Ordinary chat and native workers are governed by Hermes configuration,
its task lifecycle checks, and the project's operating instructions.
"""
import sys


def decide(tool_name="", args=None, **kwargs):
    scope = sys.modules.get("landmarksignal_v1_scope")
    if getattr(scope, "acceptance", False):
        return {"action": "block", "message": "LANDMARKSIGNAL_V1: Issue #19 acceptance calls have no tool permission."}
    return None
