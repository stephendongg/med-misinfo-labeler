# MedCheck: Automated Drug Claim Verification Using FDA Labeling  

## Submission Information
**Group Number:** 13  
**Group Members:** Viha Srinivas, Zhiming Zhang, Samantha Wu, Stephen Dong

---

## Submitted Files

### Core Implementation
- `policy_proposal_labeler.py` - **Main policy proposal labeler** with drug detection, FDA approval checking, and claim verification
- `pylabel/label.py` - Utility functions for interacting with Bluesky API and fetching posts
- `pylabel/claim_checker.py` - Extracts and fact-checks drug-related claims from post text
- `pylabel/fda_lookup.py` - FDA drug database lookup and approval validation
- `pylabel/__init__.py` - Package initialization
- `data.csv` - **[Required for submission]** Test dataset with ~150+ posts for evaluation

### Testing & Data
- `test_labeler.py` - Testing harness that runs the labeler on CSV input files
- `test-data/input-drug.csv` - Test cases for drug claim verification
- `moderation_log.csv` - Output log of labeling decisions with timestamps and details

### Configuration
- `labeler-inputs/` - Reference data directory containing domain lists and images
- `README.md` - This documentation file

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Install Dependencies
```bash
pip install -r requirements.txt
```

Key dependencies: `atproto`, `openai`, `pandas`, `python-dotenv`, `requests`

---

## Running Tests

### Basic Usage
```bash
python test_labeler.py labeler-inputs <input-csv-file>
```

### Test Examples



**Drug claim verification:**

To test the labeler with real posts:

```bash
python test_labeler.py labeler-inputs test-data/input-drug.csv
```

To test the labeler with generated posts:

```bash
python test_labeler.py labeler-inputs test-data/input-generated.csv
```

NOTE: TODO: change the csv file to data.csv (as specified by the instructions)





### Expected Output Format
```
The labeler produced (X) correct labels assignments out of (Y)
Overall ratio of correct label assignments (Z)
```

Results are also logged to `moderation_log.csv` with detailed information.

---

## Implementation Overview

### Labels Generated
- `drug-approved` - Post mentions FDA-approved drug(s)
- `drug-unapproved` - Post mentions unapproved/unrecognized drug(s)
- `supported-claim` - Claim about approved drug is verified
- `unsupported-claim` - Claim about approved drug cannot be verified

### Approach
1. **Drug Detection** - Uses LLM to identify drug mentions in posts
2. **FDA Verification** - Checks detected drugs against FDA approval database
3. **Claim Extraction** - Identifies specific claims about drug efficacy/use
4. **Fact Checking** - Verifies claims against FDA labeling data

### Key Functions
**`policy_proposal_labeler.py`:**
- `moderate_post(url)` - Main function that takes a Bluesky post URL and returns list of labels
- `_detect_drug_mention(text)` - LLM-based drug detection
- `_determine_approval_labels(payload)` - FDA approval checking
- `_check_claims(text, approved_drugs)` - Claim verification

---

## Project Links
- [Project Drive](https://drive.google.com/drive/u/0/folders/1jaiOBhk-5XAITQL_i_6qKUUg01tlnjVd)
- [Assignment Doc](https://docs.google.com/document/d/1rQrgdzop-6PgfUXK8_p0n2VOfUJENYwo3zitkWgu_rY/edit?tab=t.jl6mduu0sudz)
- [Policy Proposal](https://docs.google.com/document/d/1f-2VSGjHfFOUZXSHIMBSCVEWm4NRnzjaj4kAB7C3mjw/edit?tab=t.jzvd2wwrer9s)
- [Figma Mockup](https://www.figma.com/board/BnyKzCTUETXypsjbL3RYUs/Med-Misinfo-Labeler?node-id=0-1&t=QKd7iegx3bDecWRm-1)

### Resources
- [AT Protocol SDK](https://atproto.blue/en/latest/)


