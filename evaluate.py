"""
evaluate.py - Testing and evaluation script for AI News Summariser

Generates statistics and evaluation data for the FYP report.
Run this after the pipeline has processed articles.

Outputs:
- Collection stats
- Categorisation distribution and confidence scores
- Summarisation coverage
- Timing benchmarks
- Sample outputs for the report
"""

import time
import json
from datetime import datetime, timezone
from db_manager.db_client import DBClient
from categoriser.embedder import ArticleCategoriser
from dotenv import load_dotenv

load_dotenv()


def get_database_stats():
    """Get overall database statistics."""
    print("=" * 60)
    print("  DATABASE STATISTICS")
    print("=" * 60)

    db = DBClient()

    # Daily collection stats
    stats = db.get_daily_stats()
    print(f"\n  Daily Collection (news_data_raw):")
    print(f"    Total articles:    {stats['total_articles']}")
    print(f"    Summarised:        {stats['summarised']}")
    print(f"    Unsummarised:      {stats['unsummarised']}")
    print(f"    Categorised:       {stats['categorised']}")
    print(f"    Uncategorised:     {stats['uncategorised']}")

    # Warehouse stats
    warehouse_count = db.archived_articles.count_documents({})
    print(f"\n  Warehouse (news_data_warehouse):")
    print(f"    Archived articles: {warehouse_count}")

    # API source breakdown
    print(f"\n  Articles by API Source:")
    for source in ["newsapi", "gnews", "mediastack"]:
        count = db.articles.count_documents({"api_source": source})
        print(f"    {source:15s}: {count}")

    db.close()
    return stats


def get_category_distribution():
    """Get category distribution and confidence stats."""
    print("\n" + "=" * 60)
    print("  CATEGORISATION ANALYSIS")
    print("=" * 60)

    db = DBClient()
    articles = db.get_all_articles()

    category_data = {}
    confidence_scores = []

    for article in articles:
        cat = article.get("category", "")
        conf = article.get("category_confidence", 0)

        if cat:
            if cat not in category_data:
                category_data[cat] = {"count": 0, "confidences": []}
            category_data[cat]["count"] += 1
            if conf:
                category_data[cat]["confidences"].append(conf)
                confidence_scores.append(conf)

    print(f"\n  {'Category':<20} {'Count':>6} {'Avg Confidence':>16} {'Min':>8} {'Max':>8}")
    print(f"  {'-'*18:<20} {'-'*6:>6} {'-'*14:>16} {'-'*6:>8} {'-'*6:>8}")

    for cat in sorted(category_data.keys(), key=lambda x: category_data[x]["count"], reverse=True):
        data = category_data[cat]
        confs = data["confidences"]
        avg_conf = sum(confs) / len(confs) if confs else 0
        min_conf = min(confs) if confs else 0
        max_conf = max(confs) if confs else 0
        print(f"  {cat:<20} {data['count']:>6} {avg_conf:>15.4f} {min_conf:>8.4f} {max_conf:>8.4f}")

    if confidence_scores:
        overall_avg = sum(confidence_scores) / len(confidence_scores)
        print(f"\n  Overall average confidence: {overall_avg:.4f}")
        print(f"  Overall min confidence:     {min(confidence_scores):.4f}")
        print(f"  Overall max confidence:     {max(confidence_scores):.4f}")

    db.close()
    return category_data


def get_summary_samples(n=5):
    """Get sample summaries for the report."""
    print("\n" + "=" * 60)
    print(f"  SAMPLE SUMMARIES (Top {n})")
    print("=" * 60)

    db = DBClient()
    articles = list(db.articles.find(
        {"summary": {"$exists": True, "$ne": ""}},
    ).limit(n))

    for i, article in enumerate(articles, 1):
        print(f"\n  --- Article {i} ---")
        print(f"  Title:    {article.get('title', 'N/A')[:80]}")
        print(f"  Source:   {article.get('source', 'N/A')}")
        print(f"  Category: {article.get('category', 'N/A')} "
              f"(confidence: {article.get('category_confidence', 'N/A')})")
        print(f"  Summary:  {article.get('summary', 'N/A')[:200]}...")
        print(f"  URL:      {article.get('url', 'N/A')[:80]}")

    db.close()
    return articles


def benchmark_categoriser():
    """Benchmark the categorisation speed."""
    print("\n" + "=" * 60)
    print("  CATEGORISATION BENCHMARK")
    print("=" * 60)

    db = DBClient()
    articles = db.get_all_articles()

    if not articles:
        print("  No articles to benchmark.")
        db.close()
        return

    # Time the model loading
    start = time.time()
    categoriser = ArticleCategoriser()
    load_time = time.time() - start
    print(f"\n  Model load time:       {load_time:.2f}s")

    # Time the categorisation of all articles
    start = time.time()
    for article in articles:
        categoriser.categorise_article(article)
    total_time = time.time() - start

    per_article = total_time / len(articles) if articles else 0
    print(f"  Total categorisation:  {total_time:.2f}s for {len(articles)} articles")
    print(f"  Per article:           {per_article:.4f}s ({per_article*1000:.1f}ms)")
    print(f"  Throughput:            {len(articles)/total_time:.1f} articles/second")

    db.close()
    return {
        "model_load_time": round(load_time, 2),
        "total_time": round(total_time, 2),
        "per_article": round(per_article, 4),
        "throughput": round(len(articles) / total_time, 1),
        "article_count": len(articles)
    }


def check_deduplication_effectiveness():
    """Check how many unique URLs vs total articles."""
    print("\n" + "=" * 60)
    print("  DEDUPLICATION CHECK")
    print("=" * 60)

    db = DBClient()
    total = db.articles.count_documents({})
    urls = db.get_all_urls()
    unique_urls = len(urls)

    print(f"\n  Total articles in DB:  {total}")
    print(f"  Unique URLs:           {unique_urls}")
    print(f"  Duplicates found:      {total - unique_urls}")
    print(f"  Dedup effectiveness:   {'100%' if total == unique_urls else f'{(unique_urls/total)*100:.1f}%'}")

    db.close()
    return {"total": total, "unique": unique_urls, "duplicates": total - unique_urls}


def evaluate_categorisation_accuracy():
    """
    Display articles with their assigned categories for manual review.
    Prints a table you can use to manually check accuracy.
    """
    print("\n" + "=" * 60)
    print("  CATEGORISATION ACCURACY REVIEW")
    print("  (Manually check if these categories are correct)")
    print("=" * 60)

    db = DBClient()
    articles = list(db.articles.find(
        {"category": {"$exists": True, "$ne": ""}},
    ).limit(20))

    print(f"\n  {'#':<4} {'Title':<55} {'Category':<18} {'Conf':>6}")
    print(f"  {'-'*3:<4} {'-'*53:<55} {'-'*16:<18} {'-'*6:>6}")

    for i, article in enumerate(articles, 1):
        title = article.get("title", "N/A")[:53]
        cat = article.get("category", "N/A")
        conf = article.get("category_confidence", 0)
        print(f"  {i:<4} {title:<55} {cat:<18} {conf:>6.3f}")

    print(f"\n  Review the above and count how many categories are correct.")
    print(f"  Accuracy = correct / {len(articles)} * 100")

    db.close()


def run_full_evaluation():
    """Run all evaluation steps."""
    print("\n" + "#" * 60)
    print("#  AI NEWS SUMMARISER - FULL EVALUATION")
    print(f"#  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("#" * 60)

    # 1. Database stats
    stats = get_database_stats()

    # 2. Category distribution
    cat_data = get_category_distribution()

    # 3. Dedup check
    dedup = check_deduplication_effectiveness()

    # 4. Categoriser benchmark
    benchmark = benchmark_categoriser()

    # 5. Sample summaries
    samples = get_summary_samples(5)

    # 6. Accuracy review table
    evaluate_categorisation_accuracy()


if __name__ == "__main__":
    run_full_evaluation()
