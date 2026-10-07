"""Reviewed manual acceptance entry; obsolete claim/dispatch shortcuts are retired."""
import sys


if __name__ == "__main__":
    if sys.argv[1:] not in (["acceptance"], ["acceptance", "--retry-blocked"]):
        print("BLOCKED: use 'kanban-control.py acceptance' from Lee's PowerShell. "
              "Claim/dispatch, dry-run and arbitrary-token shortcuts are retired.", file=sys.stderr)
        sys.exit(2)
    sys.argv.pop(1)
    from guarded_jeeves_acceptance import main
    main()
