"""Observe actual installed Hermes hooks in fresh default/Jeeves processes."""
import os
from pathlib import Path
import subprocess
import sys

PROBE='''import sys
sys.path.insert(0,sys.argv[1])
import hermes_bootstrap
from hermes_cli.plugins import get_pre_tool_call_directive
from hermes_cli.config import load_config
config=load_config()
if config.get("kanban",{}).get("review_dispatch") is not False:
    raise RuntimeError("Installed loader does not disable review dispatch")
if config.get("kanban",{}).get("max_in_progress") != 1:
    raise RuntimeError("Installed loader does not read concurrency=1")
for tool in ('kanban_show','kanban_block','kanban_request_review','write_file'):
    action,message=get_pre_tool_call_directive(tool,{'board':'landmarksignal'})
    if action=='block': raise RuntimeError('Unexpected native tool denial: '+tool)
action,message=get_pre_tool_call_directive('kanban_complete',{'board':'landmarksignal'})
if action!='block' or 'kanban_request_review' not in message:
    raise RuntimeError('Actual worker completion hook did not require Review')
print('PASS: actual Hermes hooks allow project work and require Review')
'''

def main():
    root=Path(os.environ['LOCALAPPDATA'])/'hermes';runtime=root/'hermes-agent'
    for profile,home in [('default',root),('jeeves',root/'profiles/jeeves')]:
        env=os.environ.copy();env.update(HERMES_HOME=str(home),HERMES_PROFILE=profile,HERMES_KANBAN_BOARD='landmarksignal')
        result=subprocess.run([str(runtime/'venv/Scripts/python.exe'),'-B','-c',PROBE,str(runtime)],
                              env=env,cwd=runtime,capture_output=True,text=True,timeout=45)
        print(profile+':',result.stdout.strip())
        if result.returncode:
            print(result.stderr);raise RuntimeError('Installed hook verification failed: '+profile)
if __name__=='__main__':main()
