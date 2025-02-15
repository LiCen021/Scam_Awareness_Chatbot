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
        # Load additional scam knowledge
        try:
            with open('Data/Extra_Scam_Knowledge/extra_scam_related_knowledge.txt', 'r') as f:
                self.extra_knowledge = f.read()
        except Exception as e:
            print(f"Warning: Could not load extra scam knowledge: {str(e)}")
            self.extra_knowledge = ""
        # Initialize system message
        self.system_message = {
            "role": "system", 
            "content": """You are a helpful assistant specializing in identifying and explaining scams. 
            Your approach should be conversational and focused on gathering relevant information first.
            
            Guidelines for your responses:
            1. If the user hasn't provided enough context, ask clarifying questions first
            2. Only share information that's relevant to what you know about their specific situation
            3. Keep responses concise and conversational
            4. Don't list general red flags unless they match specific details shared by the user
            5. Avoid overwhelming users with too much information at once
            
            Example approach:
            User: "I heard about an investment from X company"
            You: "I'd be happy to help you evaluate this opportunity. Could you tell me more about how they contacted you and what they're offering?"
            
            Citation instructions:
            1. Only cite sources when providing specific information
            2. Keep citations minimal and relevant to the specific discussion"""
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
            if not isinstance(source_url, str):
                source_url = "Source URL not available"
            
            context_items.append(
                f"Source URL: {source_url}\nTitle: {row['Title']}\nContent: {row['Content']}"
            )
        context = "\n\n".join(context_items)
        
        # Add extra scam knowledge to the context
        if self.extra_knowledge:
            context += "\n\nAdditional Expert Knowledge:\n" + self.extra_knowledge
        
        # Prepare the prompt with more focused instructions
        messages = [
            self.system_message,
            {"role": "user", "content": f"""Please provide a focused answer to this question: {query}

            Key requirements:
            1. Address the specific question directly
            2. Only use relevant information from the context
            3. Keep the response concise and clear
            4. If it's a scam, explain the specific red flags that apply to this case
            5. Provide clear next steps if needed

            Context:
            {context}"""}
        ]
        
        # Generate response using LLaMA model
        response = self.client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=messages,
            max_tokens=600,
            temperature=0.3,
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