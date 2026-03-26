"""
app.py - Flask API backend for AI News Summariser

A simple REST API that serves article data from MongoDB
to the frontend webapp. Hosted on Render (free tier).

Endpoints:
    GET /api/articles?category=Technology&limit=5
    GET /api/categories
    GET /api/stats
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS so the frontend (on GitHub Pages) can call this API
CORS(app)

# MongoDB connection
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


@app.route("/api/articles")
def get_articles():
    """
    Get articles filtered by category.

    Query Parameters:
        category (str): Category to filter by (required)
        limit (int): Number of articles to return (default 5, max 20)

    Returns:
        JSON with list of articles
    """
    category = request.args.get("category", "")
    limit = min(int(request.args.get("limit", 5)), 20)

    if not category:
        return jsonify({"error": "Please provide a category parameter"}), 400

    # Query MongoDB - only return articles that have been summarised
    query = {
        "category": category,
        "summary": {"$exists": True, "$ne": ""}
    }

    # Fetch articles, sorted by most recent first
    cursor = articles_collection.find(
        query,
        {
            "_id": 0,          # Exclude MongoDB ID (not JSON serialisable)
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


@app.route("/api/categories")
def get_categories():
    """
    Get all available categories and how many articles are in each.

    Returns:
        JSON with category names and article counts
    """
    pipeline = [
        {"$match": {"category": {"$exists": True, "$ne": ""}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    results = list(articles_collection.aggregate(pipeline))

    categories = [
        {"name": r["_id"], "count": r["count"]}
        for r in results
    ]

    return jsonify({"categories": categories})


@app.route("/api/stats")
def get_stats():
    """
    Get summary statistics about the database.

    Returns:
        JSON with article counts
    """
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
