"""
Grab dates from a list of DOIs and save them to a data/dates.txt
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# load environment variables
CROSSREF = os.getenv("CROSSREF")
MAILTO = os.getenv("MAILTO")

def get_date(doi: str) -> str:
    """
    Get the publication date for a given DOI.

    :param doi: DOI of the paper to query
    :return: publication date as a string in the format YYYY-MM-DD, or "Unknown" if not found
    """
    try:
        r = requests.get(f"{CROSSREF}/{doi}", params={"mailto": MAILTO})
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
    
    # parse the response JSON
    message = r.json()["message"]
    date = message["issued"]["date-parts"][0]
    # format the date as YYYY
    publication_date = str(date[0])
    print(f"Found publication date for DOI {doi}: {publication_date}")
    return publication_date

def main():
    """
    Main function to read DOIs from dois.txt, fetch their publication dates,
    """
    dois = []
    dates = []

    # read the DOIs from data/dois.txt
    with open("data/dois.txt", "r") as f:
        dois = [line.strip() for line in f if line.strip()]

    # get the publication date for each DOI
    for doi in dois:
        dates.append(get_date(doi))
    
    # write the dates into data/dates.txt
    with open("data/dates.txt", "w") as f:
        f.writelines("\n".join(dates))

if __name__ == "__main__":
    main()


