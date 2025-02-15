# Scam Alert Chatbot

A RAG-based chatbot that uses Together AI's LLaMA model to provide information about scams based on a database of scam alerts.

## Project Structure

```
.
├── Data/
│   ├── Extra_Scam_Knowledge/  # Additional scam information and resources
│   ├── bank_scam_alert_scrapper.py  # Script to scrape scam alerts
│   ├── embedding.py           # Script to generate embeddings
│   ├── scam_alerts.csv       # Original scam alerts data
│   └── scam_alerts_embeddings.csv  # Generated embeddings
├── templates/                 # HTML templates for the web interface
│   └── index.html            # Chat interface template
├── app.py                    # Main application (Flask + RAG implementation)
├── Procfile                  # Heroku deployment configuration
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your Together AI API key:

```bash
export TOGETHER_API_KEY='your_api_key_here'
```

## Usage

1. First, generate embeddings for the scam alerts database:

```bash
python Data/embedding.py
```

2. Start the web application:

```bash
python app.py
```

Then open your browser and navigate to: http://localhost:5000

3. Interact with the chatbot through the web interface.

## Heroku Deployment

1. Make sure you have the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed.

2. Login to Heroku:

```bash
heroku login
```

3. Create a new Heroku app:

```bash
heroku create your-app-name
```

4. Set your Together AI API key as a config var:

```bash
heroku config:set TOGETHER_API_KEY='your_api_key_here'
```

5. Deploy to Heroku:

```bash
git push heroku main
```

The application will be available at: https://your-app-name.herokuapp.com

## Features

- Uses Together AI's m2-bert-80M-2k-retrieval model for embeddings
- Implements Retrieval-Augmented Generation (RAG) using LLaMA 3.3 70B
- Finds the 5 most relevant scam alerts for each query
- Provides context-aware responses based on the scam database
- Modern web interface with real-time chat functionality

## Note

Make sure you have a valid Together AI API key with access to:

- togethercomputer/m2-bert-80M-2k-retrieval (for embeddings)
- meta-llama/Llama-3.3-70B-Instruct-Turbo (for text generation)
