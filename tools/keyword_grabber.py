"""
Grab keywords from a list of DOIs and save them to a data/keywords.txt
"""

import os
import requests
import re
import bs4 as BeautifulSoup
import html
from dotenv import load_dotenv

load_dotenv()

# load environment variables
EMAIL = os.getenv("MAILTO")
HDRS = {"User-Agent": EMAIL}

def get_doi_links() -> list[str]:
    """
    Get DOI links from data/doi_links.txt
    
    :return: List of DOI links
    """
    with open("data/doi_links.txt", "r", encoding="utf-8") as f:
        doi_links = [line.strip() for line in f if line.strip()]
    
    return doi_links

def get_keywords(index: int, total: int, doi: str) -> str:
    """
    Get the keywords for a given DOI.

    :param doi: DOI link of the paper to query
    :return: Keywords as a string concatenated with ", ", or "Unknown" if not found
    """
    # Clean the DOI link
    html_doc = requests.get(doi, headers=HDRS, timeout=20).text
    soup = BeautifulSoup.BeautifulSoup(html_doc, "lxml")

    # meta tag with name "keywords"
    meta = soup.find("meta", attrs={"name": re.compile("^keywords?$", re.I)})
    if meta and meta.get("content"):
        keywords = meta["content"]
        # Decode HTML entities
        keywords = html.unescape(keywords)
        # Remove extra spaces and split by comma
        keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        # Join keywords with ", "
        print(f"[{index}/{total}] Found keywords for DOI {doi}: {', '.join(keywords_list)}")
        return ", ".join(keywords_list)
    
    else:
        # any element whose class/id contains "keyword"
        block = soup.find(attrs={"class": re.compile("keyword", re.I)})
        if block:
            # Extract text and decode HTML entities
            keywords = html.unescape(block.get_text(strip=True))
            # Remove extra spaces and split by comma
            keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            # Join keywords with ", "
            print(f"[{index}/{total}] Found keywords for DOI {doi}: {', '.join(keywords_list)}")
            return ", ".join(keywords_list)
        
        else:
            # regex on full page text
            text = soup.get_text("\n", strip=True)
            m = re.search(r"(?i)key ?words?\s*[:\-]?\s*(.+)", text)
            if m:
                keywords = m.group(1)
                # Decode HTML entities
                keywords = html.unescape(keywords)
                # Remove extra spaces and split by comma
                keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
                # Join keywords with ", "
                print(f"[{index}/{total}] Found keywords for DOI {doi}: {', '.join(keywords_list)}")
                return ", ".join(keywords_list)

    print(f"[{index}/{total}] Warning: No keywords found for DOI {doi}.")
    return "Unknown"

def main():
    """
    Main function to read DOI links, fetch their keywords, and save them to data/keywords.txt
    """
    doi_links = get_doi_links()
    keywords_list = []

    for i, doi in enumerate(doi_links, start=1):
        keywords = get_keywords(i, len(doi_links), doi)
        keywords_list.append(keywords)
    
    # write the keywords into data/keywords.txt
    with open("data/keywords.txt", "w", encoding="utf-8") as f:
        f.writelines("\n".join(keywords_list))
    
    print(f"Saved {len(keywords_list)} keywords to data/keywords.txt")

if __name__ == "__main__":
    main()