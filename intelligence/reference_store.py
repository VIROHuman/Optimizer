"""
Reference Data Store Module.

Stores approved data with versioning.
Allows rollback and provides READ-ONLY access.
NEVER exposes live data to PSO or physics modules.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os


@dataclass
class ReferenceDataVersion:
    """Versioned reference data entry."""
    
    data_type: str  # "cost_index", "risk_alert", "code_revision", "currency_rate"
    version: str  # Version identifier (e.g., "v2025.02")
    data: Any  # The actual data
    approved_by: str
    approved_at: datetime
    is_active: bool
    metadata: Dict[str, Any]


class ReferenceStore:
    """
    Versioned reference data store.
    
    Stores approved data with versioning and allows rollback.
    Provides READ-ONLY access for output formatting and advisories.
    """
    
    def __init__(self, store_dir: str = "reference_data/approved"):
        """
        Initialize the reference store.
        
        Args:
            store_dir: Directory to store approved reference data files
        """
        self.store_dir = store_dir
        self.versions: Dict[str, List[ReferenceDataVersion]] = {}
        
        # Ensure store directory exists
        os.makedirs(store_dir, exist_ok=True)
        
        # Load existing approved data
        self._load_from_disk()
    
    def store_approved_data(
        self,
        data_type: str,
        version: str,
        data: Any,
        approved_by: str,
        approved_at: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store approved reference data with versioning.
        
        Args:
            data_type: Type of data
            version: Version identifier
            data: The actual data
            approved_by: Engineer who approved
            approved_at: Approval timestamp
            metadata: Additional metadata
            
        Returns:
            True if storage successful, False otherwise
        """
        if data_type not in self.versions:
            self.versions[data_type] = []
        
        # Deactivate previous versions of same type
        for existing_version in self.versions[data_type]:
            if existing_version.is_active:
                existing_version.is_active = False
        
        # Create new version
        version_entry = ReferenceDataVersion(
            data_type=data_type,
            version=version,
            data=data,
            approved_by=approved_by,
            approved_at=approved_at,
            is_active=True,
            metadata=metadata or {}
        )
        
        self.versions[data_type].append(version_entry)
        
        # Persist to disk
        self._persist_to_disk()
        
        return True
    
    def get_active_version(
        self,
        data_type: str
    ) -> Optional[ReferenceDataVersion]:
        """
        Get active version of reference data.
        
        Args:
            data_type: Type of data
            
        Returns:
            ReferenceDataVersion if found, None otherwise
        """
        if data_type not in self.versions:
            return None
        
        for version in self.versions[data_type]:
            if version.is_active:
                return version
        
        return None
    
    def get_version(
        self,
        data_type: str,
        version: str
    ) -> Optional[ReferenceDataVersion]:
        """
        Get specific version of reference data.
        
        Args:
            data_type: Type of data
            version: Version identifier
            
        Returns:
            ReferenceDataVersion if found, None otherwise
        """
        if data_type not in self.versions:
            return None
        
        for version_entry in self.versions[data_type]:
            if version_entry.version == version:
                return version_entry
        
        return None
    
    def list_versions(
        self,
        data_type: str
    ) -> List[ReferenceDataVersion]:
        """
        List all versions of reference data.
        
        Args:
            data_type: Type of data
            
        Returns:
            List of ReferenceDataVersion objects
        """
        if data_type not in self.versions:
            return []
        
        return self.versions[data_type].copy()
    
    def rollback_to_version(
        self,
        data_type: str,
        version: str
    ) -> bool:
        """
        Rollback to a specific version.
        
        Args:
            data_type: Type of data
            version: Version identifier to rollback to
            
        Returns:
            True if rollback successful, False otherwise
        """
        target_version = self.get_version(data_type, version)
        if not target_version:
            return False
        
        # Deactivate all versions
        for version_entry in self.versions[data_type]:
            version_entry.is_active = False
        
        # Activate target version
        target_version.is_active = True
        
        # Persist to disk
        self._persist_to_disk()
        
        return True
    
    def _persist_to_disk(self):
        """Persist reference store to disk."""
        store_file = os.path.join(self.store_dir, "reference_store.json")
        
        # Convert to serializable format
        store_data = {}
        for data_type, versions in self.versions.items():
            store_data[data_type] = []
            for version in versions:
                version_dict = asdict(version)
                # Convert datetime to string
                if isinstance(version_dict.get("approved_at"), datetime):
                    version_dict["approved_at"] = version_dict["approved_at"].isoformat()
                store_data[data_type].append(version_dict)
        
        with open(store_file, "w") as f:
            json.dump(store_data, f, indent=2)
        
        # Also store individual version files for easier access
        for data_type, versions in self.versions.items():
            for version in versions:
                if version.is_active:
                    # Store active version as separate file
                    version_file = os.path.join(
                        self.store_dir,
                        f"{data_type}_{version.version}.json"
                    )
                    version_dict = asdict(version)
                    if isinstance(version_dict.get("approved_at"), datetime):
                        version_dict["approved_at"] = version_dict["approved_at"].isoformat()
                    with open(version_file, "w") as f:
                        json.dump(version_dict, f, indent=2)
    
    def _load_from_disk(self):
        """Load reference store from disk."""
        store_file = os.path.join(self.store_dir, "reference_store.json")
        
        if not os.path.exists(store_file):
            return
        
        with open(store_file, "r") as f:
            store_data = json.load(f)
        
        for data_type, versions_list in store_data.items():
            self.versions[data_type] = []
            for version_dict in versions_list:
                # Convert datetime string back to datetime
                if isinstance(version_dict.get("approved_at"), str):
                    version_dict["approved_at"] = datetime.fromisoformat(version_dict["approved_at"])
                
                version_entry = ReferenceDataVersion(**version_dict)
                self.versions[data_type].append(version_entry)

