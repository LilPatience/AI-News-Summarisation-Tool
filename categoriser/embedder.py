"""
embedder.py - Article categoriser for AI News Summariser

Uses sentence-transformers to encode article titles and descriptions
into embeddings, then compares them to predefined category embeddings
using cosine similarity to assign the best matching category.

Runs entirely locally - no API keys or rate limits needed.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv
import sys
import os

# Add project root to path so we can import other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager.db_client import DBClient

# Load environment variables
load_dotenv()

# =========================================================================
# PREDEFINED CATEGORIES
# =========================================================================
# Each category has a list of representative phrases that help the model
# understand what kind of articles belong in that category.
# The more descriptive the phrases, the better the matching.

CATEGORIES = {
    "Technology": [
        "artificial intelligence and machine learning",
        "software development and programming",
        "smartphones tablets and gadgets",
        "cybersecurity and data privacy",
        "tech companies startups and innovation",
        "cloud computing and internet services",
        "social media platforms and apps"
    ],
    "Politics": [
        "government elections and voting",
        "political parties and politicians",
        "legislation laws and policy making",
        "diplomacy and international relations",
        "political campaigns and debates",
        "parliament congress and senate",
        "political protests and movements"
    ],
    "Business": [
        "stock market trading and investments",
        "corporate earnings and financial results",
        "mergers acquisitions and deals",
        "economy inflation and interest rates",
        "banking finance and cryptocurrency",
        "startups venture capital and funding",
        "retail sales and consumer spending"
    ],
    "Science": [
        "scientific research and discoveries",
        "space exploration and astronomy",
        "physics chemistry and biology",
        "climate change and environment",
        "archaeology and paleontology",
        "genetics and evolution",
        "renewable energy and sustainability"
    ],
    "Sports": [
        "football soccer and premier league",
        "basketball tennis and athletics",
        "cricket rugby and golf",
        "olympic games and world championships",
        "sports transfers and player contracts",
        "formula one racing and motorsport",
        "boxing mma and combat sports"
    ],
    "Health": [
        "medicine and medical research",
        "diseases illness and treatments",
        "mental health and wellbeing",
        "vaccines and public health",
        "nutrition diet and fitness",
        "hospitals and healthcare systems",
        "pharmaceutical drugs and clinical trials"
    ],
    "Entertainment": [
        "movies films and cinema",
        "music concerts and albums",
        "television shows and streaming",
        "celebrities and pop culture",
        "video games and gaming",
        "books literature and publishing",
        "art theatre and cultural events"
    ],
    "World News": [
        "international conflicts and wars",
        "natural disasters and emergencies",
        "global humanitarian crises",
        "immigration and refugees",
        "terrorism and security threats",
        "international trade and sanctions",
        "global summits and treaties"
    ]
}


class ArticleCategoriser:
    """
    Categorises news articles using sentence embeddings.

    How it works:
    1. Loads a pre-trained sentence-transformer model
    2. Encodes all category descriptions into embeddings (done once)
    3. For each article, encodes its title + description
    4. Compares the article embedding to each category embedding
    5. Assigns the category with the highest cosine similarity
    """

    def __init__(self):
        """
        Initialise the categoriser.
        Downloads the model on first run (about 90MB), then cached locally.
        """
        print("Loading sentence-transformer model...")
        # all-MiniLM-L6-v2 is small, fast, and good for this use case
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        print("Model loaded.")

        # Pre-compute category embeddings
        self.category_names = list(CATEGORIES.keys())
        self.category_embeddings = self._encode_categories()
        print(f"Encoded {len(self.category_names)} categories.")

    def _encode_categories(self):
        """
        Encode all category descriptions into embeddings.
        For each category, we average the embeddings of all its
        representative phrases to get a single category vector.

        Returns:
            numpy array of shape (num_categories, embedding_dim)
        """
        category_vectors = []

        for category_name in self.category_names:
            phrases = CATEGORIES[category_name]
            # Encode all phrases for this category
            phrase_embeddings = self.model.encode(phrases)
            # Average them to get one vector per category
            avg_embedding = np.mean(phrase_embeddings, axis=0)
            category_vectors.append(avg_embedding)

        return np.array(category_vectors)

    def categorise_article(self, article):
        """
        Assign a category to a single article.

        Args:
            article (dict): Article dictionary with 'title' and 'description'

        Returns:
            tuple: (category_name, confidence_score)
        """
        title = article.get("title", "")
        description = article.get("description", "")

        # Combine title and description for better matching
        text = f"{title}. {description}".strip()

        if not text or text == ".":
            return "World News", 0.0  # Default category for empty articles

        # Encode the article text
        article_embedding = self.model.encode([text])

        # Calculate cosine similarity with all categories
        similarities = cosine_similarity(article_embedding, self.category_embeddings)[0]

        # Find the best matching category
        best_index = np.argmax(similarities)
        best_category = self.category_names[best_index]
        confidence = float(similarities[best_index])

        return best_category, confidence


def categorise_all():
    """
    Main categorisation function. Fetches all uncategorised articles
    from the database, categorises each one, and updates the database.

    Returns:
        Number of articles successfully categorised
    """
    print("=" * 50)
    print("Starting article categorisation")
    print("=" * 50)

    # Initialise the categoriser (loads model)
    categoriser = ArticleCategoriser()

    # Connect to database
    db = DBClient()

    # Get articles that need categorising
    articles = db.get_uncategorised_articles()

    if not articles:
        print("No uncategorised articles found.")
        db.close()
        return 0

    print(f"\nFound {len(articles)} articles to categorise.\n")

    success_count = 0
    category_counts = {}

    for i, article in enumerate(articles, 1):
        title = article.get("title", "No title")[:60]
        print(f"[{i}/{len(articles)}] Categorising: {title}...")

        # Get category
        category, confidence = categoriser.categorise_article(article)

        # Update the article in the database
        updated = db.update_article(article["_id"], {
            "category": category,
            "category_confidence": round(confidence, 4)
        })

        if updated:
            success_count += 1
            # Track category distribution
            category_counts[category] = category_counts.get(category, 0) + 1
            print(f"  -> {category} (confidence: {confidence:.2f})")
        else:
            print(f"  Failed to update database.")

    # Show summary
    print(f"\n{'=' * 50}")
    print(f"Categorisation complete!")
    print(f"  Total articles:  {len(articles)}")
    print(f"  Categorised:     {success_count}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:15s}: {count}")
    print(f"{'=' * 50}")

    db.close()
    return success_count


# =============================================================================
# RUN DIRECTLY TO TEST
# =============================================================================

if __name__ == "__main__":
    print("Running article categorisation...\n")

    count = categorise_all()

    print(f"\nDone! Categorised {count} articles.")