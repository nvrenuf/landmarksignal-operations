"""
Evidence attachment mechanism for Hermes execution records.

This module provides functions to:
1. Attach evidence (PR URLs, test results) to task execution records
2. Record evidence before claiming success
3. Return evidence/PR URLs to GitHub
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Evidence:
    """Evidence attached to an execution record."""
    type: str  # 'pr_url', 'test_result', 'failure_log', 'human_review'
    url: Optional[str] = None
    summary: Optional[str] = None
    details: Optional[str] = None
    confidence: Optional[float] = None
    recorded_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Evidence':
        return cls(**{k: v for k, v in data.items() if v is not None})


@dataclass
class ExecutionRecord:
    """Execution record with attached evidence."""
    task_id: str
    task_title: str
    status: str
    profile: str
    workspace_path: str
    github_issue_url: Optional[str] = None
    github_repo_url: Optional[str] = None
    kanban_run_id: Optional[str] = None
    evidence: List[Evidence] = None
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
    
    def attach_evidence(self, evidence: Evidence) -> bool:
        """Attach evidence to this execution record. Evidence must be recorded before claiming success."""
        evidence.recorded_at = datetime.now(timezone.utc).isoformat()
        self.evidence.append(evidence)
        return True
    
    def get_evidence_for_github(self) -> Dict[str, Any]:
        """Format evidence for returning to GitHub."""
        result = {
            'task_id': self.task_id,
            'status': self.status,
            'evidence': []
        }
        
        result.update(github_issue_url=self.github_issue_url, board_name='landmarksignal',
                      profile=self.profile, workspace_path=self.workspace_path, kanban_run_id=self.kanban_run_id)
        result['evidence'] = [ev.to_dict() for ev in self.evidence]
        return result


def generate_idempotency_key(
    github_issue_id: str,
    kanban_task_id: str,
    profile: str,
    workspace_path: str
) -> str:
    """Generate an idempotency key to prevent duplicate task creation."""
    data = f"{github_issue_id}:{kanban_task_id}:{profile}:{workspace_path}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def create_execution_record(
    github_data: Dict[str, Any],
    kanban_task_id: str,
    profile: str,
    workspace_path: str,
    kanban_run_id: int
) -> ExecutionRecord:
    """Create an evidence record bound to an actual native run; no task is created."""
    if not isinstance(kanban_run_id, int) or kanban_run_id <= 0:
        raise ValueError('Actual native run ID is required')
    issue = github_data.get('issue', {})
    
    return ExecutionRecord(
        task_id=kanban_task_id,
        task_title=issue.get('title', 'Unknown'),
        status=github_data.get('source_status', 'todo'),
        profile=profile,
        workspace_path=workspace_path,
        github_issue_url=issue.get('url'),
        github_repo_url=issue.get('repository', {}).get('nameWithOwner'),
        kanban_run_id=str(kanban_run_id),
        evidence=[]
    )


def record_evidence(
    record: ExecutionRecord,
    evidence_type: str,
    url: Optional[str] = None,
    summary: Optional[str] = None,
    details: Optional[str] = None,
    confidence: Optional[float] = None
) -> Evidence:
    """Record evidence to an execution record."""
    ev = Evidence(
        type=evidence_type,
        url=url,
        summary=summary,
        details=details,
        confidence=confidence
    )
    record.attach_evidence(ev)
    return ev


def get_github_return_payload(record: ExecutionRecord) -> Dict[str, Any]:
    """Generate payload for returning evidence to GitHub."""
    return record.get_evidence_for_github()


