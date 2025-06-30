import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# load environment vaiables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CROSSREF = os.getenv("CROSSREF")
KEYWORDS_STRING = os.getenv("KEYWORDS")
MAILTO = os.getenv("MAILTO")

# constants
def parse_keywords() -> list:
    """
    Parse the keywords from the environment variable. 
    :return: list of keywords
    """
    keyword_list = KEYWORDS_STRING.split(',')
    return keyword_list

KEYWORDS = parse_keywords()

def verify_status(response: requests.Response):
    """
    Verify the status of the response.
    :param response: Response object from requests
    """
    print(json.dumps(response.json()["message"], indent=2))

def get_references(doi: str) -> list:
    """
    Get the DOIs of papers that DOI->paper cites. 
    :param doi: DOI of the paper to query
    :return: list of DOIs that the paper cites
    """
    r = requests.get(f"{CROSSREF}/{doi}", params={"mailto": MAILTO})
    r.raise_for_status()
    # verify_status(r)  # uncomment to see the full response
    references = r.json()["message"].get("reference", [])
    return [ref["DOI"] for ref in references if ref.get("DOI")]

def get_metadata(doi: str) -> dict:
    """
    Fetch metadata for a given DOI.
    :param doi: DOI of the paper to query
    :return: metadata of the paper as a dictionary
    """
    r = requests.get(f"{CROSSREF}/{doi}", params={"mailto": MAILTO})
    r.raise_for_status()

    # extract relevant metadata from the response
    message = r.json()["message"]
    title = " ".join(message.get("title", []))
    abstract = message.get("abstract", "")
    authors = message.get("author", [])

    # return the metadata as a dictionary
    return {"doi": doi, "title": title, "abstract": abstract, "authors": authors}



def is_relevant(metadata: dict) -> bool:
    """
    Check if the paper is relevant based on its title and abstract.
    :param metadata: metadata of the paper
    :return: True if the paper is relevant, False otherwise
    """
    text = (metadata["title"] + " " + metadata["abstract"]).lower()
    return any(key.lower() in text for key in KEYWORDS)

def query_papers(doi: str, max_depth: int = 2, depth: int = 0, visited: set = None, results: list = None, seen_results: set = None) -> list:
    """
    Recursively query papers based on their citations and references.
    :param doi: DOI of the paper to query
    :param max_depth: Maximum depth of recursion
    :param depth: Current depth of recursion
    :param visited: Set of visited DOIs to avoid cycles
    :param results: List to store the results
    :return: List of relevant papers with their metadata
    """
    # Initialize visited and results if they are None
    if visited is None:
        visited = set()
        results = []
        seen_results = set()

    # stop criteria
    if depth > max_depth or doi in visited:
        return results
    
    # mark the current DOI as visited
    visited.add(doi)
    # get the citations for the current DOI
    print(f"Querying DOI: {doi} at depth {depth}")
    next_dois = get_references(doi)
    print(f"Found {len(next_dois)} references for DOI: {doi}")
    for next in next_dois:
        # skip if the DOI has already been visited
        if next in visited:
            continue
        
        metadata = get_metadata(next)
        if is_relevant(metadata) and metadata["doi"] not in seen_results:
            results.append(metadata)
            seen_results.add(metadata["doi"])
            query_papers(next, max_depth, depth + 1, visited, results, seen_results)

    return results
