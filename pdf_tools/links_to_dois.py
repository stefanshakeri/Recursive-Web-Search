# get doi links from doi_links.txt and convert them to dois in dois.txt

with open("data/doi_links.txt", "r") as f:
    doi_links = f.readlines()

    # remove the "https://doi.org/" prefix and any trailing whitespace
    dois = [link.strip().replace("https://doi.org/", "") for link in doi_links]

    # write the cleaned DOIs into dois.txt
    with open("data/dois.txt", "w") as wf:
        wf.writelines("\n".join(dois))

