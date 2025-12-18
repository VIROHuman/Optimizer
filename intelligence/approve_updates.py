"""
Approval Tool for Intelligence Module Updates.

Command-line interface for approving or rejecting pending updates.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.validator import Validator, ApprovalStatus
from intelligence.reference_store import ReferenceStore


def list_pending(validator: Validator):
    """List all pending approvals."""
    pending = validator.get_pending_approvals()
    
    if not pending:
        print("No pending approvals.")
        return
    
    print(f"\n{'='*70}")
    print(f"PENDING APPROVALS ({len(pending)})")
    print(f"{'='*70}\n")
    
    for i, record in enumerate(pending, 1):
        print(f"{i}. {record.data_type.upper()}: {record.data_id}")
        if 'data_summary' in record.metadata:
            print(f"   Summary: {record.metadata['data_summary']}")
        elif 'rate' in record.metadata:
            print(f"   Rate: {record.metadata['rate']}")
        elif 'value' in record.metadata:
            print(f"   Value: {record.metadata['value']}")
        print()


def approve_update(
    validator: Validator,
    store: ReferenceStore,
    data_id: str,
    approved_by: str
) -> bool:
    """
    Approve a pending update and store it in reference store.
    
    Args:
        validator: Validator instance
        store: ReferenceStore instance
        data_id: Data ID to approve
        approved_by: Engineer name
        
    Returns:
        True if successful, False otherwise
    """
    # Reload pending updates from file
    validator._load_pending()
    
    # Check if pending
    status = validator.get_approval_status(data_id)
    if status != ApprovalStatus.PENDING:
        print(f"✗ {data_id} is not pending (status: {status.value if status else 'not found'})")
        return False
    
    # Get the record before approving
    record = validator.approval_records[data_id]
    
    # Approve (this will update the file)
    if not validator.approve(data_id, approved_by):
        print(f"✗ Failed to approve {data_id}")
        return False
    
    # Store in reference store based on data type
    version_prefix = {
        "currency_rate": "FX",
        "cost_index": "COST",
        "risk_alert": "RISK",
        "code_revision": "CODE"
    }.get(record.data_type, "DATA")
    
    version = f"{version_prefix}-v{datetime.now().strftime('%Y.%m.%d')}"
    
    # Extract actual data from metadata
    data_to_store = record.metadata.copy()
    
    # Store based on data type
    if record.data_type == "currency_rate":
        # Store currency rate data
        rate_value = float(data_to_store.get("rate", 0))
        store.store_approved_data(
            data_type="currency_rate",
            version=version,
            data={
                "USD_INR": {
                    "rate": rate_value,
                    "source": data_to_store.get("source", ""),
                    "date": data_to_store.get("date", ""),
                }
            },
            approved_by=approved_by,
            approved_at=datetime.now(),
            metadata=data_to_store
        )
        print(f"✓ Approved and stored {data_id}")
        print(f"  Version: {version}")
        print(f"  Rate: {rate_value:.2f} INR/USD")
        print(f"  Approved by: {approved_by}")
    elif record.data_type == "cost_index":
        # Store cost index data
        store.store_approved_data(
            data_type="cost_index",
            version=version,
            data=data_to_store,
            approved_by=approved_by,
            approved_at=datetime.now(),
            metadata=data_to_store
        )
        print(f"✓ Approved and stored {data_id}")
        print(f"  Version: {version}")
        print(f"  Approved by: {approved_by}")
    elif record.data_type == "risk_alert":
        # Store risk alert data
        store.store_approved_data(
            data_type="risk_alert",
            version=version,
            data=data_to_store,
            approved_by=approved_by,
            approved_at=datetime.now(),
            metadata=data_to_store
        )
        print(f"✓ Approved and stored {data_id}")
        print(f"  Version: {version}")
        print(f"  Approved by: {approved_by}")
    elif record.data_type == "code_revision":
        # Store code revision data
        store.store_approved_data(
            data_type="code_revision",
            version=version,
            data=data_to_store,
            approved_by=approved_by,
            approved_at=datetime.now(),
            metadata=data_to_store
        )
        print(f"✓ Approved and stored {data_id}")
        print(f"  Version: {version}")
        print(f"  Approved by: {approved_by}")
    else:
        print(f"✗ Unknown data type: {record.data_type}")
        return False
    
    return True


def reject_update(
    validator: Validator,
    data_id: str,
    reason: str
) -> bool:
    """
    Reject a pending update.
    
    Args:
        validator: Validator instance
        data_id: Data ID to reject
        reason: Rejection reason
        
    Returns:
        True if successful, False otherwise
    """
    if validator.reject(data_id, reason):
        print(f"✓ Rejected {data_id}")
        print(f"  Reason: {reason}")
        return True
    else:
        print(f"✗ Failed to reject {data_id}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Approve or reject pending intelligence updates"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all pending approvals"
    )
    parser.add_argument(
        "--approve",
        type=str,
        metavar="DATA_ID",
        help="Approve a specific update by data_id"
    )
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="Approve all pending updates"
    )
    parser.add_argument(
        "--reject",
        type=str,
        metavar="DATA_ID",
        help="Reject a specific update by data_id"
    )
    parser.add_argument(
        "--approved-by",
        type=str,
        default="Engineer",
        help="Name of person approving (default: Engineer)"
    )
    parser.add_argument(
        "--reason",
        type=str,
        help="Reason for rejection (required when using --reject)"
    )
    
    args = parser.parse_args()
    
    # Initialize with persistent file
    validator = Validator(pending_file="reference_data/pending_updates.json")
    store = ReferenceStore(store_dir="reference_data/approved")
    
    # Load pending updates from file
    validator._load_pending()
    
    if args.list:
        list_pending(validator)
        return
    
    if args.approve:
        approve_update(validator, store, args.approve, args.approved_by)
        return
    
    if args.approve_all:
        pending = validator.get_pending_approvals()
        if not pending:
            print("No pending approvals to approve.")
            return
        
        print(f"Approving {len(pending)} pending updates...")
        for record in pending:
            approve_update(validator, store, record.data_id, args.approved_by)
        return
    
    if args.reject:
        if not args.reason:
            print("Error: --reason is required when rejecting updates")
            sys.exit(1)
        reject_update(validator, args.reject, args.reason)
        return
    
    # Default: list pending
    list_pending(validator)


if __name__ == "__main__":
    main()

