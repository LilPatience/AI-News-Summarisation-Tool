"""
gemini_summariser.py - Article summariser for AI News Summariser

Uses Google's Gemini Flash (free tier) to generate a single
paragraph summary of each news article.

Integrates with db_manager to:
- Fetch unsummarised articles from the database
- Send article content to Gemini for summarisation
- Update the article with the generated summary
"""

from google import genai
from dotenv import load_dotenv
import os
import sys
import time

# Add project root to path so we can import other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager.db_client import DBClient

# Load environment variables
load_dotenv()

# Get API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def setup_gemini():
    """
    Configure and return the Gemini client using the new google.genai package.

    Returns:
        Gemini client instance
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in .env file. Please add your Gemini API key.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def summarise_article(client, article):
    """
    Generate a one-paragraph summary of a single article using Gemini.

    Args:
        client: Gemini client instance
        article (dict): Article dictionary from the database

    Returns:
        str: Summary paragraph, or empty string if failed
    """
    # Build the text to summarise from available fields
    title = article.get("title", "")
    description = article.get("description", "")
    content = article.get("content", "")

    # Use the best available content
    article_text = content if content else description

    # Skip if there's nothing to summarise
    if not article_text and not title:
        print(f"  Skipping article with no content: {article.get('url', 'no url')}")
        return ""

    # Build the prompt
    prompt = f"""Summarise the following news article into exactly ONE concise paragraph 
(3-5 sentences). Focus on the key facts: who, what, when, where, and why. 
Keep it neutral and informative. Do not include any preamble like "This article discusses..." 
- just go straight into the summary.

Title: {title}

Article: {article_text}"""

    # Retry up to 3 times if we hit rate limits
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )

            # Extract the text from the response
            if response and response.text:
                summary = response.text.strip()
                return summary
            else:
                print(f"  Empty response for: {title[:50]}")
                return ""

        except Exception as e:
            error_msg = str(e).lower()

            # If it's a rate limit error, wait and retry
            if "429" in str(e) or "quota" in error_msg or "rate" in error_msg or "resource" in error_msg:
                wait_time = 30 * (attempt + 1)  # 30s, 60s, 90s
                print(f"  Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"  Gemini error for '{title[:50]}': {e}")
                return ""

    print(f"  Failed after {max_retries} retries: {title[:50]}")
    return ""


def summarise_all():
    """
    Main summarisation function. Fetches all unsummarised articles
    from the database, summarises each one, and updates the database.

    Returns:
        Number of articles successfully summarised
    """
    print("=" * 50)
    print("Starting article summarisation")
    print("=" * 50)

    # Set up Gemini
    client = setup_gemini()

    # Connect to database
    db = DBClient()

    # Get articles that need summarising
    articles = db.get_unsummarised_articles()

    if not articles:
        print("No unsummarised articles found.")
        db.close()
        return 0

    print(f"Found {len(articles)} articles to summarise.\n")

    success_count = 0
    fail_count = 0

    for i, article in enumerate(articles, 1):
        title = article.get("title", "No title")[:60]
        print(f"[{i}/{len(articles)}] Summarising: {title}...")

        # Generate summary
        summary = summarise_article(client, article)

        if summary:
            # Update the article in the database
            updated = db.update_article(article["_id"], {"summary": summary})
            if updated:
                success_count += 1
                print(f"  Done.")
            else:
                fail_count += 1
                print(f"  Failed to update database.")
        else:
            fail_count += 1

        # Rate limiting - wait 6 seconds between requests
        if i < len(articles):
            time.sleep(6)

    # Show summary
    print(f"\n{'=' * 50}")
    print(f"Summarisation complete!")
    print(f"  Total articles:  {len(articles)}")
    print(f"  Summarised:      {success_count}")
    print(f"  Failed:          {fail_count}")
    print(f"{'=' * 50}")

    db.close()
    return success_count


# =============================================================================
# RUN DIRECTLY TO TEST
# =============================================================================

if __name__ == "__main__":
    print("Running article summarisation...\n")

    count = summarise_all()

    print(f"\nDone! Summarised {count} articles.")