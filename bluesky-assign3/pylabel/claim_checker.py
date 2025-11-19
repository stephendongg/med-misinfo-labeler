"""Claim extraction and fact-checking module."""

from typing import Dict, Optional
from openai import OpenAI
import json
import time

from .fda_lookup import get_fda_labeling

try:
    from .automated_labeler import LLM_MODEL, FACT_CHECK_THRESHOLD
except ImportError:
    LLM_MODEL = "gpt-5-mini"
    FACT_CHECK_THRESHOLD = 0.5


def extract_claim(text: str, drug_name: str) -> Dict:
    """Extract indication claim (what condition drug treats).
    
    Args:
        text: Post content text
        drug_name: Name of the drug
        
    Returns:
        Dict with keys: "has_claim" (bool), "claim_text" (str)
    """
    start = time.time()
    
    prompt = f"""Does this post make a specific claim about what condition {drug_name} treats?

Post: {text}

Extract ONLY claims about what disease/condition the drug treats. Ignore dosage, safety, interactions, side effects.

Output JSON:
{{"has_claim": true/false, "claim_text": "claim text or empty string"}}"""
    
    client = OpenAI()
    response = client.responses.create(model=LLM_MODEL, input=prompt)
    
    elapsed = time.time() - start
    print(f"    ⏱️  extract_claim({drug_name}): {elapsed:.2f}s")
    
    try:
        return json.loads(response.output_text.strip())
    except json.JSONDecodeError:
        return {"has_claim": False, "claim_text": ""}


def fact_check_claim(claim_text: str, drug_name: str, threshold: Optional[float] = None) -> Dict:
    """Fact-check if claim matches FDA-approved indication.
    
    Args:
        claim_text: The claim to fact-check
        drug_name: Name of the drug
        threshold: Confidence threshold for support (default: FACT_CHECK_THRESHOLD)
        
    Returns:
        Dict with keys: "supported" (bool/None), "evidence" (str)
    """
    if threshold is None:
        threshold = FACT_CHECK_THRESHOLD
    
    start = time.time()
    
    labeling = get_fda_labeling(drug_name)
    indications = labeling.get("indications", [])
    
    if not indications:
        elapsed = time.time() - start
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s")
        return {"supported": None, "evidence": "No FDA indication data"}
    
    fda_text = "\n".join(f"- {ind}" for ind in indications)
    if len(fda_text) > 1500:
        fda_text = fda_text[:1500] + "\n... (truncated)"
    
    prompt = f"""Claim: {claim_text}

FDA-approved uses for {drug_name}:
{fda_text}

Does the claim match FDA uses? Output JSON:
{{"confidence": 0.0-1.0, "contradicted": true/false, "evidence": "brief"}}"""
    
    client = OpenAI()
    response = client.responses.create(model=LLM_MODEL, input=prompt)
    
    elapsed = time.time() - start
    
    try:
        result = json.loads(response.output_text.strip())
        if result.get("contradicted"):
            print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s")
            return {"supported": False, "evidence": result.get("evidence", "")}
        
        confidence = float(result.get("confidence", 0.0))
        supported = confidence >= threshold
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s")
        return {
            "supported": supported,
            "evidence": result.get("evidence", "")
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s")
        return {"supported": None, "evidence": "Could not verify claim"}