import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

app = Flask(__name__)

# Load secret key from environment variable (from .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=OPENAI_API_KEY,
)

# Define a prompt template for the LLM
prompt_template = PromptTemplate(
    input_variables=["city", "query", "pois"],
    template="""\
You are a travel assistant in a map software for the city of {city}. 
Your task is to guide the user on any queries they may have about {city}. The points of interest and type of poi are provided:
POIs: {pois}
Answer the user's query based on the available POIs and features. Try to explain your choices if needed, providing the user with all the information they would need.
For internal help, output in the following format:
Bot: Your Response to the user.
Highlight: POIs to highlight.
If there is no need to highlight, then say "Highlight: None".
List POIs to highlight without quotes and separated by commas. Only highlight POIs from the provided list.
Now, here's the user query:

User Query: {query}"""
)

# Use the new RunnableSequence syntax instead of LLMChain
llm_chain = prompt_template | llm

def process_response(response):
    marker = "Highlight: "
    index = response.find(marker)
    if index == -1:
        # In case the expected marker was not found, return the whole response and no highlights
        return jsonify({"response": response, "highlight": []})
    response_text = response[:index].strip()
    highlight = response[index+len(marker):].strip()
    highlights = [item.strip() for item in highlight.split(',')]
    return jsonify({"response": response_text, "highlight": highlights})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    city = data.get("city")
    query = data.get("query")
    pois = data.get("pois")
    if not city or not query or not pois:
        return jsonify({"error": "Missing city, query, or POIs"}), 400

    # Using invoke with the new runnable chain
    response = llm_chain.invoke(city=city, query=query, pois=pois)
    print(response)
    return process_response(response)

# Note: Requests to "/" will return a 404 since no route is defined.
if __name__ == '__main__':
    app.run(debug=True)