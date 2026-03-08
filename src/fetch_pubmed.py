from Bio import Entrez
from datetime import datetime
from xml.etree import ElementTree


Entrez.email = "your_email@example.com"


QUERY = """
(
drug discovery OR molecular docking OR virtual screening
OR QSAR OR QSPR OR ADMET
OR cheminformatics
OR binding affinity
OR structure based drug design
OR molecular generation
OR generative chemistry
OR Bayesian optimization
OR active learning
OR uncertainty quantification
)
"""


def fetch_pubmed_papers(days_back=14, max_results=200):

    handle = Entrez.esearch(
        db="pubmed",
        term=QUERY,
        retmax=max_results,
        sort="pub date"
    )

    record = Entrez.read(handle)
    ids = record["IdList"]

    papers = []

    if not ids:
        return papers

    fetch_handle = Entrez.efetch(
        db="pubmed",
        id=",".join(ids),
        rettype="abstract",
        retmode="xml"
    )

    xml_data = fetch_handle.read()
    root = ElementTree.fromstring(xml_data)

    for article in root.findall(".//PubmedArticle"):

        title = article.findtext(".//ArticleTitle")
        abstract = article.findtext(".//AbstractText")

        if not abstract:
            continue

        pmid = article.findtext(".//PMID")

        papers.append({
            "title": title,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "source": "pubmed",
            "published": datetime.utcnow().isoformat()
        })

    return papers