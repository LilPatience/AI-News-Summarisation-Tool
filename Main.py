
#main.py - Daily pipeline for AI News Summariser

#Orchestrates the entire daily workflow:
#1. Archive old articles (>24 hours) to the warehouse
#2. Collect new articles from all 3 news APIs
#3. Categorise new articles using sentence-transformers
#4. Summarise new articles using Gemini Flash
#Can be run manually or left running for automatic daily execution.


from datetime import datetime, timezone
import time
import schedule

from db_manager.db_client import DBClient
from data_collector.collector import collect_all
from categoriser.embedder import categorise_all
from summariser.gemini_summariser import summarise_all


def daily_pipeline():
 
    #Run the complete daily pipeline.
    #This is the main function that gets called every 24 hours.
 
    start_time = time.time()

    print("\n" + "=" * 60)
    print("  AI NEWS SUMMARISER - DAILY PIPELINE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

  
    #Step 1: Archive old articles
  
    #print("\n[STEP 1/4] Archiving old articles...")
    #print("-" * 40)
    #try:
    #    db = DBClient()
    #    archived_count = db.archive_old_articles()
    #    db.close()
    #    print(f"Result: {archived_count} articles archived.\n")
    #except Exception as e:
    #    print(f"Archiving failed: {e}\n")

   
    #Step 2: Collect new articles
  
    print("[STEP 2/4] Collecting new articles...")
    print("-" * 40)
    try:
        collected_count = collect_all(query="latest news")
        print(f"Result: {collected_count} new articles collected.\n")
    except Exception as e:
        print(f"Collection failed: {e}\n")


    #Step 3: Categorise articles

    print("[STEP 3/4] Categorising articles...")
    print("-" * 40)
    try:
        categorised_count = categorise_all()
        print(f"Result: {categorised_count} articles categorised.\n")
    except Exception as e:
        print(f"Categorisation failed: {e}\n")

  
    #Step 4: Summarise articles

    print("[STEP 4/4] Summarising articles...")
    print("-" * 40)
    try:
        summarised_count = summarise_all()
        print(f"Result: {summarised_count} articles summarised.\n")
    except Exception as e:
        print(f"Summarisation failed: {e}\n")


    #Summary
  
    elapsed = round(time.time() - start_time, 1)

    print("=" * 60)
    print("  PIPELINE COMPLETE")
    print(f"  Time taken: {elapsed}s")
    print("=" * 60)

    #Show current database stats
    try:
        db = DBClient()
        stats = db.get_daily_stats()
        warehouse_count = db.archived_articles.count_documents({})
        db.close()

        print(f"\n  Daily collection:")
        print(f"    Total articles:   {stats['total_articles']}")
        print(f"    Summarised:       {stats['summarised']}")
        print(f"    Categorised:      {stats['categorised']}")
        print(f"  Warehouse:          {warehouse_count}")
    except Exception as e:
        print(f"  Could not fetch stats: {e}")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        #Run once and exit: python main.py --once
        print("Running pipeline once...\n")
        daily_pipeline()
    else:
        #Run on a schedule: python main.py
        print("Starting scheduled pipeline...")
        print("Pipeline will run every 24 hours.")
        print("Press Ctrl+C to stop.\n")

        #Run immediately on startup
        daily_pipeline()

        #Then schedule to run every 24 hours
        schedule.every(24).hours.do(daily_pipeline)

        while True:
            schedule.run_pending()
            time.sleep(60)