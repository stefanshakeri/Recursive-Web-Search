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
    found = query_papers(START_DOI)
    print(f"Found {len(found)} relevant papers:")

    # output the found papers into documents.txt
    with open("documents.txt", "w") as f:
        for paper in found:
            f.write(f"DOI: {paper['doi']}\n")
            f.write(f"Title: {paper['title']}\n")
            
if __name__ == "__main__":
    main()

