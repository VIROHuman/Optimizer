"""
Central Crawler Runner Module.

Single execution entry point for all crawlers.
Runs all crawlers, collects outputs, and stores as PENDING via Validator.

CRITICAL: This module does NOT apply updates automatically.
All fetched data requires explicit human approval.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path so we can import intelligence module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging for crawler execution
logging.basicConfig(
    level=logging.INFO,  # Show info, warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intelligence/crawler.log'),
        logging.StreamHandler()
    ]
)

from intelligence.cost_crawler import CostCrawler, CostIndexData
from intelligence.risk_crawler import RiskCrawler, RiskAlert
from intelligence.code_crawler import CodeCrawler, CodeRevisionAlert
from intelligence.currency_crawler import CurrencyCrawler, CurrencyRate
from intelligence.validator import Validator, ApprovalStatus
from intelligence.reference_store import ReferenceStore


def run_all_crawlers(
    regions: List[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Run all crawlers and collect candidate updates.
    
    Args:
        regions: List of regions to crawl (default: ["india", "europe", "usa"])
        verbose: Print progress messages
        
    Returns:
        Dictionary with summary of fetched data
        
    Note:
        All fetched data is stored as PENDING and requires approval.
    """
    if regions is None:
        regions = ["india", "europe", "usa"]
    
    # Initialize validator with persistent file
    validator = Validator(pending_file="reference_data/pending_updates.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "currency_updates": [],
        "cost_updates": [],
        "risk_updates": [],
        "code_updates": [],
        "pending_approvals": 0,
    }
    
    if verbose:
        print("=" * 70)
        print("RUNNING INTELLIGENCE CRAWLERS")
        print("=" * 70)
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Regions: {', '.join(regions)}")
        print()
    
    # 1. Currency Crawler
    if verbose:
        print("Fetching currency exchange rates...")
    
    currency_crawler = CurrencyCrawler()
    usd_inr_rate = currency_crawler.fetch_usd_to_inr()
    
    if usd_inr_rate:
        data_id = f"USD_INR_{datetime.now().strftime('%Y%m%d')}"
        
        # REQUIRED: Register pending update (persists to JSON)
        validator.request_approval(
            data_type="currency_rate",
            data_id=data_id,
            data_summary=f"USD/INR: {usd_inr_rate.rate:.2f} (Source: {usd_inr_rate.source})",
            metadata={
                "rate": str(usd_inr_rate.rate),
                "source": usd_inr_rate.source,
                "timestamp": usd_inr_rate.timestamp.isoformat(),
                "date": usd_inr_rate.timestamp.strftime("%Y-%m-%d"),
            }
        )
        
        summary["currency_updates"].append({
            "id": data_id,
            "rate": usd_inr_rate.rate,
            "source": usd_inr_rate.source,
        })
        if verbose:
            print(f"  ✓ Found USD/INR rate: {usd_inr_rate.rate:.2f} from {usd_inr_rate.source}")
            print(f"[CURRENCY] Candidate FX detected: USD/INR={usd_inr_rate.rate:.2f}, source={usd_inr_rate.source}")
            print(f"[CURRENCY] Pending update registered: {data_id}")
    else:
        if verbose:
            print("  ✗ No currency data available")
            print("[CURRENCY] No FX update detected")
    
    # 2. Cost Crawler
    if verbose:
        print("\nFetching cost indices...")
    
    cost_crawler = CostCrawler()
    for region in regions:
        indices = cost_crawler.fetch_all_indices(region)
        
        for index in indices:
            data_id = f"{index.index_type}_{region}_{datetime.now().strftime('%Y%m')}"
            validator.request_approval(
                data_type="cost_index",
                data_id=data_id,
                data_summary=f"{index.index_type} index for {region}: {index.value} {index.unit}",
                metadata={
                    "index_type": index.index_type,
                    "region": region,
                    "value": str(index.value),
                    "unit": index.unit,
                    "source": index.source,
                    "timestamp": index.timestamp.isoformat(),
                }
            )
            summary["cost_updates"].append({
                "id": data_id,
                "type": index.index_type,
                "region": region,
                "value": index.value,
            })
            if verbose:
                print(f"  ✓ Found {index.index_type} index for {region}: {index.value} {index.unit}")
    
    if not summary["cost_updates"]:
        if verbose:
            print("  ✗ No cost index data available")
    
    # 3. Risk Crawler
    if verbose:
        print("\nFetching risk alerts...")
    
    risk_crawler = RiskCrawler()
    for region in regions:
        alerts = risk_crawler.fetch_all_alerts(region)
        
        for alert in alerts:
            data_id = f"{alert.risk_type}_{region}_{datetime.now().strftime('%Y%m%d')}"
            validator.request_approval(
                data_type="risk_alert",
                data_id=data_id,
                data_summary=f"{alert.risk_type} alert for {region}: {alert.severity} severity",
                metadata={
                    "risk_type": alert.risk_type,
                    "region": region,
                    "severity": alert.severity,
                    "source": alert.source,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat(),
                }
            )
            summary["risk_updates"].append({
                "id": data_id,
                "type": alert.risk_type,
                "region": region,
                "severity": alert.severity,
            })
            if verbose:
                print(f"  ✓ Found {alert.risk_type} alert for {region}: {alert.severity} severity")
    
    if not summary["risk_updates"]:
        if verbose:
            print("  ✗ No risk alerts available")
    
    # 4. Code Crawler
    if verbose:
        print("\nChecking code revisions...")
    
    code_crawler = CodeCrawler()
    code_alerts = code_crawler.check_all_tracked_standards()
    
    for alert in code_alerts:
        data_id = f"{alert.standard_code}_{alert.standard_number}_{datetime.now().strftime('%Y%m%d')}"
        validator.request_approval(
            data_type="code_revision",
            data_id=data_id,
            data_summary=f"{alert.standard_code} {alert.standard_number}: {alert.status} - {alert.new_version}",
            metadata={
                "standard_code": alert.standard_code,
                "standard_number": alert.standard_number,
                "current_version": alert.current_version,
                "new_version": alert.new_version or "",
                "status": alert.status,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
            }
        )
        summary["code_updates"].append({
            "id": data_id,
            "standard": f"{alert.standard_code} {alert.standard_number}",
            "status": alert.status,
        })
        if verbose:
            print(f"  ✓ Found revision: {alert.standard_code} {alert.standard_number} - {alert.status}")
    
    if not summary["code_updates"]:
        if verbose:
            print("  ✗ No code revisions detected")
    
    # Summary
    pending = validator.get_pending_approvals()
    summary["pending_approvals"] = len(pending)
    
    if verbose:
        print("\n" + "=" * 70)
        print("CRAWLER SUMMARY")
        print("=" * 70)
        print(f"Currency updates: {len(summary['currency_updates'])}")
        print(f"Cost index updates: {len(summary['cost_updates'])}")
        print(f"Risk alerts: {len(summary['risk_updates'])}")
        print(f"Code revisions: {len(summary['code_updates'])}")
        print(f"\nTotal pending approvals: {summary['pending_approvals']}")
        print("\nNOTE: All updates are PENDING and require explicit approval.")
        print("Use Validator to approve or reject updates.")
        print("=" * 70)
    
    return summary


def main():
    """Main entry point for crawler execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run intelligence crawlers to fetch candidate updates"
    )
    parser.add_argument(
        "--regions",
        nargs="+",
        default=["india", "europe", "usa"],
        help="Regions to crawl (default: india europe usa)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    summary = run_all_crawlers(
        regions=args.regions,
        verbose=not args.quiet
    )
    
    # Exit code: 0 if updates found, 1 if none
    if summary["pending_approvals"] > 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

