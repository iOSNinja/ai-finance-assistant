"""
loaders.py — Load documents from declared sources.
"""

from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document

from src.rag.sources import SourceConfig
from src.utils.logger import setup_logger

logger = setup_logger("finnie.rag.loaders")
USER_AGENT = "Mozilla/5.0"

# 1. load_documents_for_source(source: SourceConfig) -> list[Document]
    # for each source in the sources.py, extract the urls from the sources, load the data from those urls
    # and convert them into langchain documents
# 2. _fetch_sitemap_urls(sitemap_url: str) -> list[str] 
    # pass the sitemap url
    # this would fetch the xml tree of the urls like <url><loc>https://wiki....</loc></url>
    # we extract the urls from <loc> element & return in a list
# 3. _clean_text(text: str) -> str
    # remove empty lines
    # remove trailing and leading spaces

# private func
def _fetch_sitemap_urls(sitemap_url: str) -> list[str]:
    req = Request(sitemap_url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as response:
        xml = BeautifulSoup(response, "xml")
    urls = [loc.text for loc in xml.find_all("loc")]
    logger.info("Sitemap %s returned %d urls", sitemap_url, len(urls))
    
    return urls

# private func
def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()] # split into a list of lines & remove trailing & leading white-spaces
    lines = [ln for ln in lines if ln] # drop empty lines
    return "\n".join(lines)

# public func
def load_documents_for_source(source: SourceConfig) -> list[Document]:
    # fetch the urls based on the type of discovery
    if source["discovery"] == "sitemap":
        urls = _fetch_sitemap_urls(source["sitemap_url"])
        if limit:= source.get("limit"):
            urls = urls[:limit]
    else:
        urls = source["urls"]

    logger.info("Loading %d URLs from source '%s'", len(urls), source["name"])

    # load each URL as a document
    docs:list[Document] = []
    for url in urls:
        try:
            loader = WebBaseLoader(url)
            loader.requests_kwargs = {"headers": {"User-Agent": USER_AGENT}}
            loaded = loader.load()

            # for each loaded doc, clean the text body & add metadata for filtering later
            for d in loaded:
                d.page_content = _clean_text(d.page_content)
                d.metadata["source_url"] = url
                d.metadata["source_name"] = source["name"]
                d.metadata["category"] = source["category"]
            docs.extend(loaded)
        except Exception as e:
            logger.warning("Failed to load %s - %s: %s", url, type(e).__name__, e)
            continue
        
    logger.info("Source '%s' loaded %d docs", source["name"], len(docs))
    return docs    
    

