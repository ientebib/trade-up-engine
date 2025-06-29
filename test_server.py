#!/usr/bin/env python3
"""Test if basic server works"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Server is working"}

@app.get("/test")
def test():
    return JSONResponse({"test": "success"})

if __name__ == "__main__":
    print("Starting test server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)