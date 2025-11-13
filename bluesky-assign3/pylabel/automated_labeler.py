"""Implementation of automated moderator"""

from typing import List, Dict, Optional
from atproto import Client
from openai import OpenAI
from .label import post_from_url
from .fda_lookup import check_fda_approval
import json
import csv
import os
from datetime import datetime

T_AND_S_LABEL = "t-and-s"
DOG_LABEL = "dog"
DRUG_T = 0.65 # Threshold for dicsussing drug 


class AutomatedLabeler:
    """Automated labeler implementation"""

    def __init__(self, client: Client, input_dir, log_file: Optional[str] = None):
        self.client = client
        self.log_file = log_file or "moderation_log.csv"
        self._init_log_file()

    def _init_log_file(self):
        """Initialize the log CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'url', 'llm_response', 'labels'])

    def _log_moderation_result(self, url: str, payload: Dict, labels: List[str]):
        """Log moderation result to CSV file.
        
        Args:
            url: URL of the post
            payload: LLM response payload
            labels: Resulting labels
        """
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                url,
                json.dumps(payload),
                json.dumps(labels)
            ])

    def _detect_drug_mention(self, text: str) -> Optional[Dict]:
        """Use LLM to detect if post discusses a drug.
        
        Args:
            text: Post content text
            
        Returns:
            Parsed JSON payload with drug detection results, or None if parsing fails
        """

        prompt = f"""
        You are a content moderation model.

        Analyze the following post and determine if it discusses or depicts any drug.

        Output your response in exactly this JSON format, with no additional text:
        {{
        "discussing_drug": <true or false>,
        "confidence_score": <float between 0 and 1>,
        "drug_name": "<name of the drug if any, otherwise an empty string>"
        }}

        Post content:
        {text}
        """.strip()

        openai_client = OpenAI()
        response = openai_client.responses.create(
            model="gpt-5-nano",
            input=prompt,
        )

        result = response.output_text.strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print("Could not parse JSON from LLM.")
            return None

    def _determine_labels(self, payload: Dict) -> List[str]:
        """Determine labels based on drug detection payload and FDA lookup.
        
        Args:
            payload: Parsed JSON from LLM with drug detection results
            
        Returns:
            List of labels based on approval status
        """
        if not payload.get("discussing_drug"):
            return []

        confidence = payload.get("confidence_score")
        if confidence is None or confidence < DRUG_T:
            return []

        drug_name = (payload.get("drug_name") or "").strip()
        if not drug_name:
            return []

        approval = check_fda_approval(drug_name)

        if approval.get("approved"):
            return ["drug-approved"]

        if "error" in approval:
            print(f"FDA lookup failed for {drug_name}: {approval['error']}")

        return ["drug-unapproved"]
            
    def moderate_post(self, url: str) -> List[str]:
        """Apply moderation to a post and return appropriate labels.
        
        Pipeline:
        1. Fetch post content from URL
        2. Use LLM to detect if post discusses a drug
        3. Check confidence threshold
        4. Look up drug in FDA database if name is provided
        5. Return appropriate label based on approval status
        
        Args:
            url: URL of the Bluesky post to moderate
            
        Returns:
            List of labels: ['drug-approved'], ['drug-unapproved'], or []
        """
        
        content = post_from_url(self.client, url)
        text = content.value.text
        
        # Step 1: Ask LLM to detect drug mentions
        payload = self._detect_drug_mention(text)
        if payload is None:
            return []

        # Step 2: Determine labels based on LLM response and FDA lookup
        labels = self._determine_labels(payload)
        
        # Log results to CSV file
        self._log_moderation_result(url, payload, labels)
        
        return labels
