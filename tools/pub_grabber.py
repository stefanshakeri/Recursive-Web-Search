"""
Grab publications from a list of DOIs and save them to a data/pubs.txt
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# load environment variables
CROSSREF = os.getenv("CROSSREF")
MAILTO = os.getenv("MAILTO")

def get_pub(index: int, total: int, doi: str) -> str:
    """
    Get the publication (journal, conference, etc.) for a given DOI.

    :param doi: DOI of the paper to query
    :return: publication as a string, or "Unknown" if not found
    """
    try:
        r = requests.get(f"{CROSSREF}/{doi}", params={"mailto": MAILTO}, timeout=10)
        r.raise_for_status()

    # handle exceptions
    except requests.exceptions.HTTPError as e:
        if r.status_code == 404:
            print(f"Warning: DOI {doi} not found (404). Skipping.")
        else:
            print(f"Warning: HTTP error for DOI {doi}: {e}. Skipping.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Warning: Request error for DOI {doi}: {e}. Skipping.")
        return None
    
    try:
        # parse the response JSON
        message = r.json()["message"]
        # get the publication title if message["container-title"] exists and has elements
        if "container-title" in message and message["container-title"]:
            pub = message["container-title"][0]
        else:
            pub = "Unknown"
        print(f"[{index}/{total}] Found publication for DOI {doi}: {pub}")
        return pub
    except (KeyError, IndexError, ValueError) as e:
        print(f"Warning: Error parsing response for DOI {doi}: {e}")
        return None

def main():
    """
    Main function to read DOIs from dois.txt, fetch their publications
    """
    dois = []
    pubs = []

    # read the DOIs from data/dois.txt
    with open("data/dois.txt", "r") as f:
        dois = [line.strip() for line in f if line.strip()]

    # get the publication date for each DOI
    for i, doi in enumerate(dois):
        pub = get_pub(i + 1, len(dois), doi)
        if pub is not None:  # Only append if we got a valid result
            pubs.append(pub)
        else:
            pubs.append("Unknown")  # Use "Unknown" for failed requests

    # write the dates into data/pubs.txt
    with open("data/pubs.txt", "w") as f:
        f.writelines("\n".join(pubs))

    print(f"Saved {len(pubs)} publications to data/pubs.txt")

if __name__ == "__main__":
    main()


