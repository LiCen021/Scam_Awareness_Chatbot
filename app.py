from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from together import Together
from sklearn.metrics.pairwise import cosine_similarity
import os

# Check for Together AI API key
if 'TOGETHER_API_KEY' not in os.environ:
    raise EnvironmentError(
        "Together AI API key not found! Please set your API key:\n"
        "export TOGETHER_API_KEY='your_api_key_here'"
    )

app = Flask(__name__)

class ScamChatbot:
    def __init__(self):
        self.client = Together()
        # Load the original scam alerts data
        self.scam_data = pd.read_csv('Data/scam_alerts.csv')
        # Load the embeddings
        self.embeddings_data = pd.read_csv('Data/scam_alerts_embeddings.csv')
        # Convert string representation of embeddings back to numpy arrays
        self.embeddings_data['embedding'] = self.embeddings_data['embedding'].apply(eval)
        self.embeddings_matrix = np.array(self.embeddings_data['embedding'].tolist())
        # Initialize system message
        self.system_message = {
            "role": "system", 
            "content": """You are a helpful assistant specializing in identifying and explaining scams. 
            Use the provided context to answer questions about scams and fraud. Be informative and precise in your responses.
            Always maintain a professional tone and provide practical advice when relevant.
            
            Important instructions for citations:
            1. Use the complete source URL for citations
            2. Only cite a specific URL once, even if multiple pieces of information come from the same source
            3. Group related information from the same source together in a paragraph
            4. Place the citation at the end of the paragraph in markdown format: [Source: complete_url]
            5. If information comes from multiple sources, create separate paragraphs with their respective citations"""
        }

    def get_embedding(self, text):
        """Create embedding for the input text"""
        response = self.client.embeddings.create(
            model="togethercomputer/m2-bert-80M-2k-retrieval",
            input=text
        )
        return response.data[0].embedding

    def find_relevant_content(self, query, top_k=5):
        """Find the most relevant content based on the query"""
        # Get query embedding
        query_embedding = self.get_embedding(query)
        
        # Calculate cosine similarity
        similarities = cosine_similarity([query_embedding], self.embeddings_matrix)[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Get corresponding Intel_IDs
        relevant_intel_ids = self.embeddings_data.iloc[top_indices]['Intel_ID'].tolist()
        
        # Get full content for these Intel_IDs
        relevant_contents = self.scam_data[self.scam_data['Intel_ID'].isin(relevant_intel_ids)]
        
        return relevant_contents

    def generate_response(self, query):
        """Generate response using RAG"""
        # Find relevant content
        relevant_info = self.find_relevant_content(query)
        
        # Prepare context from relevant information
        context_items = []
        for _, row in relevant_info.iterrows():
            source_url = row['Source']
            if not isinstance(source_url, str):  # Handle cases where Source might be NaN
                source_url = "Source URL not available"
            
            context_items.append(
                f"Source URL: {source_url}\nTitle: {row['Title']}\nContent: {row['Content']}"
            )
        context = "\n\n".join(context_items)
        
        # Prepare the prompt
        messages = [
            self.system_message,
            {"role": "user", "content": f"""Based on the following context about scams, please answer this question: {query}
            
            Remember to:
            1. Use complete source URLs in your citations
            2. Group related information from the same source in one paragraph
            3. Cite each source only once at the end of its respective paragraph
            4. Use markdown format for citations: [Source: complete_url]

            Context:
            {context}"""}
        ]
        
        # Generate response using LLaMA model
        response = self.client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"],
            stream=True
        )
        
        return response

# Initialize the chatbot
try:
    chatbot = ScamChatbot()
    print("Chatbot initialized successfully!")
except Exception as e:
    print(f"Error initializing chatbot: {str(e)}")
    raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    try:
        # Get response from the chatbot
        response = chatbot.generate_response(user_message)
        
        # Collect the response text
        response_text = ''
        for token in response:
            if hasattr(token, 'choices'):
                response_text += token.choices[0].delta.content
        
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/reset', methods=['POST'])
def reset():
    try:
        # No need to reinitialize the chatbot since we're using fresh context for each query
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 