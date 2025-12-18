"""
Cost Index Crawler Module.

Fetches public cost indices for steel, cement, labor, and fuel.
Outputs RAW data only - never normalizes or applies automatically.

CRITICAL: All fetched indices are CANDIDATE UPDATES ONLY.
They require explicit human approval before use.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
import json


@dataclass
class CostIndexData:
    """Raw cost index data point."""
    
    index_type: str  # "steel", "cement", "labor", "fuel"
    region: str
    value: float
    unit: str  # "USD/tonne", "USD/m³", "USD/hour", "index", etc.
    source: str  # Data source URL or identifier
    timestamp: datetime
    metadata: Dict[str, str]  # Additional metadata


class CostCrawler:
    """
    Crawler for public cost indices.
    
    Fetches data from public sources and returns RAW data only.
    Never normalizes or applies data automatically.
    
    IMPORTANT: Fetched indices are CANDIDATE UPDATES.
    They must be approved via Validator before use.
    """
    
    def __init__(self):
        """Initialize the cost crawler."""
        self.sources = {
            "steel": [
                "https://worldsteel.org",
                "https://www.metal.com",
            ],
            "cement": [
                "https://www.worldbank.org/en/research/commodity-markets",
            ],
            "labor": [
                "https://ilostat.ilo.org/data/",
            ],
            "fuel": [
                "https://www.eia.gov/opendata/",
            ],
        }
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TransmissionTowerOptimizer/1.0"
        })
    
    def fetch_steel_index(
        self,
        region: str
    ) -> Optional[CostIndexData]:
        """
        Fetch steel cost index for a region.
        
        Args:
            region: Region identifier (e.g., "india", "europe", "usa")
            
        Returns:
            CostIndexData if available, None otherwise
            
        Note:
            This is a CANDIDATE UPDATE. It requires approval before use.
        """
        try:
            # World Steel Association
            # Note: WSA may require membership or API key
            # TODO: Implement WSA API call when credentials are available
            
            # Alternative: Metal.com API (if available)
            # metal_url = "https://api.metal.com/v1/prices/steel"
            # response = self.session.get(metal_url, params={"region": region})
            # if response.status_code == 200:
            #     data = response.json()
            #     return CostIndexData(
            #         index_type="steel",
            #         region=region,
            #         value=float(data["price"]),
            #         unit="USD/tonne",
            #         source="Metal.com",
            #         timestamp=datetime.now(),
            #         metadata={"metal_id": data.get("id", "")}
            #     )
            
            return None
            
        except Exception as e:
            return None
    
    def fetch_cement_index(
        self,
        region: str
    ) -> Optional[CostIndexData]:
        """
        Fetch cement cost index for a region.
        
        Args:
            region: Region identifier
            
        Returns:
            CostIndexData if available, None otherwise
        """
        try:
            # World Bank Commodity Prices API
            # Indicator: Cement price index
            wb_url = "https://api.worldbank.org/v2/indicator/PNRG.CEMT.US"
            
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
                
                if len(data) >= 2 and len(data[1]) > 0:
                    value = data[1][0].get("value")
                    if value:
                        return CostIndexData(
                            index_type="cement",
                            region=region,
                            value=float(value),
                            unit="index",
                            source="WorldBank",
                            timestamp=datetime.now(),
                            metadata={
                                "wb_indicator": "PNRG.CEMT.US",
                                "date": data[1][0].get("date", "")
                            }
                        )
            
            return None
            
        except Exception as e:
            return None
    
    def fetch_labor_index(
        self,
        region: str
    ) -> Optional[CostIndexData]:
        """
        Fetch labor cost index for a region.
        
        Args:
            region: Region identifier
            
        Returns:
            CostIndexData if available, None otherwise
        """
        try:
            # ILOSTAT API
            # Note: ILOSTAT may require registration
            # TODO: Implement ILOSTAT API call when credentials are available
            # ilostat_url = "https://www.ilo.org/ilostatapi/"
            # response = self.session.get(ilostat_url, params={"indicator": "labor_cost"})
            
            return None
            
        except Exception as e:
            return None
    
    def fetch_fuel_index(
        self,
        region: str
    ) -> Optional[CostIndexData]:
        """
        Fetch fuel cost index for a region.
        
        Args:
            region: Region identifier
            
        Returns:
            CostIndexData if available, None otherwise
        """
        try:
            import os
            
            # EIA Open Data API
            # Diesel fuel price index (common for construction logistics)
            eia_url = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
            
            # EIA API key - check environment variable first, then use default
            api_key = os.getenv("EIA_API_KEY", "i1wFFd4TTghjk8S24G1fTf2ugFnDmnFj1c3RNtWB")
            
            if not api_key:
                return None
            
            # Fetch diesel fuel prices (most relevant for construction logistics)
            # Series ID for U.S. No 2 Diesel Retail Prices
            response = self.session.get(
                eia_url,
                params={
                    "api_key": api_key,
                    "frequency": "monthly",
                    "data[0]": "value",
                    "facets[series][]": "PET.EMD_EPD2D_PTE_NUS_DPG.M",  # Diesel retail price
                    "length": 1,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse EIA response
                if "response" in data and "data" in data["response"]:
                    data_points = data["response"]["data"]
                    if len(data_points) > 0:
                        latest = data_points[0]
                        value = latest.get("value")
                        period = latest.get("period", "")
                        
                        if value:
                            return CostIndexData(
                                index_type="fuel",
                                region=region,
                                value=float(value),
                                unit="USD/gallon",
                                source="EIA",
                                timestamp=datetime.now(),
                                metadata={
                                    "eia_series": "PET.EMD_EPD2D_PTE_NUS_DPG.M",
                                    "period": period,
                                    "fuel_type": "diesel"
                                }
                            )
            
            return None
            
        except Exception as e:
            # Log error but don't fail - return None
            return None
    
    def fetch_all_indices(
        self,
        region: str
    ) -> List[CostIndexData]:
        """
        Fetch all available cost indices for a region.
        
        Args:
            region: Region identifier
            
        Returns:
            List of CostIndexData objects (may be empty)
            
        Note:
            All fetched indices are CANDIDATE UPDATES.
            They require approval before use.
        """
        indices = []
        
        for fetch_func in [
            self.fetch_steel_index,
            self.fetch_cement_index,
            self.fetch_labor_index,
            self.fetch_fuel_index,
        ]:
            data = fetch_func(region)
            if data:
                indices.append(data)
        
        return indices
