import pandas as pd
from datetime import datetime, timedelta
from mistralai import Mistral
import json
import os

# --- CONFIGURATION ---
MISTRAL_API_KEY = "aB3dzpUhuxqm2RrojHJF8Dt9I7l9vgfM"
HISTORY_FILE = 'review_history.csv'
FILENAME = 'daily_reviews_batch.csv'

# Initialize Mistral Client
client = Mistral(api_key=MISTRAL_API_KEY)

class ReviewAgent:
    def __init__(self):
        # 1. Smart File Detection for Source (Raw Batch)
        self.source_path = FILENAME
        if not os.path.exists(self.source_path):
             # Try looking in parent directory if not found
             if os.path.exists(os.path.join("..", FILENAME)):
                 self.source_path = os.path.join("..", FILENAME)
        
        # 2. Load the Master Data Source (Raw Batch)
        self.master_data = pd.DataFrame()
        if os.path.exists(self.source_path):
            try:
                self.master_data = pd.read_csv(self.source_path)
                # Flexible date parsing
                self.master_data['Date'] = pd.to_datetime(self.master_data['Date'], errors='coerce')
                self.master_data = self.master_data.dropna(subset=['Date']) 
                print(f"Loaded {len(self.master_data)} reviews from source batch.")
            except Exception as e:
                print(f"Error loading source batch: {e}")

        # 3. Load History (Processed Data)
        self.history_path = HISTORY_FILE
        if os.path.exists(self.history_path):
            try:
                self.df = pd.read_csv(self.history_path)
                self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
            except Exception as e:
                print(f"Error loading history: {e}")
                self.df = pd.DataFrame(columns=["Date", "Topic", "Review", "Original_Topic"])
        else:
            self.df = pd.DataFrame(columns=["Date", "Topic", "Review", "Original_Topic"])

    def get_raw_data_date_range(self):
        """
        Returns the Min and Max dates found in the RAW master csv.
        Used by the frontend to set the date picker limits correctly.
        """
        if self.master_data.empty:
            return None, None
            
        dates = self.master_data['Date'].dt.date
        return dates.min(), dates.max()

    def fetch_reviews_for_date(self, target_date_str):
        """Fetches raw reviews for a specific simulation date"""
        if self.master_data.empty:
            return []
            
        # Filter where date part matches
        target_date = pd.to_datetime(target_date_str).date()
        daily_reviews = self.master_data[self.master_data['Date'].dt.date == target_date]
        
        return daily_reviews.to_dict('records')

    def analyze_and_save(self, reviews, date_str):
        """Process reviews with Mistral and append to history"""
        new_rows = []
        
        for r in reviews:
            review_text = r.get('Review_Text', '')
            if not review_text:
                continue
                
            prompt = f"""
            Analyze the following customer review.
            Classify it into ONE of these topics: 
            ['Positive Feedback', 'Delivery Time Issues', 'Food Quality Issues', 'Customer Service Issues', 'Order Accuracy', 'Price/Value'].
            
            Review: "{review_text}"
            
            Return ONLY the topic name.
            """
            
            try:
                # Call Mistral
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}]
                )
                topic = chat_response.choices[0].message.content.strip()
                
                # Create row
                new_row = {
                    "Date": date_str,
                    "Topic": topic,
                    "Review": review_text,
                    "Original_Topic": topic # redundancy for compatibility
                }
                new_rows.append(new_row)
                
            except Exception as e:
                print(f"LLM Error: {e}")
                continue

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            # Normalize date for storage
            new_df['Date'] = pd.to_datetime(new_df['Date'])
            
            # Append to memory
            if self.df.empty:
                self.df = new_df
            else:
                self.df = pd.concat([self.df, new_df], ignore_index=True)
            
            # Save to disk
            self.df.to_csv(self.history_path, index=False)
            
        return new_rows

    def get_trend_matrix(self):
        """Creates the Pivot Table (Rows: Topics, Cols: Dates)"""
        if self.df.empty:
            return pd.DataFrame()
            
        pivot = self.df.pivot_table(
            index='Topic', 
            columns='Date', 
            values='Review', 
            aggfunc='count', 
            fill_value=0
        )
        
        # Sort columns by date
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)
        # Convert column headers to string dates for JSON serialization
        pivot.columns = [d.strftime('%Y-%m-%d') for d in pivot.columns]
        return pivot

    def ask_agent(self, query):
        """Chat with the data"""
        if self.df.empty:
            return "I haven't processed any data yet. Please simulate a day first."
            
        context = self.df.tail(100).to_string()
        
        prompt = f"""
        Context (Last 100 reviews data):
        {context}
        
        User Query: {query}
        
        Answer based on the data. Cite specific dates if possible.
        """
        try:
            resp = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Error processing chat: {e}"

# Singleton instance
agent_system = ReviewAgent()