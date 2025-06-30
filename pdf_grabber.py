import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote_plus

# load environment variables
load_dotenv()
UNPAYWALL_EMAIL = os.getenv("MAILTO")

OUTPUT_DIR = "data/pdfs"
INPUT_FILE = "data/dois.txt"

# prepare output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

    with requests.get(pdf_url, stream=True, timeout=20) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    print(f"Downloaded {doi}")

def main():
    """
    Main function to orchestrate the PDF downloading process.
    """
    with open(INPUT_FILE) as f:
        dois = [line.strip() for line in f if line.strip()]

    for doi in dois:
        pdf_url = get_pdf_url(doi)
        if pdf_url:
            download_pdf(doi, pdf_url)
        else:
            print(f"No PDF found for DOI: {doi}")

if __name__ == "__main__":
    main()
    