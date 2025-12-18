"""
Validation and Approval Layer.

Requires explicit human approval for all data updates.
Records approval metadata for audit trail.

CRITICAL: All pending updates are persisted to reference_data/pending_updates.json
This is the SINGLE SOURCE OF TRUTH for pending approvals.
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import os


class ApprovalStatus(Enum):
    """Approval status for data updates."""
    
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRecord:
    """Record of approval for data update."""
    
    data_type: str  # "cost_index", "risk_alert", "code_revision", "currency_rate"
    data_id: str  # Unique identifier for the data
    status: ApprovalStatus
    approved_by: Optional[str]  # Engineer name or identifier
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    metadata: Dict[str, Any]


class Validator:
    """
    Validator for intelligence data updates.
    
    Requires explicit human approval before data can be used.
    All updates are recorded for audit trail.
    
    Pending updates are persisted to reference_data/pending_updates.json
    """
    
    def __init__(self, pending_file: str = "reference_data/pending_updates.json"):
        """
        Initialize the validator.
        
        Args:
            pending_file: Path to JSON file storing pending updates
        """
        self.pending_file = pending_file
        self.approval_records: Dict[str, ApprovalRecord] = {}
        
        # Ensure directory exists
        dir_path = os.path.dirname(pending_file)
        if dir_path:  # Only create if path has a directory component
            os.makedirs(dir_path, exist_ok=True)
        
        # Load existing pending updates
        self._load_pending()
    
    def request_approval(
        self,
        data_type: str,
        data_id: str,
        data_summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRecord:
        """
        Request approval for a data update.
        
        Args:
            data_type: Type of data ("cost_index", "risk_alert", etc.)
            data_id: Unique identifier for the data
            data_summary: Human-readable summary of the data
            metadata: Additional metadata
            
        Returns:
            ApprovalRecord with PENDING status
            
        Note:
            This persists the pending update to pending_updates.json
        """
        # Check if already exists
        if data_id in self.approval_records:
            existing = self.approval_records[data_id]
            if existing.status == ApprovalStatus.PENDING:
                # Already pending, don't duplicate
                return existing
        
        record = ApprovalRecord(
            data_type=data_type,
            data_id=data_id,
            status=ApprovalStatus.PENDING,
            approved_by=None,
            approved_at=None,
            rejection_reason=None,
            metadata=(metadata or {}).copy()
        )
        
        # Add summary to metadata for easier access
        record.metadata["data_summary"] = data_summary
        
        self.approval_records[data_id] = record
        
        # Persist to file
        self._save_pending()
        
        return record
    
    def approve(
        self,
        data_id: str,
        approved_by: str
    ) -> bool:
        """
        Approve a pending data update.
        
        Args:
            data_id: Unique identifier for the data
            approved_by: Engineer name or identifier
            
        Returns:
            True if approval successful, False otherwise
        """
        if data_id not in self.approval_records:
            return False
        
        record = self.approval_records[data_id]
        
        if record.status != ApprovalStatus.PENDING:
            return False  # Already approved or rejected
        
        record.status = ApprovalStatus.APPROVED
        record.approved_by = approved_by
        record.approved_at = datetime.now()
        
        # Persist changes and remove from pending
        self._save_pending()
        
        return True
    
    def reject(
        self,
        data_id: str,
        rejection_reason: str
    ) -> bool:
        """
        Reject a pending data update.
        
        Args:
            data_id: Unique identifier for the data
            rejection_reason: Reason for rejection
            
        Returns:
            True if rejection successful, False otherwise
        """
        if data_id not in self.approval_records:
            return False
        
        record = self.approval_records[data_id]
        
        if record.status != ApprovalStatus.PENDING:
            return False  # Already approved or rejected
        
        record.status = ApprovalStatus.REJECTED
        record.rejection_reason = rejection_reason
        
        # Persist changes and remove from pending
        self._save_pending()
        
        return True
    
    def get_approval_status(
        self,
        data_id: str
    ) -> Optional[ApprovalStatus]:
        """
        Get approval status for a data update.
        
        Args:
            data_id: Unique identifier for the data
            
        Returns:
            ApprovalStatus if found, None otherwise
        """
        if data_id not in self.approval_records:
            return None
        
        return self.approval_records[data_id].status
    
    def is_approved(
        self,
        data_id: str
    ) -> bool:
        """
        Check if data is approved.
        
        Args:
            data_id: Unique identifier for the data
            
        Returns:
            True if approved, False otherwise
        """
        status = self.get_approval_status(data_id)
        return status == ApprovalStatus.APPROVED
    
    def get_pending_approvals(
        self
    ) -> list[ApprovalRecord]:
        """
        Get all pending approval requests.
        
        Returns:
            List of ApprovalRecord objects with PENDING status
        """
        # Reload from file to ensure we have latest
        self._load_pending()
        
        return [
            record
            for record in self.approval_records.values()
            if record.status == ApprovalStatus.PENDING
        ]
    
    def _load_pending(self):
        """Load pending updates from JSON file."""
        if not os.path.exists(self.pending_file):
            self.approval_records = {}
            return
        
        try:
            with open(self.pending_file, "r") as f:
                data = json.load(f)
            
            self.approval_records = {}
            for item in data.get("pending_updates", []):
                # Convert status string to enum
                status_str = item.get("status", "pending").upper()
                if status_str == "PENDING":
                    status = ApprovalStatus.PENDING
                elif status_str == "APPROVED":
                    status = ApprovalStatus.APPROVED
                else:
                    status = ApprovalStatus.REJECTED
                
                # Parse datetime strings
                approved_at = None
                if item.get("approved_at"):
                    approved_at = datetime.fromisoformat(item["approved_at"])
                
                record = ApprovalRecord(
                    data_type=item["data_type"],
                    data_id=item["data_id"],
                    status=status,
                    approved_by=item.get("approved_by"),
                    approved_at=approved_at,
                    rejection_reason=item.get("rejection_reason"),
                    metadata=item.get("metadata", {})
                )
                
                # Only load PENDING records (approved/rejected are archived)
                if status == ApprovalStatus.PENDING:
                    self.approval_records[item["data_id"]] = record
                    
        except Exception as e:
            # If file is corrupted, start fresh
            self.approval_records = {}
    
    def _save_pending(self):
        """Save pending updates to JSON file."""
        # Only save PENDING records
        pending_data = {
            "pending_updates": []
        }
        
        for record in self.approval_records.values():
            if record.status == ApprovalStatus.PENDING:
                item = {
                    "data_id": record.data_id,
                    "data_type": record.data_type,
                    "status": "PENDING",
                    "summary": record.metadata.get("data_summary", ""),
                    "metadata": record.metadata,
                    "requested_at": datetime.now().isoformat(),
                    "approved_by": None,
                    "approved_at": None
                }
                pending_data["pending_updates"].append(item)
        
        # Write to file
        with open(self.pending_file, "w") as f:
            json.dump(pending_data, f, indent=2)

