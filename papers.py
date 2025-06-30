import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Import the query_papers function from paper_query module
from paper_query import query_papers

# Load environment variables
load_dotenv()
START_DOI = os.getenv("START_DOI")

def strip_html(text: str) -> str:
    """
    Strip HTML tags from a given text.
    :param text: Text containing HTML tags
    :return: Text without HTML tags
    """
    return BeautifulSoup(text, "html.parser").get_text()


def main():
    """
    Main function to initiate the paper querying process.
    """
    print(f"Starting query with DOI: {START_DOI}")
    found = query_papers(START_DOI, max_depth = 1)
    print(f"Found {len(found)} relevant papers")

    # output the found papers into documents.tsv
    with open("data/documents.tsv", "w", encoding="utf-8") as f:
        # write the header
        f.write("DOI\tTitle\n")
        # write one paper per line, tab-separated
        for paper in found:
            doi = paper["doi"]
            title = strip_html(paper["title"].replace("\n", " "))
            # add the DOI and title to the file
            f.write(f"https://doi.org/{doi}\t{title}\n")
            # add the doi to dois.txt
            with open("data/dois.txt", "a", encoding="utf-8") as doi_file:
                doi_file.write(f"{doi}\n")

if __name__ == "__main__":
    main()

