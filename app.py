import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from Chatbot import Chatbot

app = FastAPI()

# Create a single instance of Chatbot to reuse across requests
chatbot = Chatbot()

# Mount the static files directory for serving HTML files
app.mount("/static", StaticFiles(directory="static"), name="static")

class QueryRequest(BaseModel):
    query_text: str

class QueryResponse(BaseModel):
    response: str
    sources: list[str]

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    try:
        with open("static/index.html") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html file not found.")

@app.get("/file/{filename:path}")
async def get_file(filename: str):
    if not os.path.isfile(filename):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filename)

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        result = await run_in_threadpool(chatbot.query, request.query_text)

        if "response" not in result or "sources" not in result:
            raise HTTPException(status_code=500, detail="Invalid response from chatbot.")

        valid_sources = [source for source in result["sources"] if isinstance(source, str)]

        return QueryResponse(response=result["response"], sources=valid_sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
