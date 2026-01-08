"""
Market Oracle Service - Hybrid Intelligence Approach.

Uses AI (Groq) to determine currency code, risk factors, and local context,
but uses real exchange rate APIs for accurate currency conversion.

This combines:
- AI (Brain): Determines currency code, risk factors, regional context
- API (Tool): Fetches live exchange rates from financial APIs
- Math: Combines them for accurate pricing
"""

import os
import json
import logging
import requests
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# In-memory cache to avoid redundant API calls
_CACHE: Dict[str, Dict] = {}

# Base Global Rates (USD) - The "Anchor" Prices
BASE_STEEL_USD_PER_TONNE = 1200.0  # $1,200 per tonne
BASE_CONCRETE_USD_PER_M3 = 130.0   # $130 per m³

# Fallback rates (Global Average) if API fails
FALLBACK_RATES = {
    "steel_price_usd": 1200.0,  # USD per tonne
    "concrete_price_usd": 120.0,  # USD per m³
    "labor_factor": 2.0,
    "logistics_factor": 1.3,
    "currency_symbol": "$",
    "currency_code": "USD",
    "market_note": "Using fallback rates (API unavailable)",
    "source": "fallback"
}


def get_real_exchange_rate(target_currency: str) -> float:
    """
    Fetches live USD -> Target currency conversion rate.
    
    Uses open.er-api.com (free, no key required for basic USD rates).
    
    Args:
        target_currency: ISO currency code (e.g., "INR", "AFN", "SAR")
        
    Returns:
        Exchange rate (1 USD = X target_currency)
    """
    if target_currency == "USD":
        return 1.0
    
    try:
        # Free reliable API (No key required for basic USD rates)
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data.get('rates', {}).get(target_currency, None)
        
        if rate:
            logger.debug(f"Fetched exchange rate: 1 USD = {rate} {target_currency}")
            return float(rate)
        else:
            logger.warning(f"Currency {target_currency} not found in exchange rate API")
            # Emergency fallback for common currencies
            fallback_rates = {
                "INR": 85.0,
                "EUR": 0.92,
                "GBP": 0.79,
                "AFN": 70.0,
                "SAR": 3.75,
            }
            return fallback_rates.get(target_currency, 1.0)
            
    except requests.RequestException as e:
        logger.warning(f"Exchange rate API failed: {e}. Using fallback.")
        # Emergency fallback for common currencies
        fallback_rates = {
            "INR": 85.0,
            "EUR": 0.92,
            "GBP": 0.79,
            "AFN": 70.0,
            "SAR": 3.75,
        }
        return fallback_rates.get(target_currency, 1.0)
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return 1.0


def get_rates(country: str, region: Optional[str] = None) -> Dict:
    """
    Get real-time market rates using hybrid AI + API approach.
    
    Process:
    1. AI (Groq) determines currency code, risk factors, and local context
    2. API (open.er-api.com) fetches live exchange rate
    3. Math combines them for accurate pricing
    
    Args:
        country: Country name (e.g., "India", "Afghanistan", "Saudi Arabia")
        region: Optional region/state name for more granular pricing
        
    Returns:
        Dictionary with keys:
        - steel_price_usd: Steel price per tonne in USD
        - concrete_price_usd: Concrete price per m³ in USD
        - labor_factor: Labor cost multiplier (1.0 = baseline)
        - logistics_factor: Logistics/transport cost multiplier (1.0 = baseline)
        - currency_symbol: Currency symbol (e.g., "$", "₹", "€")
        - currency_code: ISO currency code (e.g., "USD", "INR", "EUR")
        - market_note: Human-readable note about the market conditions
        - source: "groq" or "fallback"
    """
    # Create cache key
    location_str = f"{region}, {country}" if region else country
    cache_key = location_str.lower().strip()
    
    # Check cache first
    if cache_key in _CACHE:
        logger.debug(f"MarketOracle: Using cached rates for {location_str}")
        return _CACHE[cache_key]
    
    # Get API key from environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not found in environment. Using fallback rates.")
        _CACHE[cache_key] = FALLBACK_RATES.copy()
        return FALLBACK_RATES.copy()
    
    try:
        logger.info(f"🤖 MarketOracle: Analyzing {location_str}...")
        
        # Step 1: Ask AI for the 'Strategy' (Currency Code + Risk Factors)
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
        prompt = f"""Analyze construction costs and design standards for a Transmission Line project in: {location_str}.

Return ONLY valid JSON (no markdown, no code blocks) with these exact keys:
{{
    "currency_code": "ISO currency code (e.g., INR, USD, AFN, SAR, EUR, GBP)",
    "currency_symbol": "Currency symbol (e.g., ₹, $, ؋, ﷼, €, £)",
    "labor_risk_factor": <Float: 1.0 for safe/developed, 1.2-1.5 for developing, 1.5+ for conflict zones>,
    "logistics_markup": <Float: 1.0 for flat/easy access, 1.2-1.3 for moderate, 1.3+ for mountains/remote>,
    "governing_standard": "Local design standard code (e.g., 'IS' for India, 'IEC' for international, 'WAPDA' for Pakistan, 'NESC' for USA, 'EN 50341' for Europe, 'AS/NZS' for Australia)",
    "design_stringency_factor": <Float: 1.0 for standard compliance, 1.1-1.2 for stricter local standards (e.g., WAPDA), 0.9-1.0 for relaxed standards>,
    "market_note": "<Brief 20-25 word single sentence summary of local market conditions>"
}}

Consider:
- Currency: Use the official currency of the country (India=INR, Afghanistan=AFN, Saudi Arabia=SAR, etc.)
- Labor risk: Higher in conflict zones, lower in developed countries
- Logistics: Higher in remote/mountainous areas, lower in flat/accessible regions
- Governing standard: Identify the actual local standard (e.g., Pakistan uses WAPDA, not just IEC)
- Design stringency: Some local standards require heavier structures (e.g., WAPDA 1.15x, stricter seismic zones 1.2x)
- Market conditions: Consider local economic factors

Return ONLY the JSON object, nothing else."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a construction cost analyst. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent, factual responses
            max_tokens=300,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        # Extract JSON from response
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        ai_strategy = json.loads(content)
        
        # Validate required fields
        currency_code = ai_strategy.get("currency_code", "USD")
        currency_symbol = ai_strategy.get("currency_symbol", "$")
        labor_risk_factor = float(ai_strategy.get("labor_risk_factor", 1.0))
        logistics_markup = float(ai_strategy.get("logistics_markup", 1.0))
        governing_standard = ai_strategy.get("governing_standard", "IEC")  # Default to IEC if not provided
        design_stringency_factor = float(ai_strategy.get("design_stringency_factor", 1.0))
        market_note = ai_strategy.get("market_note", f"Real-time rates for {location_str}")
        
        # Validate ranges
        labor_risk_factor = max(0.5, min(3.0, labor_risk_factor))  # Clamp to reasonable range
        logistics_markup = max(0.8, min(2.5, logistics_markup))  # Clamp to reasonable range
        design_stringency_factor = max(0.7, min(2.0, design_stringency_factor))  # Clamp to reasonable range (0.7x to 2.0x)
        
        # Step 2: Execute the 'Tool' (Fetch Live Exchange Rate)
        exchange_rate = get_real_exchange_rate(currency_code)
        
        # Step 3: Calculate Final Rates with Currency Conversion
        # Base prices are in USD per tonne (steel) and USD per m³ (concrete)
        risk_multiplier = labor_risk_factor * logistics_markup
        
        # Steel: Base price * logistics markup (accounts for transport/access difficulty)
        # Keep in USD per tonne for cost_engine calculations
        steel_price_usd_per_tonne = BASE_STEEL_USD_PER_TONNE * logistics_markup
        
        # --- THE FIX: FORCE CURRENCY AWARENESS ---
        # Calculate local currency price per kg for display
        # Base Price is $1,200 USD per Tonne = $1.20 USD per kg
        base_steel_usd_per_kg = BASE_STEEL_USD_PER_TONNE / 1000.0  # $1.20 / kg
        
        # Convert to Local Currency per kg
        local_steel_price_per_kg = base_steel_usd_per_kg * exchange_rate * logistics_markup
        
        # Sanity check: If calculated rate is abnormally low, exchange rate API likely failed
        # For INR, expect ~₹85-102 per kg (1.20 USD × 85-85 exchange rate × markup)
        if currency_code == "INR" and local_steel_price_per_kg < 50.0:
            logger.warning(
                f"MarketOracle: Calculated INR steel price per kg ({local_steel_price_per_kg:.2f}) is too low. "
                f"Exchange rate may have failed. Using fallback."
            )
            # Fallback to known INR rate: $1.20/kg × 85 INR/USD × markup
            local_steel_price_per_kg = 1.20 * 85.0 * logistics_markup
        
        # Similar check for other currencies
        if currency_code != "USD" and exchange_rate == 1.0:
            logger.warning(
                f"MarketOracle: Exchange rate for {currency_code} returned 1.0 (likely API failure). "
                f"Using fallback rates."
            )
            # Use fallback exchange rates
            fallback_rates = {
                "INR": 85.0,
                "EUR": 0.92,
                "GBP": 0.79,
                "AFN": 70.0,
                "SAR": 3.75,
            }
            fallback_rate = fallback_rates.get(currency_code, 1.0)
            local_steel_price_per_kg = base_steel_usd_per_kg * fallback_rate * logistics_markup
        
        # Concrete: Base price * (labor risk * logistics markup)
        # Keep in USD per m³ for cost_engine calculations
        concrete_price_usd_per_m3 = BASE_CONCRETE_USD_PER_M3 * risk_multiplier
        
        # Convert concrete to local currency per m³
        local_concrete_price_per_m3 = BASE_CONCRETE_USD_PER_M3 * exchange_rate * risk_multiplier
        
        # Calculate local price per tonne (for frontend display)
        local_steel_price_per_tonne = local_steel_price_per_kg * 1000.0
        
        # Prepare final response
        rates = {
            "steel_price_usd": round(steel_price_usd_per_tonne, 2),  # Per tonne (USD) - for cost_engine calculations
            "steel_price_local_per_kg": round(local_steel_price_per_kg, 2),  # Per kg (local currency) - for reference
            "steel_price_local_per_tonne": round(local_steel_price_per_tonne, 2),  # Per tonne (local currency) - for frontend display
            "concrete_price_usd": round(concrete_price_usd_per_m3, 2),  # Per m³ (USD) - for cost_engine calculations
            "concrete_price_local_per_m3": round(local_concrete_price_per_m3, 2),  # Per m³ (local currency) - for frontend display
            "labor_factor": round(labor_risk_factor, 2),
            "logistics_factor": round(logistics_markup, 2),
            "governing_standard": governing_standard,  # AI-detected local standard (e.g., "WAPDA", "IS", "IEC")
            "design_stringency_factor": round(design_stringency_factor, 3),  # Factor to adjust steel cost (e.g., 1.15 for 15% heavier)
            "currency_symbol": currency_symbol,
            "currency_code": currency_code,
            "market_note": market_note,
            "source": "groq",
            "exchange_rate": exchange_rate,  # For reference
        }
        
        # Cache the result
        _CACHE[cache_key] = rates.copy()
        logger.info(f"✅ MarketOracle: Successfully fetched rates for {location_str} ({currency_code})")
        
        return rates
        
    except json.JSONDecodeError as e:
        logger.error(f"MarketOracle: Failed to parse JSON response: {e}. Using fallback rates.")
        _CACHE[cache_key] = FALLBACK_RATES.copy()
        return FALLBACK_RATES.copy()
        
    except Exception as e:
        logger.error(f"MarketOracle: API call failed for {location_str}: {e}. Using fallback rates.")
        _CACHE[cache_key] = FALLBACK_RATES.copy()
        return FALLBACK_RATES.copy()


def clear_cache():
    """Clear the in-memory cache. Useful for testing or forcing fresh data."""
    global _CACHE
    _CACHE.clear()
    logger.info("MarketOracle: Cache cleared")


def get_cache_stats() -> Dict:
    """Get cache statistics for monitoring."""
    return {
        "cached_locations": len(_CACHE),
        "cache_keys": list(_CACHE.keys())
    }
