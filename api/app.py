
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

#Load environment variables
load_dotenv()
app = Flask(__name__)
#For github pages 
CORS(app)

#MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["news_data_raw"]
articles_collection = db["articles"]


@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "online",
        "service": "AI News Summariser API",
        "endpoints": [
            "/api/articles?category=Technology&limit=5",
            "/api/categories",
            "/api/stats"
        ]
    })

#Collects articles
@app.route("/api/articles")
def get_articles():
    category = request.args.get("category", "")
    limit = min(int(request.args.get("limit", 5)), 20)

    if not category:
        return jsonify({"error": "Please provide a category parameter"}), 400

    #Only return articles that have been summarised
    query = {
        "category": category,
        "summary": {"$exists": True, "$ne": ""}
    }

    #Fetch articles, most recent first
    cursor = articles_collection.find(
        query,
        {
            "_id": 0,         
            "title": 1,
            "summary": 1,
            "url": 1,
            "source": 1,
            "published_at": 1,
            "category": 1,
        }
    ).sort("published_at", -1).limit(limit)

    articles = list(cursor)

    return jsonify({
        "category": category,
        "count": len(articles),
        "articles": articles
    })

#Get all available categories and how many articles are in each.
@app.route("/api/categories")
def get_categories():
    try:
        pipeline = [
            {"$match": {"category": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]

        results = list(articles_collection.aggregate(pipeline))

        categories = [
            {"name": str(r["_id"]), "count": r["count"]}
            for r in results
        ]

        return jsonify({"categories": categories})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Get summary statistics about the database.
@app.route("/api/stats")
def get_stats():
    total = articles_collection.count_documents({})
    summarised = articles_collection.count_documents({"summary": {"$exists": True, "$ne": ""}})
    categorised = articles_collection.count_documents({"category": {"$exists": True, "$ne": ""}})

    return jsonify({
        "total_articles": total,
        "summarised": summarised,
        "categorised": categorised
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
