import os
from dotenv import load_dotenv

# Import the query_papers function from paper_query module
from paper_query import query_papers

# Load environment variables
load_dotenv()
START_DOI = os.getenv("START_DOI")

def main():
    """
    Main function to initiate the paper querying process.
    """
    print(f"Starting query with DOI: {START_DOI}")
    found = query_papers(START_DOI, max_depth = 1)
    print(f"Found {len(found)} relevant papers")

    # output the found papers into documents.tsv
    with open("documents.tsv", "w", encoding="utf-8") as f:
        # write the header
        f.write("DOI\tTitle\n")
        # write one paper per line, tab-separated
        for paper in found:
            doi = paper["doi"]
            title = paper["title"].replace("\n", " ")
            f.write(f"https://doi.org/{doi}\t{title}\n")

if __name__ == "__main__":
    main()

