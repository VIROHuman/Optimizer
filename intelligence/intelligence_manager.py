"""
Intelligence Manager Module.

Orchestrates crawlers, tracks approved versions, and exposes summaries
to OUTPUT LAYER ONLY. Never exposes data to PSO or physics modules.
"""

from typing import Dict, Optional
from datetime import datetime
from intelligence.cost_crawler import CostCrawler
from intelligence.risk_crawler import RiskCrawler
from intelligence.code_crawler import CodeCrawler
from intelligence.currency_crawler import CurrencyCrawler
from intelligence.validator import Validator
from intelligence.reference_store import ReferenceStore


class IntelligenceManager:
    """
    Manager for intelligence module.
    
    Orchestrates crawlers and manages approved reference data.
    Exposes summaries to OUTPUT LAYER ONLY.
    """
    
    def __init__(self):
        """Initialize the intelligence manager."""
        self.cost_crawler = CostCrawler()
        self.risk_crawler = RiskCrawler()
        self.code_crawler = CodeCrawler()
        self.currency_crawler = CurrencyCrawler()
        self.validator = Validator(pending_file="reference_data/pending_updates.json")
        self.reference_store = ReferenceStore(store_dir="reference_data/approved")
    
    def get_reference_status(
        self
    ) -> Dict[str, str]:
        """
        Get status of reference data versions.
        
        Returns:
            Dictionary mapping data types to version strings
        """
        status = {}
        
        data_types = [
            "cost_index",
            "risk_alert",
            "code_revision",
            "currency_rate",
        ]
        
        for data_type in data_types:
            active_version = self.reference_store.get_active_version(data_type)
            if active_version:
                status[data_type] = active_version.version
            else:
                status[data_type] = "N/A"
        
        return status
    
    def get_currency_rate(
        self,
        base_currency: str,
        target_currency: str
    ) -> Optional[float]:
        """
        Get approved currency exchange rate.
        
        Args:
            base_currency: Base currency code (e.g., "USD")
            target_currency: Target currency code (e.g., "INR")
            
        Returns:
            Exchange rate if available, None otherwise
            
        Note:
            Only returns rates from APPROVED reference data.
            Returns None if no approved rate exists (fallback to default).
        """
        # Check reference store for approved rate
        currency_data = self.reference_store.get_active_version("currency_rate")
        
        if currency_data and isinstance(currency_data.data, dict):
            key = f"{base_currency}_{target_currency}"
            if key in currency_data.data:
                rate = currency_data.data[key].get("rate")
                if rate:
                    return float(rate)
        
        return None
    
    def get_currency_version(
        self
    ) -> Optional[str]:
        """
        Get version of currency reference data.
        
        Returns:
            Version string if available, None otherwise
        """
        currency_data = self.reference_store.get_active_version("currency_rate")
        if currency_data:
            return currency_data.version
        return None

