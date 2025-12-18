"""
Currency Exchange Rate Crawler Module.

Tracks reference exchange rates from trusted sources.
Currency data is FINANCIAL REFERENCE DATA only.
Never auto-applies exchange rate changes.

CRITICAL: All fetched rates are CANDIDATE UPDATES ONLY.
They require explicit human approval before use.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CurrencyRate:
    """Currency exchange rate data."""
    
    base_currency: str  # "USD"
    target_currency: str  # "INR", "EUR", etc.
    rate: float  # Exchange rate
    source: str  # Data source identifier
    timestamp: datetime
    volatility_note: Optional[str]  # Note on volatility if significant
    metadata: Dict[str, str]


class CurrencyCrawler:
    """
    Crawler for currency exchange rates.
    
    Uses trusted sources (RBI, IMF, World Bank).
    Currency data is FINANCIAL REFERENCE DATA only.
    
    IMPORTANT: Fetched rates are CANDIDATE UPDATES.
    They must be approved via Validator before use.
    """
    
    def __init__(self):
        """Initialize the currency crawler."""
        self.sources = {
            "INR": {
                "primary": "RBI",
                "fallback": ["IMF", "WorldBank"],
            },
            "EUR": {
                "primary": "ECB",
                "fallback": ["IMF"],
            },
            "GBP": {
                "primary": "BoE",
                "fallback": ["IMF"],
            },
        }
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TransmissionTowerOptimizer/1.0"
        })
    
    def fetch_usd_to_inr(
        self
    ) -> Optional[CurrencyRate]:
        """
        Fetch USD to INR exchange rate from stable FX reference API.
        
        Uses Yahoo Finance as primary source (reliable, no API key required).
        Falls back to Fixer.io, exchangerate.host, and World Bank if needed.
        RBI and IMF implementations are temporarily deprecated due to:
        - RBI: Requires HTML scraping (unstable)
        - IMF: Complex API endpoints (brittle)
        - World Bank: FX indicators unreliable
        
        TODO: Implement RBI/IMF APIs when stable endpoints are available.
        
        Returns:
            CurrencyRate if available, None otherwise
            
        Note:
            This is a CANDIDATE UPDATE. It requires approval before use.
            FX rate is REFERENCE-ONLY, not for commercial settlement.
        """
        # Try Yahoo Finance first (most reliable, no API key)
        rate = self._fetch_yahoo_finance_usd_inr()
        if rate:
            return rate
        
        # Fallback to Fixer.io
        rate = self._fetch_fixer_io_usd_inr()
        if rate:
            return rate
        
        # Fallback to exchangerate.host (no API key required)
        rate = self._fetch_exchangerate_host_usd_inr()
        if rate:
            return rate
        
        # Fallback to World Bank (if all fail)
        rate = self._fetch_worldbank_usd_inr()
        if rate:
            return rate
        
        # If all sources fail, return None
        return None
    
    def _fetch_yahoo_finance_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from Yahoo Finance API.
        
        Source: https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X
        
        This is a reliable FX API with no API key required.
        Suitable for:
        - Cost reporting
        - Feasibility studies
        - Early-stage estimation tools
        
        Note: This is REFERENCE-ONLY, not for commercial settlement.
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Yahoo Finance API response structure:
            # {
            #   "chart": {
            #     "result": [{
            #       "meta": {
            #         "regularMarketPrice": <rate>
            #       }
            #     }]
            #   }
            # }
            
            if "chart" in data and "result" in data["chart"]:
                results = data["chart"]["result"]
                if len(results) > 0:
                    meta = results[0].get("meta", {})
                    rate = meta.get("regularMarketPrice")
                    
                    if rate:
                        logger.info(f"Successfully fetched USD/INR rate from Yahoo Finance: {rate}")
                        return CurrencyRate(
                            base_currency="USD",
                            target_currency="INR",
                            rate=round(float(rate), 2),
                            source="Yahoo Finance",
                            timestamp=datetime.now(),
                            volatility_note=None,
                            metadata={
                                "currency_pair": "USDINR=X",
                                "api_url": url
                            }
                        )
                    else:
                        logger.warning("Yahoo Finance response missing regularMarketPrice")
                else:
                    logger.warning("Yahoo Finance response has empty results array")
            else:
                logger.warning(f"Yahoo Finance response missing expected structure. Keys: {list(data.keys())}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching Yahoo Finance: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data parsing error from Yahoo Finance: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in Yahoo Finance fetch: {e}")
            return None
    
    def _fetch_fixer_io_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from Fixer.io API.
        
        Source: https://fixer.io/
        
        This is a reliable FX API suitable for:
        - Cost reporting
        - Feasibility studies
        - Early-stage estimation tools
        
        Note: This is REFERENCE-ONLY, not for commercial settlement.
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        try:
            import os
            
            # Fixer.io API key - check environment variable first, then use default
            api_key = os.getenv("FIXER_API_KEY", "b9f5d90acda9ac4bd8452f4181dd3c36")
            
            if not api_key:
                logger.warning("Fixer.io API key not available")
                return None
            
            # Fixer.io free tier endpoint (latest rates)
            # Note: Free tier uses EUR as base, so we need to convert
            url = f"http://data.fixer.io/api/latest"
            params = {
                "access_key": api_key,
                "symbols": "USD,INR"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if API returned success
            if data.get("success", False) and "rates" in data:
                rates = data["rates"]
                usd_rate = rates.get("USD")
                inr_rate = rates.get("INR")
                
                if usd_rate and inr_rate:
                    # Fixer.io free tier uses EUR as base
                    # Convert: USD/INR = (EUR/INR) / (EUR/USD) = INR_rate / USD_rate
                    usd_inr_rate = float(inr_rate) / float(usd_rate)
                    
                    logger.info(f"Successfully fetched USD/INR rate from Fixer.io: {usd_inr_rate:.2f}")
                    return CurrencyRate(
                        base_currency="USD",
                        target_currency="INR",
                        rate=round(usd_inr_rate, 2),
                        source="Fixer.io",
                        timestamp=datetime.now(),
                        volatility_note=None,
                        metadata={
                            "date": data.get("date", ""),
                            "api_url": url
                        }
                    )
            else:
                error_info = data.get("error", {})
                logger.warning(f"Fixer.io API error: {error_info.get('info', 'Unknown error')}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching Fixer.io: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data parsing error from Fixer.io: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in Fixer.io fetch: {e}")
            return None
    
    def _fetch_exchangerate_host_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from exchangerate.host API.
        
        Source: https://api.exchangerate.host/latest
        
        This is a stable FX reference API suitable for:
        - Cost reporting
        - Feasibility studies
        - Early-stage estimation tools
        
        Note: This is REFERENCE-ONLY, not for commercial settlement.
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        try:
            url = "https://api.exchangerate.host/latest"
            params = {"base": "USD", "symbols": "INR"}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Debug: Check API response structure
            # exchangerate.host API returns: {"success": true, "base": "USD", "date": "...", "rates": {"INR": ...}}
            # Some versions may not have "success" field, so check rates directly
            if "rates" in data:
                rate = data["rates"].get("INR")
                if rate:
                    return CurrencyRate(
                        base_currency="USD",
                        target_currency="INR",
                        rate=round(float(rate), 2),
                        source="exchangerate.host",
                        timestamp=datetime.now(),
                        volatility_note=None,
                        metadata={
                            "date": data.get("date", ""),
                            "api_url": url
                        }
                    )
            
            # If no rates found, try alternative endpoint format
            # exchangerate.host might use different response structure
            return None
            
        except requests.exceptions.RequestException as e:
            # Network/HTTP errors - log but don't fail
            logger.warning(f"Network error fetching exchangerate.host: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            # JSON parsing or data structure errors
            logger.warning(f"Data parsing error from exchangerate.host: {e}")
            return None
        except Exception as e:
            # Any other unexpected errors
            logger.warning(f"Unexpected error in exchangerate.host fetch: {e}")
            return None
    
    def _fetch_rbi_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from Reserve Bank of India.
        
        Source: https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx
        
        TEMPORARILY DEPRECATED:
        - Requires HTML scraping (unstable)
        - RBI API endpoints not publicly documented
        - Implementation deferred until stable API available
        
        TODO: Implement RBI API when stable endpoints are available.
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        # Temporarily disabled - use exchangerate.host instead
        return None
    
    def _fetch_imf_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from IMF.
        
        Source: https://www.imf.org/external/np/fin/data/param_rms_mth.aspx
        
        TEMPORARILY DEPRECATED:
        - Complex API endpoints (brittle)
        - IMF API documentation not readily available
        - Implementation deferred until stable API available
        
        TODO: Implement IMF API when stable endpoints are available.
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        # Temporarily disabled - use exchangerate.host instead
        return None
    
    def _fetch_worldbank_usd_inr(self) -> Optional[CurrencyRate]:
        """
        Fetch USD/INR rate from World Bank API.
        
        Source: World Bank Open Data API
        
        Returns:
            CurrencyRate if successful, None otherwise
        """
        try:
            # World Bank API endpoint
            # Example: https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF
            wb_url = "https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF"
            
            response = self.session.get(
                wb_url,
                params={
                    "format": "json",
                    "date": datetime.now().strftime("%Y"),
                    "per_page": 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse World Bank response
                if len(data) >= 2 and len(data[1]) > 0:
                    rate_value = data[1][0].get("value")
                    if rate_value:
                        return CurrencyRate(
                            base_currency="USD",
                            target_currency="INR",
                            rate=float(rate_value),
                            source="WorldBank",
                            timestamp=datetime.now(),
                            volatility_note=None,
                            metadata={
                                "wb_indicator": "PA.NUS.FCRF",
                                "date": data[1][0].get("date", "")
                            }
                        )
            
            return None
            
        except Exception as e:
            # If World Bank API fails, return None
            return None
    
    def fetch_usd_to_eur(
        self
    ) -> Optional[CurrencyRate]:
        """
        Fetch USD to EUR exchange rate.
        
        Returns:
            CurrencyRate if available, None otherwise
        """
        # TODO: Implement ECB API call
        return None
    
    def fetch_rate(
        self,
        base_currency: str,
        target_currency: str
    ) -> Optional[CurrencyRate]:
        """
        Fetch exchange rate between two currencies.
        
        Args:
            base_currency: Base currency code (e.g., "USD")
            target_currency: Target currency code (e.g., "INR")
            
        Returns:
            CurrencyRate if available, None otherwise
            
        Note:
            This is a CANDIDATE UPDATE. It requires approval before use.
        """
        if base_currency == "USD" and target_currency == "INR":
            return self.fetch_usd_to_inr()
        elif base_currency == "USD" and target_currency == "EUR":
            return self.fetch_usd_to_eur()
        
        return None
