import os
import time
import re
import openai
from openai.error import RateLimitError, APIError

from flask import Flask, request, jsonify

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import BaseTool

from pydantic import Field
from typing import Dict, Any

# --------------------
# Helpers
# --------------------
def safe_llm_call(fn, *args, **kwargs):
    """Call an LLM function with exponential backoff on rate limits or API errors."""
    backoff = 1
    for attempt in range(6):
        try:
            return fn(*args, **kwargs)
        except RateLimitError:
            time.sleep(backoff)
            backoff *= 2
        except APIError:
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("LLM calls are consistently failing after retries.")

def process_response(response_text: str) -> Dict[str, Any]:
    """Parse the <response>…</response> block into JSON payload."""
    # Extract the <response>…</response>
    m = re.search(r"<response>(.*?)</response>", response_text, re.DOTALL)
    if not m:
        return {"response": response_text.strip(), "highlight": [], "waymark": []}

    content = m.group(1).strip()
    bot_m = re.search(r"Bot:(.*?)(Highlight:|Waymark:|$)", content, re.DOTALL)
    hl_m = re.search(r"Highlight:(.*?)(Waymark:|$)", content, re.DOTALL)
    wm_m = re.search(r"Waymark:(.*)", content, re.DOTALL)

    bot_text = bot_m.group(1).strip() if bot_m else ""
    hl_text = hl_m.group(1).strip() if hl_m else ""
    wm_text = wm_m.group(1).strip() if wm_m else ""

    highlights = [h.strip() for h in hl_text.split(",") if h.strip()] or ["None"]
    waymarks  = [w.strip() for w in wm_text.split(",") if w.strip()] or ["None"]

    return {
        "response": bot_text,
        "highlight": highlights,
        "waymark": waymarks
    }

# --------------------
# POI / Feature Tool
# --------------------
class POIFeatureTool(BaseTool):
    name: str = "poi_feature_tool"
    description: str = "Get list of POIs or Features for a city. Input format: 'city;query_type' where query_type is 'pois' or 'features'."
    city_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def _run(self, input_str: str) -> str:
        try:
            city, query_type = [x.strip() for x in input_str.split(";", 1)]
            if city not in self.city_data or query_type not in self.city_data[city]:
                return "No data available."
            return ", ".join(self.city_data[city][query_type])
        except Exception:
            return "Invalid input format. Use 'CityName;pois' or 'CityName;features'."

    def _arun(self, query: str):
        raise NotImplementedError("Async not implemented.")

# --------------------
# Load API Key & LLMs
# --------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=512,
    timeout=30,
    api_key=OPENAI_API_KEY
)

validator_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=512,
    timeout=30,
    api_key=OPENAI_API_KEY
)

# --------------------
# Flask App
# --------------------
app = Flask(__name__)

@app.route('/', methods=['POST'])
def chat():
    try:
        data     = request.get_json(force=True)
        city     = data.get("city")
        query    = data.get("query")
        pois     = data.get("pois")
        features = data.get("features", [])

        if not city or not query or pois is None:
            return jsonify({"error": "Missing 'city', 'query', or 'pois' field"}), 400

        # Build the POI/Feature tool with both lists
        tool = POIFeatureTool(city_data={ city: {"pois": pois, "features": features} })
        tools = [
            Tool(
                name=tool.name,
                func=tool._run,
                description=tool.description
            )
        ]

        # System prompt
        system_message = SystemMessage(content=f"""
You are a travel assistant for {city}. You may call the tool `poi_feature_tool` exactly once
to fetch POIs ({city};pois) and once for features ({city};features). Do NOT call it more than once.
You MUST wrap your final answer in:

<response>
Bot: <…>
Highlight: <comma-separated POIs>
Waymark: <comma-separated POIs>  (only if route planning is requested)
</response>
""".strip())

        # Initialize agent
        agent_executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=False,
            agent_kwargs={"system_message": system_message}
        )

        # 1) Let agent answer
        agent_resp = safe_llm_call(agent_executor.invoke, {"input": query})

        # 2) Validate / fix format
        validation_prompt = f"""
Fix the following system output so it strictly follows the rules:

User Query: {query}
System Output: {agent_resp['output']}
"""
        # Use predict_messages to get a ChatMessage with .content
        fixed_msg = safe_llm_call(
            validator_llm.predict_messages,
            [HumanMessage(content=validation_prompt)]
        )
        fixed_text = fixed_msg.content

        # 3) Parse and return
        return jsonify(process_response(fixed_text))

    except Exception as e:
        app.logger.error("Error in / chat", exc_info=e)
        return jsonify({"error": str(e)}), 500

@app.route('/home', methods=['GET'])
def home():
    return "Travel Assistant API is running. Send POST / with JSON payload."

if __name__ == '__main__':
    # In production, set WEB_CONCURRENCY=1 or use an async worker class to reduce memory use
    app.run(host='0.0.0.0', port=5000, debug=True)
