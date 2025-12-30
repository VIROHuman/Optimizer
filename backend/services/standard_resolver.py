"""
Universal Standard Resolver Service.

Automatically determines the correct Electrical Design Standard for any location on Earth
using a Cascade Logic: Specific Country → Regional Block → Global Fallback.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import pycountry_convert, fallback to manual mapping if not available
try:
    import pycountry_convert as pc
    PYCOUNTRY_AVAILABLE = True
except ImportError:
    PYCOUNTRY_AVAILABLE = False
    logger.warning("pycountry_convert not available. Using manual continent mapping as fallback.")


# Comprehensive Standard Mapping Dictionary
STANDARD_MAP: Dict[str, Dict[str, Any]] = {
    # --- NORTH AMERICA ---
    'US': {'code': 'NESC', 'name': 'National Electrical Safety Code', 'frequency': 60},
    'CA': {'code': 'CSA C22.3', 'name': 'Canadian Standards Association', 'frequency': 60},
    'MX': {'code': 'NOM-001', 'name': 'Norma Oficial Mexicana', 'frequency': 60},

    # --- SOUTH AMERICA ---
    'BR': {'code': 'NBR 5422', 'name': 'ABNT (Brazil)', 'frequency': 60},
    'AR': {'code': 'AEA 95301', 'name': 'AEA (Argentina)', 'frequency': 50},
    'CL': {'code': 'NSEG 5', 'name': 'Chilean Standard', 'frequency': 50},
    'CO': {'code': 'RETIE', 'name': 'RETIE (Colombia)', 'frequency': 60},

    # --- EUROPE (Specific Overrides) ---
    'GB': {'code': 'BS EN 50341', 'name': 'British Standard', 'frequency': 50},
    'FR': {'code': 'NF EN 50341', 'name': 'AFNOR (France)', 'frequency': 50},
    'DE': {'code': 'DIN EN 50341', 'name': 'VDE (Germany)', 'frequency': 50},
    'ES': {'code': 'UNE EN 50341', 'name': 'AENOR (Spain)', 'frequency': 50},
    # EUROPE REGIONAL FALLBACK
    'EUROPE_DEFAULT': {'code': 'EN 50341', 'name': 'Eurocode (CENELEC)', 'frequency': 50},

    # --- ASIA / PACIFIC ---
    'IN': {'code': 'IS 5613', 'name': 'Indian Standard', 'frequency': 50},
    'CN': {'code': 'GB 50545', 'name': 'Chinese National Standard', 'frequency': 50},
    'JP': {'code': 'JEC 127', 'name': 'JEC (Japan)', 'frequency': 50},  # Note: 50/60Hz split, defaulting 50 for safe calc
    'KR': {'code': 'KEC', 'name': 'Korea Electro-technical Code', 'frequency': 60},
    'AU': {'code': 'AS/NZS 7000', 'name': 'Australian Standard', 'frequency': 50},
    'NZ': {'code': 'AS/NZS 7000', 'name': 'New Zealand Standard', 'frequency': 50},
    'ID': {'code': 'SNI 04', 'name': 'SNI (Indonesia)', 'frequency': 50},
    'VN': {'code': 'TCVN', 'name': 'Vietnam Standards', 'frequency': 50},
    
    # --- RUSSIA / CIS ---
    'RU': {'code': 'PUE-7', 'name': 'Electrical Installation Rules (Russia)', 'frequency': 50},
    'KZ': {'code': 'PUE', 'name': 'Kazakhstan Electrical Code', 'frequency': 50},

    # --- MIDDLE EAST (Often Mixed/IEC) ---
    'SA': {'code': 'SASO/IEC', 'name': 'Saudi Standards', 'frequency': 60},
    'AE': {'code': 'ADEWA/IEC', 'name': 'Abu Dhabi/Dubai Regulations', 'frequency': 50},

    # --- AFRICA ---
    'ZA': {'code': 'SANS 10280', 'name': 'South African National Standard', 'frequency': 50},
    'NG': {'code': 'NESIS', 'name': 'Nigerian Check', 'frequency': 50},

    # --- GLOBAL FALLBACK ---
    'WORLD_DEFAULT': {'code': 'IEC 60826', 'name': 'International Electrotechnical Commission', 'frequency': 50}
}

# Mapping from standard codes to enum-compatible strings
# This maps the detailed standard codes to the 4 main categories used by the system
STANDARD_CODE_TO_ENUM: Dict[str, str] = {
    # Indian Standards
    'IS 5613': 'IS',
    
    # IEC-based standards
    'IEC 60826': 'IEC',
    'SASO/IEC': 'IEC',
    'ADEWA/IEC': 'IEC',
    'NBR 5422': 'IEC',  # Brazil (typically IEC-based)
    'AEA 95301': 'IEC',  # Argentina
    'NSEG 5': 'IEC',  # Chile
    'RETIE': 'IEC',  # Colombia
    'SANS 10280': 'IEC',  # South Africa
    'NESIS': 'IEC',  # Nigeria
    'AS/NZS 7000': 'IEC',  # Australia/New Zealand
    'SNI 04': 'IEC',  # Indonesia
    'TCVN': 'IEC',  # Vietnam
    'GB 50545': 'IEC',  # China
    'JEC 127': 'IEC',  # Japan
    'KEC': 'IEC',  # Korea
    'PUE-7': 'IEC',  # Russia
    'PUE': 'IEC',  # Kazakhstan
    
    # Eurocode standards
    'EN 50341': 'EUROCODE',
    'BS EN 50341': 'EUROCODE',
    'NF EN 50341': 'EUROCODE',
    'DIN EN 50341': 'EUROCODE',
    'UNE EN 50341': 'EUROCODE',
    
    # ASCE/North America standards
    'NESC': 'ASCE',
    'CSA C22.3': 'ASCE',
    'NOM-001': 'ASCE',
}

# Manual continent code mapping (fallback if pycountry_convert unavailable)
# Maps ISO country codes to continent codes: EU, NA, SA, AS, AF, OC, AN
MANUAL_CONTINENT_MAP: Dict[str, str] = {
    # Europe
    'GB': 'EU', 'FR': 'EU', 'DE': 'EU', 'ES': 'EU', 'IT': 'EU', 'NL': 'EU',
    'BE': 'EU', 'PL': 'EU', 'RO': 'EU', 'PT': 'EU', 'GR': 'EU', 'AT': 'EU',
    'CH': 'EU', 'SE': 'EU', 'NO': 'EU', 'DK': 'EU', 'FI': 'EU', 'IE': 'EU',
    'CZ': 'EU', 'HU': 'EU', 'SK': 'EU', 'SI': 'EU', 'BG': 'EU', 'HR': 'EU',
    'EE': 'EU', 'LV': 'EU', 'LT': 'EU', 'LU': 'EU', 'MT': 'EU', 'CY': 'EU',
    
    # North America
    'US': 'NA', 'CA': 'NA', 'MX': 'NA', 'GT': 'NA', 'BZ': 'NA', 'SV': 'NA',
    'HN': 'NA', 'NI': 'NA', 'CR': 'NA', 'PA': 'NA', 'CU': 'NA', 'JM': 'NA',
    'HT': 'NA', 'DO': 'NA', 'PR': 'NA', 'TT': 'NA',
    
    # South America
    'BR': 'SA', 'AR': 'SA', 'CL': 'SA', 'CO': 'SA', 'PE': 'SA', 'VE': 'SA',
    'EC': 'SA', 'BO': 'SA', 'PY': 'SA', 'UY': 'SA', 'GY': 'SA', 'SR': 'SA',
    
    # Asia
    'IN': 'AS', 'CN': 'AS', 'JP': 'AS', 'KR': 'AS', 'ID': 'AS', 'VN': 'AS',
    'TH': 'AS', 'MY': 'AS', 'SG': 'AS', 'PH': 'AS', 'BD': 'AS', 'PK': 'AS',
    'LK': 'AS', 'MM': 'AS', 'KH': 'AS', 'LA': 'AS', 'MN': 'AS', 'KZ': 'AS',
    'UZ': 'AS', 'TM': 'AS', 'TJ': 'AS', 'KG': 'AS', 'AF': 'AS', 'IR': 'AS',
    'IQ': 'AS', 'SA': 'AS', 'AE': 'AS', 'QA': 'AS', 'KW': 'AS', 'BH': 'AS',
    'OM': 'AS', 'YE': 'AS', 'JO': 'AS', 'LB': 'AS', 'SY': 'AS', 'IL': 'AS',
    'PS': 'AS', 'TR': 'AS', 'RU': 'AS', 'GE': 'AS', 'AM': 'AS', 'AZ': 'AS',
    
    # Africa
    'ZA': 'AF', 'NG': 'AF', 'EG': 'AF', 'KE': 'AF', 'ET': 'AF', 'GH': 'AF',
    'TZ': 'AF', 'UG': 'AF', 'DZ': 'AF', 'SD': 'AF', 'MA': 'AF', 'AO': 'AF',
    'MZ': 'AF', 'MG': 'AF', 'CM': 'AF', 'CI': 'AF', 'NE': 'AF', 'BF': 'AF',
    'ML': 'AF', 'MW': 'AF', 'ZM': 'AF', 'SN': 'AF', 'TD': 'AF', 'SO': 'AF',
    'ZW': 'AF', 'GN': 'AF', 'RW': 'AF', 'BJ': 'AF', 'TN': 'AF', 'BI': 'AF',
    'SS': 'AF', 'TG': 'AF', 'SL': 'AF', 'LY': 'AF', 'LR': 'AF', 'MR': 'AF',
    
    # Oceania
    'AU': 'OC', 'NZ': 'OC', 'PG': 'OC', 'FJ': 'OC', 'SB': 'OC', 'NC': 'OC',
    'PF': 'OC', 'VU': 'OC', 'WS': 'OC', 'KI': 'OC', 'FM': 'OC', 'TO': 'OC',
    'MH': 'OC', 'PW': 'OC', 'NR': 'OC', 'TV': 'OC',
}


class StandardResolver:
    """
    Universal Standard Resolver with Cascade Logic.
    
    Resolves electrical design standards using:
    1. Specific Country Match
    2. Regional Block Match (by continent)
    3. Global Fallback (IEC)
    """
    
    def __init__(self):
        """Initialize the StandardResolver."""
        self.standard_map = STANDARD_MAP
        self.continent_map = MANUAL_CONTINENT_MAP
    
    def _get_continent_code(self, country_code: str) -> Optional[str]:
        """
        Get continent code from country code.
        
        Args:
            country_code: ISO 2-letter country code (e.g., 'US', 'IN', 'GB')
            
        Returns:
            Continent code ('EU', 'NA', 'SA', 'AS', 'AF', 'OC') or None
        """
        if not country_code:
            return None
        
        country_code = country_code.upper()
        
        # Try pycountry_convert first if available
        if PYCOUNTRY_AVAILABLE:
            try:
                # Get continent code from country code
                # pycountry_convert uses: country_alpha2_to_continent_code(country_code)
                continent_code = pc.country_alpha2_to_continent_code(country_code)
                return continent_code
            except (KeyError, AttributeError, ValueError):
                # Fallback to manual mapping
                pass
        
        # Fallback to manual mapping
        return self.continent_map.get(country_code)
    
    def resolve(self, country_code: Optional[str]) -> Dict[str, Any]:
        """
        Resolve design standard using cascade logic.
        
        Step 1: Specific Match - Check if country_code exists in STANDARD_MAP
        Step 2: Regional Match - Convert to continent and use regional default
        Step 3: Global Match - Return WORLD_DEFAULT (IEC)
        
        Args:
            country_code: ISO 2-letter country code (e.g., 'US', 'IN', 'GB')
                          Can be None for unknown locations
        
        Returns:
            Dictionary with 'code', 'name', and 'frequency' keys
            Never returns None - always falls back to WORLD_DEFAULT
        """
        if not country_code:
            logger.debug("No country code provided, using WORLD_DEFAULT")
            return self.standard_map['WORLD_DEFAULT']
        
        country_code = country_code.upper()
        
        # Step 1: Specific Match
        if country_code in self.standard_map:
            standard_info = self.standard_map[country_code]
            logger.info(f"Specific match found for {country_code}: {standard_info['code']}")
            return standard_info
        
        # Step 2: Regional Match
        continent_code = self._get_continent_code(country_code)
        
        if continent_code == 'EU':
            # Europe regional fallback
            logger.info(f"Regional match (Europe) for {country_code}: {self.standard_map['EUROPE_DEFAULT']['code']}")
            return self.standard_map['EUROPE_DEFAULT']
        
        elif continent_code == 'NA':
            # North America - use US standard as common fallback for Caribbean/Central America
            logger.info(f"Regional match (North America) for {country_code}: {self.standard_map['US']['code']}")
            return self.standard_map['US']
        
        # Step 3: Global Match (for all other continents or unknown)
        logger.info(f"Global fallback for {country_code}: {self.standard_map['WORLD_DEFAULT']['code']}")
        return self.standard_map['WORLD_DEFAULT']
    
    def get_enum_compatible_code(self, country_code: Optional[str]) -> str:
        """
        Get enum-compatible standard code (IS, IEC, EUROCODE, ASCE).
        
        This method resolves the standard and maps it to one of the 4 main categories
        used by the DesignStandard enum.
        
        Args:
            country_code: ISO 2-letter country code
            
        Returns:
            One of: 'IS', 'IEC', 'EUROCODE', 'ASCE'
        """
        standard_info = self.resolve(country_code)
        standard_code = standard_info['code']
        
        # Map to enum-compatible code
        enum_code = STANDARD_CODE_TO_ENUM.get(standard_code, 'IEC')  # Default to IEC if unknown
        
        logger.debug(f"Mapped {standard_code} to enum code: {enum_code}")
        return enum_code
    
    def get_full_standard_info(self, country_code: Optional[str]) -> Dict[str, Any]:
        """
        Get full standard information including code, name, and frequency.
        
        Args:
            country_code: ISO 2-letter country code
            
        Returns:
            Dictionary with 'code', 'name', and 'frequency' keys
        """
        return self.resolve(country_code)


# Global instance for convenience
_standard_resolver = StandardResolver()


def resolve_standard(country_code: Optional[str]) -> str:
    """
    Convenience function to resolve standard to enum-compatible code.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        Enum-compatible code: 'IS', 'IEC', 'EUROCODE', or 'ASCE'
    """
    return _standard_resolver.get_enum_compatible_code(country_code)


def resolve_standard_full(country_code: Optional[str]) -> Dict[str, Any]:
    """
    Convenience function to resolve full standard information.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        Dictionary with 'code', 'name', and 'frequency' keys
    """
    return _standard_resolver.get_full_standard_info(country_code)

