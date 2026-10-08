"""Allow native work; workers submit LandmarkSignal output for human review."""
import os
from pathlib import Path
import sys


def decide(tool_name='', args=None, **kwargs):
    scope=sys.modules.get('landmarksignal_v1_scope')
    if getattr(scope,'acceptance',False):
        return {'action':'block','message':'LANDMARKSIGNAL_V1: Explicit acceptance calls have no tools.'}
    args=args if isinstance(args,dict) else {}
    native_board=os.environ.get('HERMES_KANBAN_BOARD')
    database=os.environ.get('HERMES_KANBAN_DB','').replace('\\','/').lower()
    landmarksignal=(args.get('board')=='landmarksignal' or native_board=='landmarksignal'
                    or database.endswith('/kanban/boards/landmarksignal/kanban.db'))
    if tool_name=='kanban_complete' and landmarksignal:
        return {'action':'block','message':'Submit this work with kanban_request_review and actual file/test evidence. Lee completes it from the dashboard after review. If work is incomplete, call kanban_block with the exact blocker.'}
    return None
