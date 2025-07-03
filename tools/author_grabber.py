"""
Grab authors from a list of DOIs and save them to a data/authors.txt
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# load environment variables
CROSSREF = os.getenv("CROSSREF")
MAILTO = os.getenv("MAILTO")

def get_authors(index: int, total: int, doi: str) -> str:
    """
    Get the authors for a given DOI, concatenated by ", ".

    :param doi: DOI of the paper to query
    :return: authors as a string, or "Unknown" if not found
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
        # get the authors if message["author"] exists and has elements
        if "author" in message and message["author"]:
            authors_list = [f"{a['given']} {a['family']}" for a in message["author"]]
            authors = ", ".join(authors_list)
        else:
            authors = "Unknown"
        print(f"[{index}/{total}] Found authors for DOI {doi}: {authors}")
        return authors
    except (KeyError, IndexError, ValueError) as e:
        print(f"Warning: Error parsing response for DOI {doi}: {e}")
        return None

def main():
    """
    Main function to read DOIs from dois.txt, fetch their authors
    """
    dois = []
    authors_list = []

    # read the DOIs from data/dois.txt
    with open("data/dois.txt", "r") as f:
        dois = [line.strip() for line in f if line.strip()]

    # get the publication date for each DOI
    for i, doi in enumerate(dois):
        authors = get_authors(i + 1, len(dois), doi)
        if authors is not None:  # Only append if we got a valid result
            authors_list.append(authors)
        else:
            authors_list.append("Unknown")  # Use "Unknown" for failed requests

    # write the authors into data/authors.txt
    with open("data/authors.txt", "w") as f:
        f.writelines("\n".join(authors))

    print(f"Saved {len(authors)} authors to data/authors.txt")

if __name__ == "__main__":
    main()


