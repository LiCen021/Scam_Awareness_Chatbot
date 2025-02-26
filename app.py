from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from together import Together
from sklearn.metrics.pairwise import cosine_similarity
import os
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Dict
import re
import json

# Check for Together AI API key
if 'TOGETHER_API_KEY' not in os.environ:
    raise EnvironmentError(
        "Together AI API key not found! Please set your API key:\n"
        "export TOGETHER_API_KEY='your_api_key_here'"
    )

app = Flask(__name__)

class RoutingAgent:
    def __init__(self, chatbot):
        self.chatbot = chatbot
        self.routes = {
            "company_check": "Route for verifying specific company mentions using RAG",
            "situation_analysis": "Route for analyzing user's situation with expert knowledge"
        }
        
    def detect_company_name_llm(self, text):
        """
        Use LLM to detect if a company name is mentioned in the text
        Returns: 1 if company name found, 0 if not
        """
        messages = [
            {"role": "system", "content": """You are a company name detection expert. 
            Analyze the text and respond ONLY with a JSON object in this exact format:
            {
                "has_company": 1 or 0
            }
            1 means a company name is mentioned, 0 means no company name is mentioned.
            Do not include any other text or explanation. if just word 'company' is mentioned without a proper company name, it should return 0"""},
            {"role": "user", "content": text}
        ]
        
        try:
            response = self.chatbot.client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=messages,
                max_tokens=100,
                temperature=0.1,
                response_format={"type": "json_object"},
                stop=["<|eot_id|>", "<|eom_id|>"]
            )
            
            content = response.choices[0].message.content.strip()
            if not content:
                return 0
                
            try:
                result = json.loads(content)
                return result.get("has_company", 0)
            except json.JSONDecodeError:
                return 0
                
        except Exception as e:
            print(f"LLM detection error: {str(e)}")
            return 0
            
    def route_query(self, query):
        """Route the query to appropriate handler based on content"""
        print("\n=== Routing Agent Analysis ===")
        print(f"Query: {query}")
        
        # Use LLM to detect if query mentions a company
        llm_result = self.detect_company_name_llm(query)
        print(f"LLM Detection Result: {llm_result}")
        
        # Route to appropriate handler based on detection
        if llm_result == 1:
            print("\n✓ Routing to company handler")
            return self._handle_company_query(query)
        else:
            print("\n✓ Routing to situation analysis")
            return self._handle_situation_query(query)
    
    def _handle_company_query(self, query):
        """Handle queries about specific companies"""
        # Use RAG to find relevant company information
        relevant_info = self.chatbot.find_relevant_content(query)
        
        # Format context from relevant information
        context_items = []
        for _, row in relevant_info.iterrows():
            source_url = row.get('Source', 'Source not available')
            context_items.append(
                f"Source: {source_url}\n"
                f"Title: {row.get('Title', '')}\n"
                f"Content: {row.get('Content', '')}"
            )
        context = "\n\n".join(context_items)
        
        # Company-specific prompt
        messages = [
            self.chatbot.system_message,
            {"role": "user", "content": f"""Please analyze this query about the company: {query}

            Focus on:

            1. Whether this company has been involved in known scams
            2. Similar company names used in scams
            3. Source url of the information

            IMPORTANT: The following context information comes from the bot's database, NOT from the user. 
            Do not say "based on the information you provided" or similar phrases. Instead, refer to it as 
            "based on my database" or "according to my records".

            Context:
            {context}"""}
        ]
        
        # Generate response using the chatbot's LLM
        try:
            response = self.chatbot.client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.5,
                stream=True
            )
            return response
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error while processing your query."
    
    def _handle_situation_query(self, query):
        """Handle general situation analysis"""
        # Use RAG for general scam patterns
        relevant_info = self.chatbot.find_relevant_content(query)
        
        # Format context from relevant information
        context_items = []
        for _, row in relevant_info.iterrows():
            source_url = row.get('Source', 'Source not available')
            context_items.append(
                f"Source: {source_url}\n"
                f"Title: {row.get('Title', '')}\n"
                f"Content: {row.get('Content', '')}"
            )
        context = "\n\n".join(context_items)
        
        # General scam pattern prompt
        messages = [
            self.chatbot.system_message,
            {"role": "user", "content": f"""Please analyze this situation: {query}

            Focus on:
            1. Identifying potential scam patterns
            2. Specific red flags in the situation
            3. Recommended safety steps
            4. Similar known scam cases

            IMPORTANT: The following context information comes from the bot's database, NOT from the user. 
            Do not say "based on the information you provided" or similar phrases. Instead, refer to it as 
            "based on my database" or "according to my records".

            Context:
            {context}"""}
        ]
        
        # Generate response using the chatbot's LLM
        try:
            response = self.chatbot.client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.5,
                stream=True
            )
            return response
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I apologize, but I encountered an error while processing your query."

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
        # Initialize the routing agent
        self.router = RoutingAgent(self)

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
        """Generate response using the routing agent"""
        return self.router.route_query(query)

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
        
        # Check if response is a string (error message)
        if isinstance(response, str):
            return jsonify({'response': response})
            
        # Collect the response text
        response_text = ''
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    if chunk.choices[0].delta.content is not None:
                        response_text += chunk.choices[0].delta.content
        
        # If we didn't get any text, return an error
        if not response_text:
            print("Warning: Empty response text received from LLM")
            return jsonify({'response': 'I apologize, but I was unable to generate a response. Please try again.'})
            
        return jsonify({'response': response_text})
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        return jsonify({'response': f'Error: {str(e)}'}), 500

@app.route('/reset', methods=['POST'])
def reset():
    try:
        # No need to reinitialize the chatbot since we're using fresh context for each query
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/save-chat', methods=['POST'])
def save_chat():
    try:
        data = request.json
        chat_history = data.get('chatHistory', [])
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{timestamp}.txt"
        
        # Create 'chat_histories' directory if it doesn't exist
        if not os.path.exists('chat_histories'):
            os.makedirs('chat_histories')
        
        # Write chat history to file
        filepath = os.path.join('chat_histories', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            for message in chat_history:
                role = "User" if message['isUser'] else "Bot"
                f.write(f"{role}: {message['text']}\n\n")
        
        # Return the file for download
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-prompts', methods=['GET'])
def get_prompts():
    prompts = [
        "I heard this good investment opportunity from a company, can you help me to check if any institution has warned about it?",
        "I'm not sure if this is a scam, can you help me check if the pattern look like a scam?"
    ]
    return jsonify({'prompts': prompts})

@app.route('/get-boilerplate-response', methods=['POST'])
def get_boilerplate_response():
    data = request.json
    prompt = data.get('prompt', '')
    
    # Define boilerplate responses for specific prompts
    boilerplate_responses = {
        "I heard this good investment opportunity from a company, can you help me to check if any institution has warned about it?": 
            "Sure, would you be able to tell the name of the company?"
    }
    
    # Check if the prompt has a boilerplate response
    if prompt in boilerplate_responses:
        return jsonify({'response': boilerplate_responses[prompt], 'is_boilerplate': True})
    else:
        return jsonify({'is_boilerplate': False})

if __name__ == '__main__':
    app.run(debug=True, port=5000) 