
#Removes duplicate articles by comparing URLs.
#Works with the db_manager to check what's already in the database.


import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def remove_duplicates_from_list(articles_list):
 
    #Remove duplicate articles within a list by comparing URLs.
    #This is used BEFORE inserting into the database, to handle
    #duplicates that come from querying multiple APIs.

    seen_urls = set()
    unique_articles = []

    for article in articles_list:
        url = article.get("url")

        #Skip articles with no URL
        if not url:
            continue

        #Only keep the first occurrence of each URL
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    duplicates_removed = len(articles_list) - len(unique_articles)
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate articles from batch.")

    return unique_articles


def filter_existing_urls(articles_list, existing_urls):

    #Remove articles whose URLs already exist in the database.
    #This prevents re-inserting articles we've already collected.

    new_articles = []

    for article in articles_list:
        url = article.get("url")
        if url and url not in existing_urls:
            new_articles.append(article)

    filtered_count = len(articles_list) - len(new_articles)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} articles already in database.")

    return new_articles


def deduplicate(articles_list, existing_urls):

    #Full deduplication pipeline:
    #1. Remove duplicates within the batch (from multiple APIs)
    #2. Remove articles already in the database

    print(f"\nStarting deduplication of {len(articles_list)} articles...")

    #Step 1: Remove duplicates within the batch
    unique = remove_duplicates_from_list(articles_list)

    #Step 2: Remove articles already in the database
    new_articles = filter_existing_urls(unique, existing_urls)

    print(f"Deduplication complete: {len(new_articles)} new unique articles.")
    return new_articles
