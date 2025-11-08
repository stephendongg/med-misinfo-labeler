"""FDA drug approval lookup module.

Provides functions to check if a drug is FDA approved using the OpenFDA API.
"""

import requests
from typing import Dict, List, Optional

FDA_DRUG_API = "https://api.fda.gov/drug/drugsfda.json"


def fetch_fda_results(drug_name: str) -> List[Dict]:
    """Query FDA API for drug approval information.
    
    Args:
        drug_name: Name of the drug to search for
        
    Returns:
        List of FDA approval records, or empty list if not found
    """
    params = {
        "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
        "limit": 1,
    }
    response = requests.get(FDA_DRUG_API, params=params, timeout=10)
    
    # Handle 404 as "no results" rather than an error
    if response.status_code == 404:
        return []
    
    response.raise_for_status()
    return response.json().get("results", [])


def check_fda_approval(drug_name: str) -> Dict:
    """Check if a drug is FDA approved.
    
    Args:
        drug_name: Name of the drug to check
        
    Returns:
        Dictionary with:
            - 'approved': bool indicating approval status
            - 'brand_name', 'generic_name', 'manufacturer': Optional[str] if approved
            - 'error': Optional[str] if lookup failed
    """
    try:
        results = fetch_fda_results(drug_name)
        if not results:
            return {"approved": False}

        openfda = results[0].get("openfda", {})
        return {
            "approved": True,
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "manufacturer": (openfda.get("manufacturer_name") or [None])[0],
        }
    except Exception as exc:
        return {"approved": False, "error": str(exc)}