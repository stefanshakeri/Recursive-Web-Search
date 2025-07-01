import os
import re
import requests
from dotenv import load_dotenv
from urllib.parse import urljoin, quote_plus

# load environment variables
load_dotenv()
UNPAYWALL_EMAIL = os.getenv("MAILTO")

OUTPUT_DIR = "data/pdfs"
INPUT_FILE = "data/dois.txt"

PDF_COUNTER = 0

# prepare output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

def web_scrape_pdfs(doi: str) -> str:
    """
    Web scrape the PDF from the given DOI. 
    :param doi: the DOI of the paper
    :return: URL of the PDF if available, otherwise None
    """
    doi_url = f"https://doi.org/{quote_plus(doi)}"
    try:
        # make a request to the DOI URL
        r = requests.get(doi_url, timeout=10)
        r.raise_for_status()

        # check if the response contains a PDF link
        pdf_link = re.search(r'href="([^"]+\.pdf)"', r.text, re.IGNORECASE)
        if pdf_link:
            pdf_url = urljoin(doi_url, pdf_link.group(1))
            return pdf_url
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF for DOI {doi}: {e}")
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
            pdf_url = web_scrape_pdfs(doi)
            if pdf_url:
                download_pdf(doi, pdf_url)
            else:
                print(f"No PDF found for DOI: {doi}")

    print(f"Downloaded {PDF_COUNTER} PDFs.")


if __name__ == "__main__":
    main()
    