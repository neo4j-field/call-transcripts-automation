This is a [Python](https://www.python.org/) project for constructing a business-process aware knowledge graph for customer service automation and acceleration.

## Getting Started

First, set up a python virtual environment:

```bash
python3 -m venv venv
```

Once that's done, activate the venv and install the dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Set up a `.env` file with the following entries:

```
NEO4J_URI=...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...
NEO4J_DATABASE=...

AURA=true/false
AURA_API_CLIENT_ID=...
AURA_API_CLIENT_SECRET=...

# OPENAI_API_KEY= <use Azure OpenAI>
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
```

## Run

```bash
python ingest.py
python process.py
```
