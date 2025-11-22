"""FDA drug approval lookup module.

Provides functions to check if a drug is FDA approved using the OpenFDA API.
"""

import requests
import time
from functools import lru_cache
from typing import Dict, List

FDA_DRUG_API = "https://api.fda.gov/drug/drugsfda.json"

FDA_LABEL_API = "https://api.fda.gov/drug/label.json"

def fetch_fda_results(drug_name: str) -> List[Dict]:
    """Query FDA drugsfda API for drug approval info.
    
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
    
    if response.status_code == 404:
        return []
    
    response.raise_for_status()
    return response.json().get("results", [])


def get_generic_name_from_label(drug_name: str) -> str:
    """Use label API to translate brand name to generic name.
    
    Args:
        drug_name: Brand or generic name of the drug
        
    Returns:
        Generic name if found, otherwise the original drug_name
    """
    try:
        params = {
            "search": f'openfda.brand_name:{drug_name}',
            "limit": 1
        }
        response = requests.get(FDA_LABEL_API, params=params, timeout=10)
        
        if response.status_code != 200:
            return drug_name
        
        results = response.json().get("results", [])
        if not results:
            return drug_name
        
        openfda = results[0].get("openfda", {})
        generic_names = openfda.get("generic_name", [])
        
        if generic_names and generic_names[0]:
            return generic_names[0]
        
        return drug_name
    except Exception:
        return drug_name


@lru_cache(maxsize=200)
def check_fda_approval(drug_name: str) -> Dict:
    """Check if drug is FDA approved using two-step fallback strategy (cached).
    
    Strategy:
    1. Try drugsfda API with original name (most authoritative)
    2. If not found, use label API to get generic name
    3. Try drugsfda API again with generic name
    4. If still not found, mark as unapproved
    
    Args:
        drug_name: Name of the drug to check (brand or generic)
        
    Returns:
        Dict with keys: "approved" (bool), "brand_name", "generic_name", "manufacturer" (optional),
        "error" (optional str if lookup failed)
    """
    start = time.time()
    try:
        # Step 1: Try drugsfda with original name
        results = fetch_fda_results(drug_name)
        
        if not results:
            # Step 2: Get generic name from label API
            generic_name = get_generic_name_from_label(drug_name)
            
            # Step 3: If we got a different name, try drugsfda again
            if generic_name and generic_name.lower() != drug_name.lower():
                results = fetch_fda_results(generic_name)
        
        # If still no results, drug is not approved
        if not results:
            elapsed = time.time() - start
            print(f"    ⏱️  check_fda_approval({drug_name}): {elapsed:.2f}s")
            return {"approved": False}

        # Found approval record
        openfda = results[0].get("openfda", {})
        elapsed = time.time() - start
        print(f"    ⏱️  check_fda_approval({drug_name}): {elapsed:.2f}s")
        return {
            "approved": True,
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "manufacturer": (openfda.get("manufacturer_name") or [None])[0],
        }
    except Exception as exc:
        elapsed = time.time() - start
        print(f"    ⏱️  check_fda_approval({drug_name}): {elapsed:.2f}s")
        return {"approved": False, "error": str(exc)}

@lru_cache(maxsize=200)
def get_fda_labeling(drug_name: str) -> Dict:
    """Get FDA indications for fact-checking (cached).
    
    Args:
        drug_name: Name of the drug (substance, brand, or generic name)
        
    Returns:
        Dict with key "indications" containing list of indication strings.
        Returns empty dict if no labels found.
    """    
    start = time.time()
    
    params = {
        "search": f'openfda.substance_name:"{drug_name}" OR openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
        "limit": 1
    }
    response = requests.get(FDA_LABEL_API, params=params, timeout=10)
    
    if response.status_code != 200:
        elapsed = time.time() - start
        print(f"    ⏱️  get_fda_labeling({drug_name}): {elapsed:.2f}s")
        return {}
    
    response_data = response.json()
    label_results = response_data.get("results", [])
    
    if not label_results:
        elapsed = time.time() - start
        print(f"    ⏱️  get_fda_labeling({drug_name}): {elapsed:.2f}s")
        return {}

    label = label_results[0]
    indications = label.get("indications_and_usage", [])

    elapsed = time.time() - start
    print(f"    ⏱️  get_fda_labeling({drug_name}): {elapsed:.2f}s")
    
    return {"indications": indications}
    