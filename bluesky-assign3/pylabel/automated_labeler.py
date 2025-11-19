"""Implementation of automated moderator"""

from typing import List, Dict, Optional
from atproto import Client
from openai import OpenAI
from .label import post_from_url
from .fda_lookup import check_fda_approval
from .claim_checker import extract_claim, fact_check_claim
import json
import csv
import os
import time
from datetime import datetime

DRUG_CONFIDENCE_THRESHOLD = 0.65
FACT_CHECK_THRESHOLD = 0.5
LLM_MODEL = "gpt-5-mini" 


class AutomatedLabeler:
    """Automated labeler implementation"""

    def __init__(self, client: Client, input_dir, log_file: Optional[str] = None):
        self.client = client
        self.log_file = log_file or "moderation_log.csv"
        self.openai_client = OpenAI()
        self._init_log_file()

    def _init_log_file(self):
        """Initialize the log CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'url', 'llm_response', 'labels', 'claim_details'])

    def _log_moderation_result(self, url: str, payload: Dict, labels: List[str], claim_details: Optional[List[Dict]] = None):
        """Log moderation result to CSV file.
        
        Args:
            url: URL of the post
            payload: LLM response payload
            labels: Resulting labels
            claim_details: Optional list of claim details dictionaries
        """
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                url,
                json.dumps(payload),
                json.dumps(labels),
                json.dumps(claim_details) if claim_details else ""
            ])

    def _detect_drug_mention(self, text: str) -> Optional[Dict]:
        """Detect if post discusses any drugs using LLM.
        
        Args:
            text: Post content text
            
        Returns:
            Dict with keys: "discussing_drug", "confidence_score", "drug_names", or None if parsing fails
        """
        start = time.time()
        
        prompt = f"""
        You are a content moderation model.

        Analyze the following post and determine if it discusses or depicts any drugs.

        Output your response in exactly this JSON format, with no additional text:
        {{
        "discussing_drug": <true or false>,
        "confidence_score": <float between 0 and 1>,
        "drug_names": [<list of drug names as strings, empty if none>]
        }}

        Post content:
        {text}
        """.strip()

        response = self.openai_client.responses.create(
            model=LLM_MODEL,
            input=prompt,
        )

        result = response.output_text.strip()
        elapsed = time.time() - start
        print(f"⏱️  detect_drug_mention: {elapsed:.2f}s")

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print("Could not parse JSON from LLM.")
            return None

    def _check_claims(self, text: str, approved_drugs: List[str]) -> tuple[List[str], List[Dict]]:
        """Check claims for approved drugs.
        
        Args:
            text: Post content text
            approved_drugs: List of approved drug names
            
        Returns:
            Tuple of (claim_labels, claim_details)
            - claim_labels: List of "supported-claim" or "unsupported-claim" labels
            - claim_details: List of dicts with claim info (drug_name, claim_text, supported, evidence)
        """
        start_total = time.time()
        claim_labels = []
        claim_details = []
        
        for drug_name in approved_drugs:
            claim_info = extract_claim(text, drug_name)
            if not claim_info.get("has_claim"):
                continue
            
            fact_check = fact_check_claim(claim_info["claim_text"], drug_name)
            
            supported = fact_check.get("supported")
            claim_details.append({
                "drug_name": drug_name,
                "claim_text": claim_info["claim_text"],
                "supported": supported,
                "evidence": fact_check.get("evidence", "")
            })
            
            if supported is True:
                claim_labels.append("supported-claim")
            elif supported is False:
                claim_labels.append("unsupported-claim")
        
        elapsed_total = time.time() - start_total
        print(f"⏱️  check_claims (total): {elapsed_total:.2f}s")
        
        return claim_labels, claim_details
        
    def _determine_approval_labels(self, payload: Dict) -> tuple[List[str], List[str]]:
        """Check if detected drugs are FDA-approved.
        
        Args:
            payload: Dict with keys: "discussing_drug", "confidence_score", "drug_names"
            
        Returns:
            Tuple of (approval_labels, approved_drugs)
            - approval_labels: ["drug-approved"] or ["drug-unapproved"] or []
            - approved_drugs: List of approved drug names (empty if unapproved)
        """
        if not payload.get("discussing_drug") or payload.get("confidence_score", 0) < DRUG_CONFIDENCE_THRESHOLD:
            return [], []

        drug_names = payload.get("drug_names", [])
        if not drug_names:
            return [], []

        start = time.time()
        approved_drugs = []
        has_unapproved = False
        
        for drug_name in drug_names:
            drug_name = drug_name.strip()
            if not drug_name:
                continue
            approval = check_fda_approval(drug_name)
            if "error" in approval or not approval.get("approved"):
                has_unapproved = True
            else:
                approved_drugs.append(drug_name)
        
        elapsed = time.time() - start
        print(f"⏱️  determine_approval_labels: {elapsed:.2f}s")

        if has_unapproved:
            return ["drug-unapproved"], []
        
        return ["drug-approved"], approved_drugs
            
    def moderate_post(self, url: str) -> List[str]:
        """Moderate a post and return labels.
        
        Args:
            url: URL of the Bluesky post to moderate
            
        Returns:
            List of labels: ['drug-approved'], ['drug-approved', 'supported-claim'], 
            ['drug-approved', 'unsupported-claim'], ['drug-unapproved'], or []
        """
        
        # Step 1: Fetch post content from URL
        start_total = time.time()
        start = time.time()
        content = post_from_url(self.client, url)
        text = content.value.text
        elapsed = time.time() - start
        print(f"⏱️  fetch_post: {elapsed:.2f}s")
        
        # Step 2: Use LLM to detect drug mentions
        payload = self._detect_drug_mention(text)
        if payload is None:
            return []

        # Step 3: Check confidence threshold and FDA approval status
        approval_labels, approved_drugs = self._determine_approval_labels(payload)
        
        # If no drugs or unapproved, return early
        if not approval_labels or "drug-unapproved" in approval_labels:
            self._log_moderation_result(url, payload, approval_labels)
            elapsed_total = time.time() - start_total
            print(f"⏱️  TOTAL TIME: {elapsed_total:.2f}s\n")
            return approval_labels
        
        # Step 4: All approved - check for claims and fact-check them
        labels = approval_labels.copy()

        claim_labels, claim_details = self._check_claims(text, approved_drugs)
        labels.extend(claim_labels)
        
        # Step 5: Log results and return labels
        self._log_moderation_result(url, payload, labels, claim_details)
        
        elapsed_total = time.time() - start_total
        print(f"⏱️  TOTAL TIME: {elapsed_total:.2f}s\n")
            
        return labels