#!/bin/bash
# Install deps if needed, then start the FastAPI server
# Run from the backend/ directory: bash start.sh

pip install -r requirements.txt --quiet
uvicorn main:app --reload --host 0.0.0.0 --port 8000
