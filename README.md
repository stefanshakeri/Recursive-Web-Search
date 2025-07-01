# Recursive-Web-Search
Search through research papers and informational resources to recursively compile a list of relevant resources. Also generate PDFs from their DOIs. 

### Step 1. environment variables
Create a ```.env``` file with the necessary envrionment variables like so:
```
CROSSREF='https://api.crossref.org/works'
KEYWORDS='[relevant-keyword1, relevant-keyword2, ...]'
MAILTO='example@gmail.com'
START_DOI='[doi of paper you'll start with]'
```

### Step 2. requirments
Run ```pip install requirements.txt``` to install requirements. 

### Step 3. run the file
Run 
```
python papers.py
```
and check ```documents.tsv``` for your DOIs and titles. 

## PDF Generation

### Optional. convert DOI links to DOIs
Run 
```
python pdf_tools/links_to_dois.py
```
to convert a list of doi links in ```doi_links.txt``` into a list of only dois stored in ```dois.txt```

### Step 1. run the file
Run
```
python pdf_tools/pdf_grabber.py
```
and check ```data/pdfs``` for your pdfs. 