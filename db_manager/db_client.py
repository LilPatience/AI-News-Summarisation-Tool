"""
db_client.py - MongoDB interface for AI News Summariser

Handles all database operations:
- Connecting to MongoDB Atlas
- Inserting new articles into the daily collection
- Retrieving articles (all, by category, by ID)
- Archiving articles older than 24 hours to the warehouse
- Retrieving archived articles
"""

from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


class DBClient:
    """
    Main database client class.
    
    Uses two databases:
    - news_data_raw: stores freshly collected articles (last 24 hours)
    - news_data_warehouse: stores archived articles (older than 24 hours)
    """

    def __init__(self):
        """
        Initialise the database client.
        Connects to MongoDB Atlas using the connection string from .env
        and sets up references to both databases and their collections.
        """
        # Get connection string from .env file
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in .env file. Please add your MongoDB connection string.")

        # Create the MongoDB client connection
        self.client = MongoClient(mongo_uri)

        # Reference the two databases (these match your existing Atlas setup)
        self.raw_db = self.client["news_data_raw"]
        self.warehouse_db = self.client["news_data_warehouse"]

        # Reference the collections within each database
        self.articles = self.raw_db["articles"]
        self.archived_articles = self.warehouse_db["archived_articles"]

    # =========================================================================
    # CONNECTION TESTING
    # =========================================================================

    def test_connection(self):
        """
        Test that the MongoDB connection is working.
        Returns True if successful, raises an exception if not.
        """
        try:
            # ping command forces a round trip to the server
            self.client.admin.command("ping")
            print("Successfully connected to MongoDB Atlas!")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            raise

    # =========================================================================
    # INSERT OPERATIONS
    # =========================================================================

    def insert_article(self, article):
        """
        Insert a single article into the daily collection.

        Args:
            article (dict): Article data with keys like:
                - title (str): Article headline
                - description (str): Short description
                - content (str): Full article text
                - url (str): Original article URL
                - source (str): News source name
                - published_at (str): Publication date
                - collected_at (datetime): When we collected it
                - category (str): Assigned category (added later by categoriser)
                - summary (str): AI-generated summary (added later by summariser)

        Returns:
            The inserted document's ID
        """
        # Add a timestamp for when we collected this article
        article["collected_at"] = datetime.now(timezone.utc)

        result = self.articles.insert_one(article)
        return result.inserted_id

    def insert_articles(self, articles_list):
        """
        Insert multiple articles at once (more efficient than one at a time).

        Args:
            articles_list (list): List of article dictionaries

        Returns:
            List of inserted document IDs
        """
        if not articles_list:
            print("No articles to insert.")
            return []

        # Add collection timestamp to each article
        for article in articles_list:
            article["collected_at"] = datetime.now(timezone.utc)

        result = self.articles.insert_many(articles_list)
        print(f"Inserted {len(result.inserted_ids)} articles into daily collection.")
        return result.inserted_ids

    # =========================================================================
    # RETRIEVE OPERATIONS
    # =========================================================================

    def get_all_articles(self):
        """
        Get all articles from the daily collection.

        Returns:
            List of article dictionaries
        """
        return list(self.articles.find())

    def get_articles_by_category(self, category):
        """
        Get articles filtered by category.

        Args:
            category (str): Category name (e.g., "Technology", "Politics")

        Returns:
            List of matching article dictionaries
        """
        return list(self.articles.find({"category": category}))

    def get_article_by_id(self, article_id):
        """
        Get a single article by its MongoDB ObjectId.

        Args:
            article_id: MongoDB ObjectId

        Returns:
            Article dictionary or None
        """
        from bson.objectid import ObjectId
        return self.articles.find_one({"_id": ObjectId(article_id)})

    def get_unsummarised_articles(self):
        """
        Get articles that haven't been summarised yet.
        Useful for the summariser to know what still needs processing.

        Returns:
            List of articles without a 'summary' field
        """
        return list(self.articles.find({
            "$or": [
                {"summary": {"$exists": False}},
                {"summary": None},
                {"summary": ""}
            ]
        }))

    def get_uncategorised_articles(self):
        """
        Get articles that haven't been categorised yet.
        Useful for the categoriser to know what still needs processing.

        Returns:
            List of articles without a 'category' field
        """
        return list(self.articles.find({
            "$or": [
                {"category": {"$exists": False}},
                {"category": None},
                {"category": ""}
            ]
        }))

    def get_top_articles(self, category, limit=5):
        """
        Get the top N most recent articles for a category.
        This is what the webapp will call to display articles.

        Args:
            category (str): Category to filter by
            limit (int): Number of articles to return (default 5)

        Returns:
            List of article dictionaries, sorted newest first
        """
        return list(
            self.articles.find({"category": category})
            .sort("published_at", -1)
            .limit(limit)
        )

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    def update_article(self, article_id, update_data):
        """
        Update an existing article with new data.
        Used by the summariser and categoriser to add their results.

        Args:
            article_id: MongoDB ObjectId of the article
            update_data (dict): Fields to update, e.g., {"summary": "...", "category": "Tech"}

        Returns:
            True if an article was updated, False if not found
        """
        from bson.objectid import ObjectId
        result = self.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    # =========================================================================
    # ARCHIVING OPERATIONS
    # =========================================================================

    def archive_old_articles(self):
        """
        Move articles older than 24 hours from the daily collection
        to the warehouse collection. This keeps the daily collection
        small and fast.

        Returns:
            Number of articles archived
        """
        # Calculate the cutoff time (24 hours ago)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        # Find all articles older than 24 hours
        old_articles = list(self.articles.find({
            "collected_at": {"$lt": cutoff_time}
        }))

        if not old_articles:
            print("No articles to archive.")
            return 0

        # Insert them into the warehouse
        self.archived_articles.insert_many(old_articles)

        # Remove them from the daily collection
        self.articles.delete_many({
            "collected_at": {"$lt": cutoff_time}
        })

        print(f"Archived {len(old_articles)} articles to warehouse.")
        return len(old_articles)

    def get_archived_articles(self, category=None, limit=50):
        """
        Retrieve archived articles from the warehouse.

        Args:
            category (str, optional): Filter by category
            limit (int): Max number of articles to return

        Returns:
            List of archived article dictionaries
        """
        query = {}
        if category:
            query["category"] = category

        return list(
            self.archived_articles.find(query)
            .sort("published_at", -1)
            .limit(limit)
        )

    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================

    def url_exists(self, url):
        """
        Check if an article URL already exists in the daily collection.
        Used by the deduplication system.

        Args:
            url (str): Article URL to check

        Returns:
            True if the URL already exists, False otherwise
        """
        return self.articles.find_one({"url": url}) is not None

    def get_all_urls(self):
        """
        Get all URLs currently in the daily collection.
        Used for batch deduplication (faster than checking one by one).

        Returns:
            Set of URL strings
        """
        urls = self.articles.find({}, {"url": 1})
        return set(doc["url"] for doc in urls if "url" in doc)

    def get_daily_stats(self):
        """
        Get summary statistics for the daily collection.
        Useful for monitoring and debugging.

        Returns:
            Dictionary with stats
        """
        total = self.articles.count_documents({})
        summarised = self.articles.count_documents({"summary": {"$exists": True, "$ne": ""}})
        categorised = self.articles.count_documents({"category": {"$exists": True, "$ne": ""}})

        return {
            "total_articles": total,
            "summarised": summarised,
            "unsummarised": total - summarised,
            "categorised": categorised,
            "uncategorised": total - categorised
        }

    def clear_daily_collection(self):
        """
        Remove all articles from the daily collection.
        Use with caution — mainly for testing.

        Returns:
            Number of articles deleted
        """
        result = self.articles.delete_many({})
        print(f"Cleared {result.deleted_count} articles from daily collection.")
        return result.deleted_count

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
        print("MongoDB connection closed.")


# =============================================================================
# QUICK TEST - Run this file directly to test the connection
# =============================================================================

if __name__ == "__main__":
    # This block only runs when you execute: python db_client.py
    # It won't run when the file is imported by other modules

    print("Testing MongoDB connection...")
    print("-" * 40)

    db = DBClient()
    db.test_connection()

    # Show current stats
    stats = db.get_daily_stats()
    print(f"\nDaily Collection Stats:")
    print(f"  Total articles:   {stats['total_articles']}")
    print(f"  Summarised:       {stats['summarised']}")
    print(f"  Categorised:      {stats['categorised']}")

    # Show warehouse count
    warehouse_count = db.archived_articles.count_documents({})
    print(f"\nWarehouse articles: {warehouse_count}")

    db.close()