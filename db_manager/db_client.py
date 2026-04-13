
#Handles all database operations:
#- Connecting to MongoDB Atlas
#- Inserting new articles into the daily collection
#- Retrieving articles (all, by category, by ID)
#- Archiving articles older than 24 hours to the warehouse
#- Retrieving archived articles


from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os


load_dotenv()


class DBClient:
   
    #Main database client class.
    #Uses two databases:
    #- news_data_raw: stores freshly collected articles (last 24 hours)
    #- news_data_warehouse: stores archived articles (older than 24 hours)
   

    def __init__(self):
        #Initialise the database client.
        #Connects to MongoDB Atlas using the connection string from .env
        #and sets up references to both databases and their collections.
  
        #Get connection string from .env file
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in .env file. Please add your MongoDB connection string.")

        #Create the MongoDB client connection
        self.client = MongoClient(mongo_uri)

         
        self.raw_db = self.client["news_data_raw"]
        self.warehouse_db = self.client["news_data_warehouse"]

      
        self.articles = self.raw_db["articles"]
        self.archived_articles = self.warehouse_db["archived_articles"]

    
 
    def test_connection(self):

        #Test that the MongoDB connection is working.
        #Returns True if successful, raises an exception if not.

        try:
            #ping command forces a round trip to the server
            self.client.admin.command("ping")
            print("Successfully connected to MongoDB Atlas!")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            raise

  
    #Insert

    def insert_article(self, article):

        #Insert a single article into the daily collection.

        #Add a timestamp for when we collected this article
        article["collected_at"] = datetime.now(timezone.utc)

        result = self.articles.insert_one(article)
        return result.inserted_id

    def insert_articles(self, articles_list):
        #Insert multiple articles at once (more efficient than one at a time).

        if not articles_list:
            print("No articles to insert.")
            return []

        #Add collection timestamp to each article
        for article in articles_list:
            article["collected_at"] = datetime.now(timezone.utc)

        result = self.articles.insert_many(articles_list)
        print(f"Inserted {len(result.inserted_ids)} articles into daily collection.")
        return result.inserted_ids


    #Retrieve
  

    def get_all_articles(self):

        #Get all articles from the daily collection.

        return list(self.articles.find())

    def get_articles_by_category(self, category):

        #Get articles filtered by category.

        return list(self.articles.find({"category": category}))

    def get_article_by_id(self, article_id):

        #Get a single article by its MongoDB ObjectId.

        from bson.objectid import ObjectId
        return self.articles.find_one({"_id": ObjectId(article_id)})

    def get_unsummarised_articles(self):

        #Get articles that haven't been summarised yet.
        #Useful for the summariser to know what still needs processing.

        return list(self.articles.find({
            "$or": [
                {"summary": {"$exists": False}},
                {"summary": None},
                {"summary": ""}
            ]
        }))

    def get_uncategorised_articles(self):
 
        #Get articles that haven't been categorised yet.
        #Useful for the categoriser to know what still needs processing.

        return list(self.articles.find({
            "$or": [
                {"category": {"$exists": False}},
                {"category": None},
                {"category": ""}
            ]
        }))

    def get_top_articles(self, category, limit=5):

        #Get the top N most recent articles for a category.
        #This is what the webapp will call to display articles.

        return list(
            self.articles.find({"category": category})
            .sort("published_at", -1)
            .limit(limit)
        )

 
    #Update
    def update_article(self, article_id, update_data):
 
        #Update an existing article with new data.
        #Used by the summariser and categoriser to add their results.

        from bson.objectid import ObjectId
        result = self.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

   
    #Archiving
    def archive_old_articles(self):
        #Move articles older than 24 hours from the daily collection to the warehouse collection.

        #Calculate the cutoff time (24 hours ago)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        #Find all articles older than 24 hours
        old_articles = list(self.articles.find({
            "collected_at": {"$lt": cutoff_time}
        }))

        if not old_articles:
            print("No articles to archive.")
            return 0

        #Insert them into the warehouse
        self.archived_articles.insert_many(old_articles)

        #Remove them from the daily collection
        self.articles.delete_many({
            "collected_at": {"$lt": cutoff_time}
        })

        print(f"Archived {len(old_articles)} articles to warehouse.")
        return len(old_articles)

    def get_archived_articles(self, category=None, limit=50):
 
        #Retrieve archived articles from the warehouse.

        query = {}
        if category:
            query["category"] = category

        return list(
            self.archived_articles.find(query)
            .sort("published_at", -1)
            .limit(limit)
        )


    def url_exists(self, url):

        #Check if an article URL already exists in the daily collection.
        #Used by the deduplication system.

        return self.articles.find_one({"url": url}) is not None

    def get_all_urls(self):

        #Get all URLs currently in the daily collection.
        #Used for batch deduplication (faster than checking one by one).

        urls = self.articles.find({}, {"url": 1})
        return set(doc["url"] for doc in urls if "url" in doc)

    def get_daily_stats(self):
 
        #Get summary statistics for the daily collection.

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

        #Remove all articles from the daily collection.
  
        result = self.articles.delete_many({})
        print(f"Cleared {result.deleted_count} articles from daily collection.")
        return result.deleted_count

    def close(self):
        self.client.close()
        print("MongoDB connection closed.")


#Test

if __name__ == "__main__":

    print("Testing MongoDB connection...")
    print("-" * 40)

    db = DBClient()
    db.test_connection()


    stats = db.get_daily_stats()
    print(f"\nDaily Collection Stats:")
    print(f"  Total articles:   {stats['total_articles']}")
    print(f"  Summarised:       {stats['summarised']}")
    print(f"  Categorised:      {stats['categorised']}")

    #Show warehouse count
    warehouse_count = db.archived_articles.count_documents({})
    print(f"\nWarehouse articles: {warehouse_count}")

    db.close()