import pandas as pd
import numpy as np
from together import Together
from tqdm import tqdm
import os
import getpass

print("Starting script...")

# Change working directory to the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"Changed working directory to: {script_dir}")

def get_api_key():
    """Prompt user for Together AI API key"""
    print("Requesting API key...")
    api_key = getpass.getpass("Please enter your Together AI API key: ")
    return api_key

def create_embeddings(text, client):
    """Create embeddings for a given text using Together AI's API"""
    try:
        response = client.embeddings.create(
            model="togethercomputer/m2-bert-80M-2k-retrieval",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error creating embedding: {e}")
        return None

def main():
    print("Starting main function...")
    
    try:
        # Get API key from user
        api_key = get_api_key()
        print("API key received")
        
        # Initialize Together AI client with the provided key
        print("Initializing Together AI client...")
        client = Together(api_key=api_key)
        
        # Read the scam alerts CSV file
        print("Reading CSV file...")
        df = pd.read_csv('scam_alerts.csv')
        print(f"Found {len(df)} rows in CSV")
        
        # Initialize a list to store embeddings
        embeddings = []
        
        # Create embeddings for each content
        print("Creating embeddings...")
        for content in tqdm(df['Content']):
            embedding = create_embeddings(content, client)
            if embedding:
                embeddings.append(embedding)
            else:
                embeddings.append([0] * 768)  # output the embedd 768 dimensions
        
        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings)
        
        # Create a new dataframe with Intel_ID and embeddings
        embeddings_df = pd.DataFrame({
            'Intel_ID': df['Intel_ID'],
            'embedding': embeddings_array.tolist()
        })
        
        # Save to CSV
        embeddings_df.to_csv('scam_alerts_embeddings.csv', index=False)
        print("Embeddings saved to scam_alerts_embeddings.csv")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    print("Script is running...")
    main() 