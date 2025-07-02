import os
import re
import requests
from dotenv import load_dotenv
from urllib.parse import urljoin, quote_plus, urlparse, parse_qs

from bs4 import BeautifulSoup

# load environment variables
load_dotenv()
UNPAYWALL_EMAIL = os.getenv("MAILTO")

OUTPUT_DIR = "data/pdfs"
INPUT_FILE = "data/dois.txt"

PDF_COUNTER = 0

# prepare output folder
os.makedirs(OUTPUT_DIR, exist_ok=True)

def verify_pdf_url(url: str, session: requests.Session = None) -> bool:
    """
    Verify that a URL actually points to a PDF by checking headers.
    :param url: URL to verify
    :param session: requests session to use
    :return: True if URL points to a PDF, False otherwise
    """
    session = session or requests.Session()
    try:
        # Make a HEAD request to check content type without downloading
        response = session.head(url, timeout=10, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "").lower()
        
        # Check if content type indicates PDF
        if "application/pdf" in content_type:
            return True
        
        # Some servers don't set proper content type, so check content-disposition
        content_disposition = response.headers.get("Content-Disposition", "").lower()
        if ".pdf" in content_disposition:
            return True
        
        # If HEAD doesn't work, try a small GET request
        if response.status_code != 200:
            response = session.get(url, timeout=10, stream=True, headers={"Range": "bytes=0-1023"})
            
        # Check if URL path suggests it's a PDF
        if url.lower().endswith('.pdf'):
            return True
            
    except requests.exceptions.RequestException:
        pass
    
    return False

def is_pdf_link(href: str) -> bool:
    """
    Check if the given href points to .pdf or pdfft endpoint carrying a PDF
    
    :param href: URL or path to check
    :return: True if it points to a PDF, False otherwise
    """
    if not href:
        return False
        
    href_lower = href.lower()
    
    # Check for common PDF indicators
    pdf_indicators = [
        ".pdf", "pdfft", "/pdf/", "pdf?", "getPDF", "downloadPDF", 
        "viewPDF", "fulltext.pdf", "article.pdf", "download.pdf",
        "content_type=pdf", "format=pdf", "type=pdf"
    ]
    
    if any(indicator in href_lower for indicator in pdf_indicators):
        return True
    
    # parse the URL and check the path
    try:
        parsed = urlparse(href)
        path = parsed.path.lower()
        
        if path.endswith(".pdf"):
            return True
        
        # check for query-string values as well
        for vals in parse_qs(parsed.query).values():
            if any(v.lower().endswith(".pdf") for v in vals):
                return True
    except Exception:
        pass
    
    return False

def find_pdf_link(soup: BeautifulSoup, base_url: str) -> str:
    """
    Find a direct PDF link in the given BeautifulSoup object.

    :param soup: BeautifulSoup object containing the HTML content
    :param base_url: Base URL to resolve relative links
    :return: URL of the PDF if found, otherwise None
    """
    # Priority 1: Direct PDF links in <a> tags
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if is_pdf_link(href):
            return urljoin(base_url, href)
    
    # Priority 2: Look for meta tags with PDF URLs
    meta_pdf = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta_pdf and meta_pdf.get("content"):
        return urljoin(base_url, meta_pdf["content"])
    
    # Priority 3: <iframe> or <embed> with PDF
    iframe = soup.find("iframe", src=re.compile(r"\.pdf$", re.I))
    if iframe:
        return urljoin(base_url, iframe["src"])
    
    embed = soup.find("embed", src=re.compile(r"\.pdf$", re.I))
    if embed:
        return urljoin(base_url, embed["src"])
    
    # Priority 4: <link> with rel="alternate" and type="application/pdf"
    link = soup.find("link", rel="alternate", type="application/pdf")
    if link and link.get("href"):
        return urljoin(base_url, link["href"])
    
    # Priority 5: Look for buttons/links with download attributes
    download_link = soup.find("a", attrs={"download": True, "href": True})
    if download_link and is_pdf_link(download_link["href"]):
        return urljoin(base_url, download_link["href"])
    
    # Priority 6: Look for data attributes that might contain PDF URLs
    for element in soup.find_all(attrs={"data-pdf-url": True}):
        pdf_url = element.get("data-pdf-url")
        if pdf_url and is_pdf_link(pdf_url):
            return urljoin(base_url, pdf_url)
    
    return None

def find_intermediate_pdf_page(soup: BeautifulSoup) -> str: 
    """
    Find intermediate links that lead to a PDF download page.

    :param soup: BeautifulSoup object containing the HTML content
    :return: URL of the intermediate page if found, otherwise None
    """
    # Priority 1: Look for specific PDF-related links with aria-labels or classes
    selectors = [
        "a[aria-label*='PDF' i]",
        "a[aria-label*='Download' i]", 
        "a.pdf-link",
        "a.download-pdf",
        "a.full-text",
        "a[class*='pdf' i]",
        "a[id*='pdf' i]"
    ]
    
    for selector in selectors:
        link = soup.select_one(selector)
        if link and link.get("href"):
            return link["href"]
    
    # Priority 2: Look for buttons with PDF-related text
    pdf_keywords = [
        "PDF", "Download PDF", "View PDF", "Full Text PDF", "Download", 
        "Full Text", "Article PDF", "Download Article", "View Article",
        "Get PDF", "Access PDF", "Read PDF", "Open PDF"
    ]
    
    for keyword in pdf_keywords:
        # Look in link text
        candidates = soup.find_all("a", href=True, string=re.compile(keyword, re.I))
        if candidates:
            return candidates[0]["href"]
        
        # Look in button text within links
        button_link = soup.find("a", href=True)
        if button_link:
            button = button_link.find(string=re.compile(keyword, re.I))
            if button:
                return button_link["href"]
    
    # Priority 3: Look for links with PDF-related href patterns
    pdf_href_patterns = [
        r"pdf", r"download", r"fulltext", r"article", r"view.*pdf",
        r"get.*pdf", r"access.*pdf"
    ]
    
    for pattern in pdf_href_patterns:
        pdf_link = soup.find("a", href=re.compile(pattern, re.I))
        if pdf_link and pdf_link.get("href"):
            return pdf_link["href"]
    
    # Priority 4: Look for form submissions that might lead to PDFs
    form = soup.find("form")
    if form and form.get("action"):
        action = form["action"].lower()
        if any(keyword in action for keyword in ["pdf", "download", "export"]):
            return form["action"]
    
    return None

def web_scrape_pdfs(doi: str, session: requests.Session = None) -> str:
    """
    Web scrape the PDF from the given DOI. 
    :param doi: the DOI of the paper
    :return: URL of the PDF if available, otherwise None
    """
    session = session or requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    })

    doi_url = f"https://doi.org/{quote_plus(doi)}"

    try:
        # make a request to the DOI URL
        r1 = session.get(doi_url, timeout=15, allow_redirects=True)
        r1.raise_for_status()
        html = r1.text
        
        # Method 1: Check if PDF URL is embedded in JSON or JavaScript
        pdf_url_patterns = [
            r'"pdfUrl"\s*:\s*"([^"]+)"',
            r'"pdf_url"\s*:\s*"([^"]+)"',
            r'"downloadUrl"\s*:\s*"([^"]+\.pdf[^"]*)"',
            r'pdfUrl\s*=\s*["\']([^"\']+)["\']',
            r'pdf_link\s*=\s*["\']([^"\']+\.pdf[^"\']*)["\']'
        ]
        
        for pattern in pdf_url_patterns:
            match = re.search(pattern, html, re.I)
            if match:
                import html as html_module
                pdf_url = html_module.unescape(match.group(1))
                candidate_url = urljoin(r1.url, pdf_url)
                if is_pdf_link(candidate_url):
                    return candidate_url

        # Method 2: Check if the response itself is a PDF
        if "application/pdf" in r1.headers.get("Content-Type", ""):
            return r1.url
        
        soup1 = BeautifulSoup(r1.text, "html.parser")

        # Method 3: Look for direct PDF links in the HTML
        pdf_url = find_pdf_link(soup1, r1.url)
        if pdf_url:
            # Verify the PDF URL before returning it
            if verify_pdf_url(pdf_url, session):
                return pdf_url
            else:
                print(f"  PDF URL verification failed for {pdf_url}")
        
        # Method 4: Try multiple intermediate page strategies
        intermediate_links = find_intermediate_pdf_page(soup1)
        
        if intermediate_links:
            inter_url = urljoin(r1.url, intermediate_links)
            try:
                r2 = session.get(inter_url, timeout=15, allow_redirects=True)
                r2.raise_for_status()

                # Check if intermediate page directly serves PDF
                if "application/pdf" in r2.headers.get("Content-Type", ""):
                    return r2.url

                soup2 = BeautifulSoup(r2.text, "html.parser")
                pdf_url = find_pdf_link(soup2, r2.url)
                if pdf_url and verify_pdf_url(pdf_url, session):
                    return pdf_url
            except requests.exceptions.RequestException:
                pass  # Continue to next method
        
        # Method 5: Try common PDF endpoint patterns
        base_domain = f"{urlparse(r1.url).scheme}://{urlparse(r1.url).netloc}"
        common_pdf_paths = [
            f"/pdf/{doi}",
            f"/pdf/{doi}.pdf", 
            f"/article/pdf/{doi}",
            f"/content/pdf/{doi}.pdf",
            f"/download/pdf/{doi}",
            f"/full/{doi}.pdf"
        ]
        
        for path in common_pdf_paths:
            try:
                test_url = base_domain + path
                if verify_pdf_url(test_url, session):
                    return test_url
            except requests.exceptions.RequestException:
                continue
        
    # handle various request exceptions
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error while fetching PDF for DOI {doi}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF for DOI {doi}: {e}")
    
    return None


def try_alternative_sources(doi: str, session: requests.Session) -> str:
    """
    Try alternative sources for PDF access.
    :param doi: DOI of the paper
    :param session: requests session to use
    :return: URL of the PDF if found, otherwise None
    """
    # Try arXiv if it's an arXiv paper
    if "arxiv" in doi.lower():
        arxiv_id = doi.split("/")[-1] if "/" in doi else doi
        arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if verify_pdf_url(arxiv_pdf_url, session):
            return arxiv_pdf_url
    
    # Try bioRxiv/medRxiv patterns
    for preprint_server in ["biorxiv", "medrxiv"]:
        if preprint_server in doi.lower():
            try:
                # Extract the paper ID and construct direct PDF URL
                parts = doi.split("/")
                if len(parts) >= 2:
                    paper_id = parts[-1]
                    pdf_url = f"https://www.{preprint_server}.org/content/10.1101/{paper_id}v1.full.pdf"
                    if verify_pdf_url(pdf_url, session):
                        return pdf_url
            except requests.exceptions.RequestException:
                pass
    
    return None

def get_pdf_url(doi: str) -> str:
    """
    Get the PDF URL for a given DOI using the Unpaywall API.
    :param doi: DOI of the paper
    :return: URL of the PDF if available, otherwise None
    """
    try:
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
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF URL from Unpaywall for DOI {doi}: {e}")
        return None

def is_valid_pdf(file_path: str) -> bool:
    """
    Check if the downloaded file is a valid PDF by checking its header and basic structure.
    :param file_path: Path to the file to check
    :return: True if it's a valid PDF, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            # Check PDF header
            header = f.read(8)
            if not header.startswith(b'%PDF-'):
                return False
            
            # Check file size - PDFs should be at least a few hundred bytes
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()
            if file_size < 100:  # Too small to be a valid PDF
                return False
            
            # Check for PDF trailer (basic structure validation)
            f.seek(max(0, file_size - 1024))  # Read last 1KB
            trailer_content = f.read()
            if b'%%EOF' not in trailer_content and b'trailer' not in trailer_content:
                return False
            
            return True
    except Exception as e:
        print(f"Error validating PDF {file_path}: {e}")
        return False

def is_html_content(content_bytes: bytes) -> bool:
    """
    Check if content is HTML (common when servers return error pages instead of PDFs).
    :param content_bytes: First few bytes of content
    :return: True if content appears to be HTML
    """
    # Check for common HTML indicators
    html_indicators = [b'<!DOCTYPE', b'<html', b'<HTML', b'<head', b'<HEAD', b'<body', b'<BODY']
    content_lower = content_bytes.lower()
    return any(indicator in content_lower for indicator in html_indicators)

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
            
            # Check if the response is actually a PDF
            content_type = r.headers.get("Content-Type", "").lower()
            if "application/pdf" not in content_type and "pdf" not in content_type:
                print(f"Warning: Content-Type is '{content_type}' for {doi}, may not be a PDF")
            
            # Read first chunk to check if it's HTML instead of PDF
            first_chunk = None
            content_written = 0
            
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if first_chunk is None:
                        first_chunk = chunk
                        # Check if the response is HTML instead of PDF
                        if is_html_content(chunk):
                            print(f"Error: Received HTML content instead of PDF for {doi}")
                            return
                    
                    f.write(chunk)
                    content_written += len(chunk)
            
            # Check if we got a reasonable amount of content
            if content_written < 1000:  # Less than 1KB is suspicious for a PDF
                os.remove(output_path)
                print(f"Error: Downloaded file for {doi} is too small ({content_written} bytes), likely not a valid PDF")
                return
            
            # Validate that the downloaded file is actually a PDF
            if is_valid_pdf(output_path):
                global PDF_COUNTER
                PDF_COUNTER += 1
                print(f"Downloaded {doi} ({content_written} bytes)")
            else:
                os.remove(output_path)  # Remove invalid file
                print(f"Downloaded file for {doi} is not a valid PDF, removed")
                return
            
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

    print(f"Processing {len(dois)} DOIs...")
    
    # iterate over each DOI and fetch the PDF URL
    for i, doi in enumerate(dois, 1):
        print(f"\n[{i}/{len(dois)}] Processing DOI: {doi}")
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        })
        
        # Method 1: Try Unpaywall API first
        pdf_url = get_pdf_url(doi)
        if pdf_url:
            print(f"  Found PDF via Unpaywall: {pdf_url}")
            # Verify the URL before downloading
            if verify_pdf_url(pdf_url, session):
                download_pdf(doi, pdf_url)
                continue
            else:
                print(f"  Unpaywall URL verification failed, trying other methods...")
        
        # Method 2: Try web scraping
        pdf_url = web_scrape_pdfs(doi, session=session)
        if pdf_url:
            print(f"  Found PDF via web scraping: {pdf_url}")
            download_pdf(doi, pdf_url)
            continue
        
        # Method 3: Try alternative sources
        pdf_url = try_alternative_sources(doi, session)
        if pdf_url:
            print(f"  Found PDF via alternative source: {pdf_url}")
            download_pdf(doi, pdf_url)
            continue
        
        print(f"  No PDF found for DOI: {doi}")

    print(f"\nDownloaded {PDF_COUNTER} PDFs out of {len(dois)} DOIs.")


if __name__ == "__main__":
    main()
    