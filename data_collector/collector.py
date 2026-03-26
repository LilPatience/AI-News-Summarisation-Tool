"""
collector.py - News data collector for AI News Summariser

Fetches articles from three news APIs:
- NewsAPI.org
- GNews.io
- API.MediaStack.com

Each API returns data in a different format, so this module
normalises everything into a common schema before storing.
"""

import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import sys

# Add project root to path so we can import other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager.db_client import DBClient
from data_collector.dedup import deduplicate

# Load environment variables
load_dotenv()

# API keys from .env file
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
GNEWS_KEY = os.getenv("GNEWS_KEY")
MEDIASTACK_KEY = os.getenv("MEDIASTACK_KEY")


def normalise_article(title, description, content, url, source, published_at, api_source):
    """
    Convert an article from any API into our standard format.
    This ensures all articles look the same in the database
    regardless of which API they came from.

    Args:
        title (str): Article headline
        description (str): Short description/snippet
        content (str): Full article content (if available)
        url (str): Link to original article
        source (str): News source name (e.g., "BBC News")
        published_at (str): Publication date string
        api_source (str): Which API this came from

    Returns:
        Dictionary in our standard article format
    """
    return {
        "title": title or "",
        "description": description or "",
        "content": content or "",
        "url": url or "",
        "source": source or "Unknown",
        "published_at": published_at or "",
        "api_source": api_source,
        "category": "",       # Will be filled by categoriser
        "summary": "",        # Will be filled by summariser
    }


# =============================================================================
# API 1: NewsAPI.org
# =============================================================================

def fetch_newsapi(query="latest news", page_size=20):
    """
    Fetch articles from NewsAPI.org

    API docs: https://newsapi.org/docs/endpoints/everything

    Args:
        query (str): Search query
        page_size (int): Number of articles to fetch (max 100)

    Returns:
        List of normalised article dictionaries
    """
    if not NEWSAPI_KEY:
        print("WARNING: NEWSAPI_KEY not found in .env file. Skipping NewsAPI.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": NEWSAPI_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []

        articles = []
        for item in data.get("articles", []):
            article = normalise_article(
                title=item.get("title"),
                description=item.get("description"),
                content=item.get("content"),
                url=item.get("url"),
                source=item.get("source", {}).get("name"),
                published_at=item.get("publishedAt"),
                api_source="newsapi"
            )
            articles.append(article)

        print(f"NewsAPI: Fetched {len(articles)} articles.")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"NewsAPI request failed: {e}")
        return []


# =============================================================================
# API 2: GNews.io
# =============================================================================

def fetch_gnews(query="latest news", max_results=10):
    """
    Fetch articles from GNews.io

    API docs: https://gnews.io/docs/v4

    Args:
        query (str): Search query
        max_results (int): Number of articles to fetch (max 10 on free plan)

    Returns:
        List of normalised article dictionaries
    """
    if not GNEWS_KEY:
        print("WARNING: GNEWS_KEY not found in .env file. Skipping GNews.")
        return []

    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "max": max_results,
        "lang": "en",
        "token": GNEWS_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get("articles", []):
            article = normalise_article(
                title=item.get("title"),
                description=item.get("description"),
                content=item.get("content"),
                url=item.get("url"),
                source=item.get("source", {}).get("name"),
                published_at=item.get("publishedAt"),
                api_source="gnews"
            )
            articles.append(article)

        print(f"GNews: Fetched {len(articles)} articles.")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"GNews request failed: {e}")
        return []


# =============================================================================
# API 3: MediaStack
# =============================================================================

def fetch_mediastack(keywords="latest news", limit=25):
    """
    Fetch articles from MediaStack API

    API docs: http://mediastack.com/documentation

    Note: Free plan only supports HTTP (not HTTPS)

    Args:
        keywords (str): Search keywords
        limit (int): Number of articles to fetch (max 25 on free plan)

    Returns:
        List of normalised article dictionaries
    """
    if not MEDIASTACK_KEY:
        print("WARNING: MEDIASTACK_KEY not found in .env file. Skipping MediaStack.")
        return []

    # Note: MediaStack free plan uses HTTP, not HTTPS
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": MEDIASTACK_KEY,
        "keywords": keywords,
        "languages": "en",
        "limit": limit,
        "sort": "published_desc"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            print(f"MediaStack error: {data['error'].get('message', 'Unknown error')}")
            return []

        articles = []
        for item in data.get("data", []):
            article = normalise_article(
                title=item.get("title"),
                description=item.get("description"),
                content=item.get("description"),  # MediaStack doesn't give full content
                url=item.get("url"),
                source=item.get("source"),
                published_at=item.get("published_at"),
                api_source="mediastack"
            )
            articles.append(article)

        print(f"MediaStack: Fetched {len(articles)} articles.")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"MediaStack request failed: {e}")
        return []


# =============================================================================
# MAIN COLLECTION FUNCTION
# =============================================================================

def collect_all(query="latest news"):
    """
    Main collection function. Fetches from all three APIs,
    deduplicates, and stores in MongoDB.

    This is the function that gets called by the daily scheduler.

    Args:
        query (str): Search query to use across all APIs

    Returns:
        Number of new articles inserted
    """
    print("=" * 50)
    print(f"Starting data collection: '{query}'")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    # Fetch from all three APIs
    all_articles = []

    newsapi_articles = fetch_newsapi(query=query)
    all_articles.extend(newsapi_articles)

    gnews_articles = fetch_gnews(query=query)
    all_articles.extend(gnews_articles)

    mediastack_articles = fetch_mediastack(keywords=query)
    all_articles.extend(mediastack_articles)

    print(f"\nTotal articles fetched: {len(all_articles)}")

    if not all_articles:
        print("No articles fetched from any API.")
        return 0

    # Connect to database
    db = DBClient()

    # Get existing URLs for deduplication
    existing_urls = db.get_all_urls()

    # Deduplicate
    new_articles = deduplicate(all_articles, existing_urls)

    if not new_articles:
        print("No new unique articles to insert.")
        db.close()
        return 0

    # Insert into database
    inserted_ids = db.insert_articles(new_articles)

    # Show summary
    print(f"\n{'=' * 50}")
    print(f"Collection complete!")
    print(f"  Fetched:    {len(all_articles)}")
    print(f"  New unique: {len(new_articles)}")
    print(f"  Inserted:   {len(inserted_ids)}")
    print(f"{'=' * 50}")

    db.close()
    return len(inserted_ids)


# =============================================================================
# RUN DIRECTLY TO TEST
# =============================================================================

if __name__ == "__main__":
    # Test the collector
    print("Running test collection...\n")

    # You can change the query to test different topics
    count = collect_all(query="technology")

    print(f"\nDone! Inserted {count} articles.")