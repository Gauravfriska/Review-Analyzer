import pandas as pd
from google_play_scraper import Sort, reviews_all, reviews
from datetime import datetime
import time

# --- CONFIGURATION ---
APP_ID = 'in.swiggy.android'  # Example: Swiggy's ID from Play Store URL
START_DATE = datetime(2024, 6, 1) # The cutoff date you requested
CSV_FILENAME = 'daily_reviews_batch.csv'
MAX_REVIEWS = 100000 # <--- LIMIT ADDED HERE

def fetch_and_filter_reviews():
    print(f"Fetching reviews for {APP_ID}...")
    
    all_reviews = []
    continuation_token = None
    
    # Fetch in batches until we reach dates older than START_DATE or hit MAX_REVIEWS
    while True:
        result, continuation_token = reviews(
            APP_ID,
            lang='en',             # Language
            country='in',          # Country
            sort=Sort.NEWEST,      # Start from today and go back
            count=200,             # Number of reviews per request
            continuation_token=continuation_token
        )
        
        # Check dates in this batch
        batch_new_data = []
        stop_fetching = False
        
        for review in result:
            review_date = review['at'] # 'at' is the timestamp key
            
            if review_date >= START_DATE:
                batch_new_data.append(review)
            else:
                # We found a review older than June 1st, 2024
                stop_fetching = True
        
        all_reviews.extend(batch_new_data)
        
        # --- NEW LOGIC: CHECK LIMIT ---
        if len(all_reviews) >= MAX_REVIEWS:
            print(f"Limit of {MAX_REVIEWS} reviews reached. Stopping.")
            all_reviews = all_reviews[:MAX_REVIEWS] # Trim to exact number
            break
            
        print(f"Collected {len(all_reviews)} reviews so far...")
        
        if stop_fetching or not continuation_token:
            break
            
        time.sleep(1) # Be polite to Google's servers

    return all_reviews

def save_to_csv(data):
    if not data:
        print("No reviews found for this period.")
        return

    # Convert list of dicts to Pandas DataFrame
    df = pd.DataFrame(data)
    
    # Select only useful columns for your Trend Analysis
    df = df[['at', 'content', 'score', 'userName']]
    
    # Rename for clarity
    df.columns = ['Date', 'Review_Text', 'Rating', 'User']
    
    # Export to CSV
    df.to_csv(CSV_FILENAME, index=False)
    print(f"SUCCESS: Saved {len(df)} reviews to {CSV_FILENAME}")

# --- EXECUTION ---
if __name__ == "__main__":
    data = fetch_and_filter_reviews()
    save_to_csv(data)