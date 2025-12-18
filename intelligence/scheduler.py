"""
Scheduler Module for Periodic Crawler Execution.

Runs crawlers periodically using schedule library.
NEVER runs PSO or optimization - only crawlers.

CRITICAL: Scheduler runs independently of optimization.
It does NOT affect engineering calculations.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add parent directory to path so we can import intelligence module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.run_crawlers import run_all_crawlers

# Optional import - only needed for continuous scheduling
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intelligence/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_currency_crawler():
    """Run currency crawler (weekly)."""
    logger.info("Running currency crawler (weekly schedule)")
    try:
        summary = run_all_crawlers(regions=["india", "europe", "usa"], verbose=False)
        logger.info(f"Currency crawler completed: {len(summary['currency_updates'])} updates")
    except Exception as e:
        logger.error(f"Currency crawler failed: {e}", exc_info=True)


def run_cost_crawler():
    """Run cost crawler (monthly)."""
    logger.info("Running cost crawler (monthly schedule)")
    try:
        summary = run_all_crawlers(regions=["india", "europe", "usa"], verbose=False)
        logger.info(f"Cost crawler completed: {len(summary['cost_updates'])} updates")
    except Exception as e:
        logger.error(f"Cost crawler failed: {e}", exc_info=True)


def run_risk_crawler():
    """Run risk crawler (monthly)."""
    logger.info("Running risk crawler (monthly schedule)")
    try:
        summary = run_all_crawlers(regions=["india", "europe", "usa"], verbose=False)
        logger.info(f"Risk crawler completed: {len(summary['risk_updates'])} updates")
    except Exception as e:
        logger.error(f"Risk crawler failed: {e}", exc_info=True)


def run_code_crawler():
    """Run code crawler (quarterly)."""
    logger.info("Running code crawler (quarterly schedule)")
    try:
        summary = run_all_crawlers(regions=["india", "europe", "usa"], verbose=False)
        logger.info(f"Code crawler completed: {len(summary['code_updates'])} updates")
    except Exception as e:
        logger.error(f"Code crawler failed: {e}", exc_info=True)


def setup_schedule():
    """
    Setup periodic crawler schedules.
    
    Default schedules:
    - Currency: Weekly (Sunday 2 AM)
    - Cost: Monthly (1st of month, 3 AM)
    - Risk: Monthly (1st of month, 4 AM)
    - Code: Quarterly (1st of Jan/Apr/Jul/Oct, 5 AM)
    
    Note: These schedules are examples. Adjust as needed.
    """
    # Currency crawler - weekly (Sunday 2 AM)
    schedule.every().sunday.at("02:00").do(run_currency_crawler)
    
    # Cost crawler - monthly (1st of month, 3 AM)
    schedule.every().month.do(run_cost_crawler)
    
    # Risk crawler - monthly (1st of month, 4 AM)
    schedule.every().month.do(run_risk_crawler)
    
    # Code crawler - quarterly (1st of Jan/Apr/Jul/Oct, 5 AM)
    # Note: schedule library doesn't support quarterly directly
    # Use monthly check with conditional execution
    schedule.every().month.do(run_code_crawler)
    
    logger.info("Scheduler configured with default schedules")
    logger.info("Currency: Weekly (Sunday 2 AM)")
    logger.info("Cost: Monthly (1st, 3 AM)")
    logger.info("Risk: Monthly (1st, 4 AM)")
    logger.info("Code: Quarterly (1st, 5 AM)")


def run_scheduler():
    """
    Run the scheduler continuously.
    
    This function runs in a loop, checking for scheduled tasks.
    It never blocks optimization and runs independently.
    
    IMPORTANT: This scheduler ONLY runs crawlers.
    It NEVER runs PSO or optimization.
    """
    if not SCHEDULE_AVAILABLE:
        logger.error("schedule library not installed. Install with: pip install schedule")
        logger.error("For one-time runs, use: python intelligence/run_crawlers.py")
        return
    
    logger.info("Starting intelligence scheduler")
    logger.info("Scheduler runs independently of optimization")
    logger.info("Press Ctrl+C to stop")
    
    setup_schedule()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)


def main():
    """
    Main entry point for scheduler.
    
    Can be run as:
    - Standalone script: python intelligence/scheduler.py
    - Background service: nohup python intelligence/scheduler.py &
    - Systemd service: Configure as systemd service
    - Cron alternative: Use OS cron to call run_crawlers.py directly
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run intelligence crawler scheduler"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run all crawlers once and exit (no scheduling)"
    )
    parser.add_argument(
        "--currency-only",
        action="store_true",
        help="Run only currency crawler"
    )
    parser.add_argument(
        "--cost-only",
        action="store_true",
        help="Run only cost crawler"
    )
    parser.add_argument(
        "--risk-only",
        action="store_true",
        help="Run only risk crawler"
    )
    parser.add_argument(
        "--code-only",
        action="store_true",
        help="Run only code crawler"
    )
    
    args = parser.parse_args()
    
    if args.once:
        # Run all crawlers once and exit
        logger.info("Running all crawlers once (no scheduling)")
        run_all_crawlers(regions=["india", "europe", "usa"], verbose=True)
        return
    
    if args.currency_only:
        run_currency_crawler()
        return
    
    if args.cost_only:
        run_cost_crawler()
        return
    
    if args.risk_only:
        run_risk_crawler()
        return
    
    if args.code_only:
        run_code_crawler()
        return
    
    # Default: Run scheduler continuously
    run_scheduler()


# Cron-style schedule documentation
"""
Example cron entries (for reference, not enforced):

# Currency crawler - Weekly (Sunday 2 AM)
0 2 * * 0 cd /path/to/Optimiser && python intelligence/run_crawlers.py --regions india europe usa

# Cost crawler - Monthly (1st of month, 3 AM)
0 3 1 * * cd /path/to/Optimiser && python intelligence/run_crawlers.py --regions india europe usa

# Risk crawler - Monthly (1st of month, 4 AM)
0 4 1 * * cd /path/to/Optimiser && python intelligence/run_crawlers.py --regions india europe usa

# Code crawler - Quarterly (1st of Jan/Apr/Jul/Oct, 5 AM)
0 5 1 1,4,7,10 * cd /path/to/Optimiser && python intelligence/run_crawlers.py --regions india europe usa

Note: Using cron directly calls run_crawlers.py, bypassing scheduler.py.
This is acceptable and may be preferred for production deployments.
"""


if __name__ == "__main__":
    main()

