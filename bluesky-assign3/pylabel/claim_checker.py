"""Claim extraction and fact-checking module."""

from typing import Dict
from openai import OpenAI
import json
import time

from .fda_lookup import get_fda_labeling


def extract_claim(text: str, drug_name: str, llm_model: str) -> Dict:
    """Extract indication claim(s) (what condition(s) drug treats).
    
    Args:
        text: Post content text
        drug_name: Name of the drug
        llm_model: LLM model to use
        
    Returns:
        Dict with keys: "has_claim" (bool), "claim_confidence" (float), "claim_text" (str)
    """
    start = time.time()
    
    prompt = f"""Does this post make a TREATMENT CLAIM about what condition {drug_name} treats?

POST TEXT:
{text}

REQUIRES EXPLICIT TREATMENT LANGUAGE:
The post MUST explicitly state the drug treats/cures/helps with a condition.
Examples of treatment language: "treats", "cures", "used for", "prescribed for", "helps with", "indicated for"

EXTRACT AS CLAIM:
- "{drug_name} treats diabetes"
- "prescribed {drug_name} for my arthritis"  
- "{drug_name} helps reduce fever"

DO NOT EXTRACT:
- Personal stories that mention condition but don't claim treatment (e.g., "I have diabetes and take {drug_name}")
- Advocacy/pricing discussions (e.g., "{drug_name} should be free")
- Drug and condition mentioned separately without treatment link

If the post claims multiple conditions, include ALL of them in claim_text separated by commas.

CONFIDENCE:
- 0.9-1.0: Explicit treatment verb + condition
- 0.7-0.8: Strongly implied treatment claim
- 0.0-0.6: No clear treatment claim → set has_claim=false

Output ONLY JSON:
{{"has_claim": true/false, "claim_confidence": 0.0-1.0, "claim_text": "condition(s)"}}"""
    
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
    
    prompt = f"""Verify if a claimed medical indication matches FDA-approved indications.

CLAIMED INDICATION: "{claim_text}"

FDA-APPROVED INDICATIONS for {drug_name}:
{fda_text}

TASK: Determine whether the CLAIMED INDICATION matches any FDA-approved indication,
even if the wording is different.

IMPORTANT:
- FDA uses clinical terminology (e.g., "primary hyperlipidemia").
- Patients use lay terms (e.g., "high cholesterol").
- If the lay term clearly refers to the same medical condition as the FDA term,
then it IS a supported indication.

MATCHING RULES:
- Count synonyms, layperson equivalents, and clinically equivalent phrases as matches.
- Examples:
    * "high cholesterol" -> hyperlipidemia / hypercholesterolemia
    * "high blood pressure" -> hypertension
    * "heartburn" -> gastroesophageal reflux disease (GERD)
- Only mark unsupported if the condition is genuinely different.

SCORING (match_score):
- 1.0 = Claim DEFINITELY matches an FDA indication
- 0.7-0.9 = Claim LIKELY matches (via synonym/equivalent term)
- 0.4-0.6 = Unclear or partial match
- 0.0-0.3 = Claim does NOT match any FDA indication

Output ONLY JSON:
{{"match_score": 0.0-1.0, "evidence": "brief explanation"}}"""
    
    client = OpenAI()
    response = client.responses.create(model=llm_model, input=prompt)
    
    elapsed = time.time() - start
    
    try:
        result = json.loads(response.output_text.strip())
        # Try both "match_score" (new) and "confidence" (legacy) for backwards compatibility
        match_score = float(result.get("match_score") or result.get("confidence", 0.0))

        supported = match_score >= threshold
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s (match_score: {match_score:.2f})")
        return {
            "supported": supported,
            "evidence": result.get("evidence", "")
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        print(f"    ⏱️  fact_check_claim({drug_name}): {elapsed:.2f}s (parse error)")
        return {"supported": None, "evidence": "Could not verify claim"}