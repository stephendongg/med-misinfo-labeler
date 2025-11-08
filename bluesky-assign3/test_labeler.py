"""Script for testing the automated labeler"""

import warnings
# Suppress pydantic warnings from dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import argparse
import json
import os

import pandas as pd
from atproto import Client
from dotenv import load_dotenv
from pylabel import AutomatedLabeler, label_post, did_from_handle

load_dotenv(override=True)
USERNAME = 'tns-labeler.bsky.social'
PW = '20251107'

def main():
    """
    Main function for the test script
    """
    client = Client()
    labeler_client = None
    client.login(USERNAME, PW)
    did = did_from_handle(USERNAME)

    parser = argparse.ArgumentParser()
    parser.add_argument("labeler_inputs_dir", type=str)
    parser.add_argument("input_urls", type=str)
    parser.add_argument("--emit_labels", action="store_true")
    args = parser.parse_args()

    if args.emit_labels:
        labeler_client = client.with_proxy("atproto_labeler", did)

    labeler = AutomatedLabeler(client, args.labeler_inputs_dir)

    urls = pd.read_csv(args.input_urls)
    num_correct, total = 0, urls.shape[0]
    for _index, row in urls.iterrows():
        url, expected_labels = row["URL"], json.loads(row["Labels"])
        labels = labeler.moderate_post(url)
        if sorted(labels) == sorted(expected_labels):
            num_correct += 1
        else:
            print(f"For {url}, labeler produced {labels}, expected {expected_labels}")
        if args.emit_labels and (len(labels) > 0):
            label_post(client, labeler_client, url, labels)
    print(f"The labeler produced {num_correct} correct labels assignments out of {total}")
    print(f"Overall ratio of correct label assignments {num_correct/total}")


if __name__ == "__main__":
    main()
