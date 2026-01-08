from fastapi import FastAPI, Query
from agent_engine import agent_system
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/simulate-day")
def simulate_day(date: Optional[str] = Query(None)):
    """
    Trigger the agent to pull data for a specific date.
    If no date provided, defaults to internal clock (not recommended for this interactive mode).
    """
    if date:
        target_date = date
    else:
        # Fallback or default behavior
        target_date = "2026-01-07"

    raw_reviews = agent_system.fetch_reviews_for_date(target_date)
    
    if not raw_reviews:
        return {
            "status": "empty", 
            "message": f"No reviews found in CSV for {target_date}",
            "processed_count": 0
        }
    
    processed_data = agent_system.analyze_and_save(raw_reviews, target_date)
    
    return {
        "status": "success", 
        "simulated_date": target_date, 
        "reviews_processed_in_batch": len(processed_data)
    }

@app.get("/trends")
def get_trends():
    """Get the pivot table for the frontend"""
    pivot = agent_system.get_trend_matrix()
    if pivot.empty:
        return []
    return pivot.reset_index().to_dict(orient='records')

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """Chat with the agent about the data"""
    response = agent_system.ask_agent(req.message)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)