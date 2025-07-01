import os
import re
import requests
from dotenv import load_dotenv
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

# load environment variables
load_dotenv()
UNPAYWALL_EMAIL = os.getenv("MAILTO")

OUTPUT_DIR = "data/pdfs"
INPUT_FILE = "data/dois.txt"

PDF_COUNTER = 0

# prepare output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

def find_pdf_link(soup: BeautifulSoup, base_url: str) -> str:
    """
    Find a direct PDF link in the given BeautifulSoup object.

    :param soup: BeautifulSoup object containing the HTML content
    :param base_url: Base URL to resolve relative links
    :return: URL of the PDF if found, otherwise None
    """

    # direct .pdf in <a>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    
    # <iframe> or <embed> with PDF
    iframe = soup.find("iframe", src=re.compile(r"\.pdf$", re.I))
    if iframe:
        return urljoin(base_url, iframe["src"])
    
    embed = soup.find("embed", src=re.compile(r"\.pdf$", re.I))
    if embed:
        return urljoin(base_url, embed["src"])
    
    # find <link> with rel="alternate" and type="application/pdf"
    link = soup.find("link", rel="alternate", type="application/pdf")
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    
    return None

def find_intermediate_pdf_page(soup: BeautifulSoup) -> str: 
    """
    Find intermediate links that lead to a PDF download page.

    :param soup: BeautifulSoup object containing the HTML content
    :return: URL of the intermediate page if found, otherwise None
    """
    candidates = soup.find_all("a", href=True, string=re.compile(r"PDF", re.I))
    for a in candidates:
        return a["href"]
    
    return None

def web_scrape_pdfs(doi: str, session: requests.Session = None) -> str:
    """
    Web scrape the PDF from the given DOI. 
    :param doi: the DOI of the paper
    :return: URL of the PDF if available, otherwise None
    """
    session = session or requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; PDFScraper/1.0; +https://github.com/stefanshakeri/Recursive-Web-Search)"
    })

    doi_url = f"https://doi.org/{quote_plus(doi)}"

    try:
        # make a request to the DOI URL
        r1 = session.get(doi_url, timeout=10)
        r1.raise_for_status()

        # if the response is a PDF, return the URL
        if "application/pdf" in r1.headers.get("Content-Type", ""):
            return r1.url
        
        soup1 = BeautifulSoup(r1.text, "html.parser")

        # look for a direct PDF link in the HTML
        pdf_url = find_pdf_link(soup1, doi_url)
        if pdf_url:
            return pdf_url
        
        # find intermediate links to "download PDF" or "view PDF" type pages
        intermediate_links = find_intermediate_pdf_page(soup1)
        if intermediate_links:
            inter_url = urljoin(doi_url, intermediate_links)
            r2 = session.get(inter_url, timeout=10)
            r2.raise_for_status()

            soup2 = BeautifulSoup(r2.text, "html.parser")

            pdf_url = find_pdf_link(soup2, inter_url)
            if pdf_url:
                return pdf_url
        
    # handle various request exceptions
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF for DOI {doi}: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout while fetching PDF for DOI {doi}: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error while fetching PDF for DOI {doi}: {e}")
    
    return None


def get_pdf_url(doi: str) -> str:
    """
    Get the PDF URL for a given DOI using the Unpaywall API.
    :param doi: DOI of the paper
    :return: URL of the PDF if available, otherwise None
    """
    # construct the Unpaywall API URL with the DOI
    url = f"https://api.unpaywall.org/v2/{quote_plus(doi)}"
    params = {"email": UNPAYWALL_EMAIL}

    # make a request to the Unpaywall API
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    # check if the best OA location is available and return its PDF URL
    oa = data.get("best_oa_location")
    return oa.get("url_for_pdf") if oa else None

def download_pdf(doi: str, pdf_url: str):
    """
    Download the PDF from the given URL and save it to the output directory.
    :param doi: DOI of the paper
    :param pdf_url: URL of the PDF to download
    """
    # create a safe filename by replacing slashes in the DOI
    safe_name = doi.replace("/", "_")
    output_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")
    
    try:
        with requests.get(pdf_url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            global PDF_COUNTER
            PDF_COUNTER += 1
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading {doi}: {e}")
        return
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error while downloading {doi}: {e}")
        return
    except requests.exceptions.Timeout as e:
        print(f"Max retries exceeded while downloading {doi}: {e}")
        return
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading {doi}: {e}")
        return
    
    print(f"Downloaded {doi}")

def clear_pdfs():
    """
    Clear all PDF files from the output directory.
    """
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

def main():
    """
    Main function to orchestrate the PDF downloading process.
    """
    # clear the output directory
    clear_pdfs()
    # read DOIs from the input file
    with open(INPUT_FILE) as f:
        dois = [line.strip() for line in f if line.strip()]

    # iterate over each DOI and fetch the PDF URL
    for doi in dois:
        pdf_url = get_pdf_url(doi)
        if pdf_url:
            download_pdf(doi, pdf_url)
        else:
            # if Unpaywall API fails, try web scraping
            pdf_url = web_scrape_pdfs(doi, session=requests.Session())
            if pdf_url:
                download_pdf(doi, pdf_url)
            else:
                print(f"No PDF found for DOI: {doi}")

    print(f"Downloaded {PDF_COUNTER} PDFs.")


if __name__ == "__main__":
    main()
    