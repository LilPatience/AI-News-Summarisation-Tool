# AI News Summarisation Tool

An AI-powered news aggregation and summarisation system that collects articles from multiple news APIs, categorises them using NLP embeddings, and generates concise summaries using Google's Gemini AI. The summarised articles are served through a live web application.

**Live Demo:** [https://lilpatience.github.io/AI-News-Summarisation-Tool/](https://lilpatience.github.io/AI-News-Summarisation-Tool/)

---

## How It Works

The system follows a daily pipeline that runs in four stages:

1. **Archive** — Articles older than 24 hours are moved from the daily collection to a data warehouse for long-term storage.
2. **Collect** — Fresh articles are fetched from three news APIs (NewsAPI, GNews, MediaStack), normalised into a common format, and deduplicated by URL before being stored in MongoDB.
3. **Categorise** — Each article's title and description are encoded into vector embeddings using a sentence-transformer model, then compared against predefined category embeddings using cosine similarity to assign the best matching category.
4. **Summarise** — Article content is sent to Google's Gemini Flash model, which generates a single concise paragraph summary focusing on the key facts.

The web application lets users select a topic and view the top 5 most recent summarised articles along with the original source link.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   NewsAPI.org    │     │    GNews.io     │     │   MediaStack    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────┬───────────┘───────────────────────┘
                     │
              ┌──────▼──────┐
              │   Collector  │  Fetch + Normalise + Deduplicate
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   MongoDB    │  news_data_raw / news_data_warehouse
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         │                       │
  ┌──────▼──────┐        ┌──────▼──────┐
  │ Categoriser  │        │ Summariser  │
  │ (Embeddings) │        │  (Gemini)   │
  └──────┬──────┘        └──────┬──────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │  Flask API   │  Hosted on Render
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   Web App    │  Hosted on GitHub Pages
              └─────────────┘
```

---

## Project Structure

```
AI-News-Summarisation-Tool/
├── api/                    # Flask REST API (deployed on Render)
│   ├── app.py
│   └── requirements.txt
├── categoriser/            # Article categorisation using embeddings
│   ├── __init__.py
│   └── embedder.py
├── data_collector/         # News API integration and deduplication
│   ├── __init__.py
│   ├── collector.py
│   └── dedup.py
├── db_manager/             # MongoDB database interface
│   ├── __init__.py
│   └── db_client.py
├── docs/                   # Web application (GitHub Pages)
│   └── index.html
├── summariser/             # Gemini AI summarisation
│   ├── __init__.py
│   └── gemini_summariser.py
├── main.py                 # Daily pipeline orchestrator
├── requirements.txt        # Python dependencies
├── .env.example            # API key template
└── README.md
```

---

## Technologies Used

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Database | MongoDB Atlas |
| News APIs | NewsAPI.org, GNews.io, MediaStack |
| Categorisation | sentence-transformers (all-MiniLM-L6-v2) |
| Summarisation | Google Gemini 2.5 Flash-Lite |
| Backend API | Flask + Gunicorn |
| Frontend | HTML, CSS, JavaScript |
| API Hosting | Render |
| Frontend Hosting | GitHub Pages |

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Git
- MongoDB Atlas account
- API keys for NewsAPI, GNews, MediaStack, and Google Gemini

### Installation

1. Clone the repository:
```bash
git clone https://github.com/LilPatience/AI-News-Summarisation-Tool.git
cd AI-News-Summarisation-Tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your API keys:
```
MONGO_URI=your_mongodb_connection_string
NEWSAPI_KEY=your_newsapi_key
GNEWS_KEY=your_gnews_key
MEDIASTACK_KEY=your_mediastack_key
GEMINI_API_KEY=your_gemini_key
```

4. Run the pipeline:
```bash
python main.py --once
```

### Running Individual Components

```bash
# Test database connection
python db_manager/db_client.py

# Collect articles only
python data_collector/collector.py

# Categorise articles only
python categoriser/embedder.py

# Summarise articles only
python summariser/gemini_summariser.py
```

---

## API Endpoints

The Flask API is hosted at `https://ai-news-summarisation-tool.onrender.com`

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /api/articles?category=Technology&limit=5` | Get articles by category |
| `GET /api/categories` | List all categories with article counts |
| `GET /api/stats` | Database statistics |

---

## Categories

Articles are automatically classified into 8 predefined categories:

- Technology
- Politics
- Business
- Science
- Sports
- Health
- Entertainment
- World News

Categorisation uses cosine similarity between article embeddings and predefined category description embeddings, with a confidence score stored alongside each classification.