"""Claim extraction and fact-checking module."""

from typing import Dict
from openai import OpenAI
import json
import time

from .fda_lookup import get_fda_labeling


def extract_claim(text: str, drug_name: str, llm_model: str) -> Dict:
    """Extract indication claim (what condition drug treats).
    
    Args:
        text: Post content text
        drug_name: Name of the drug
        llm_model: LLM model to use
        
    Returns:
        Dict with keys: "has_claim" (bool), "claim_confidence" (float), "claim_text" (str)
    """
    start = time.time()
    
    prompt = f"""Does this post make a specific claim about what condition {drug_name} treats?

Post: {text}

Extract ONLY explicit claims about what disease/condition the drug treats. 
- Ignore mentions of conditions in context (e.g., "because he had seizures" is NOT a claim)
- Ignore dosage, timing, schedule, safety, interactions, side effects
- Only extract if the post explicitly states or implies what condition the drug is used to treat

Output JSON:
{{"has_claim": true/false, "claim_confidence": 0.0-1.0, "claim_text": "claim text or empty string"}}"""
    
    client = OpenAI()
    response = client.responses.create(model=llm_model, input=prompt)
    
    elapsed = time.time() - start
    
    try:
        result = json.loads(response.output_text.strip())
        confidence = result.get("claim_confidence", 0.0)
        print(f"    ⏱️  extract_claim({drug_name}): {elapsed:.2f}s (confidence: {confidence:.2f})")
        return result
    except (json.JSONDecodeError, ValueError, KeyError):
        print(f"    ⏱️  extract_claim({drug_name}): {elapsed:.2f}s (parse error)")
        return {"has_claim": False, "claim_confidence": 0.0, "claim_text": ""}


def fact_check_claim(claim_text: str, drug_name: str, threshold: float, llm_model: str) -> Dict:
    """Fact-check if claim matches FDA-approved indication.
    
    Args:
        claim_text: The claim to fact-check
        drug_name: Name of the drug
        threshold: Confidence threshold for determining if claim is supported
        llm_model: LLM model to use for fact-checking
        
    Returns:
        Dict with keys: "supported" (bool/None), "evidence" (str)
    """
    start = time.time()
    
    labeling = get_fda_labeling(drug_name)
    indications = labeling.get("indications", [])
    
    if not indications:
        elapsed = time.time() - start
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s (no FDA data)")
        return {"supported": None, "evidence": "No FDA indication data"}
    
    fda_text = "\n".join(f"- {ind}" for ind in indications)
    if len(fda_text) > 1500:
        fda_text = fda_text[:1500] + "\n... (truncated)"
    
    prompt = f"""Claim: {claim_text}

FDA-approved uses for {drug_name}:
{fda_text}

How well does the claim match FDA-approved uses? Rate confidence 0.0-1.0.
Output JSON:
{{"confidence": 0.0-1.0, "evidence": "brief explanation"}}"""
    
    client = OpenAI()
    response = client.responses.create(model=llm_model, input=prompt)
    
    elapsed = time.time() - start
    
    try:
        result = json.loads(response.output_text.strip())
        confidence = float(result.get("confidence", 0.0))
        supported = confidence >= threshold
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s (confidence: {confidence:.2f})")
        return {
            "supported": supported,
            "evidence": result.get("evidence", "")
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s (parse error)")
        return {"supported": None, "evidence": "Could not verify claim"}