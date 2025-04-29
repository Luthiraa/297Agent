# Importing necessary libraries
import os
from flask import Flask, request, jsonify
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import BaseTool
from pydantic import Field
from typing import Dict, Any
import re

# Load secret key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Create LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=30, # 30 second timeout
    max_retries=2,
    api_key=OPENAI_API_KEY,
)

validator_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=30, # 30 second timeout
    max_retries=2,
    api_key=OPENAI_API_KEY,
)

# Tool Definition
class POIFeatureTool(BaseTool):
    name: str = "poi_feature_tool"
    description: str = "Get list of POIs/Features for a city. Input format: 'city;query_type' where query_type is 'pois'."
    city_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def _run(self, input_str: str) -> str:
        try:
            city, query_type = map(str.strip, input_str.split(";", 1))
            print(city, query_type)
            print(self.city_data)
            if city not in self.city_data or query_type not in self.city_data[city]:
                return "No data available."
            return ", ".join(self.city_data[city][query_type])
        except Exception:
            return "Invalid input format. Use 'city,query_type'."

    def _arun(self, query: str):
        raise NotImplementedError("Async not implemented.")

# Helper to process response
def process_response(response):
    if hasattr(response, "content"):
        response = response.content # Check if content is present

    # Extract content inside <response>...</response>
    match = re.search(r"<response>(.*?)</response>", response, re.DOTALL)
    if not match:
        # If <response> block is missing
        return {
            "response": response.strip(),
            "highlight": [],
            "waymark": []
        }
    
    full_content = match.group(1).strip()

    # Separate sections
    bot_text_match = re.search(r"Bot:(.*?)(Highlight:|Waymark:|$)", full_content, re.DOTALL)
    highlight_match = re.search(r"Highlight:(.*?)(Waymark:|$)", full_content, re.DOTALL)
    waymark_match = re.search(r"Waymark:(.*)", full_content, re.DOTALL)

    bot_text = bot_text_match.group(1).strip() if bot_text_match else ""
    highlight_text = highlight_match.group(1).strip() if highlight_match else ""
    waymark_text = waymark_match.group(1).strip() if waymark_match else ""

    # Process highlights
    highlights = []
    if highlight_text and highlight_text.lower() != "none":
        highlights = [h.strip() for h in highlight_text.split(',') if h.strip()]
    
    if len(highlights) == 0:
        highlights.append("None")

    # Process waymarks
    waymarks = []
    if waymark_text and waymark_text.lower() != "none":
        waymarks = [w.strip() for w in waymark_text.split(',') if w.strip()]
    
    if len(waymarks) == 0:
        waymarks.append("None")

    return {
        "response": bot_text,
        "highlight": highlights,
        "waymark": waymarks
    }

# ----- FLASK APPLICATION -----
# Flask App
app = Flask(__name__)

# Flask route
# Flask App
app = Flask(__name__)

# Flask route
@app.route('/', methods=['POST'])
def chat():
    try:
        # Get the 
        data = request.json
        city = data.get("city")
        query = data.get("query")
        pois = data.get("pois")
        features = data.get("features", [])
        
        # Check for any empty fields
        if not city or not query or pois is None:
            return jsonify({"error": "Missing city, query, or POIs"}), 400

        # Create the POI tool dynamically for this request
        tool = POIFeatureTool(city_data={city: {"pois": pois}})
        tools = [
            Tool(
                name=tool.name,
                func=tool._run,
                description=tool.description,
            )
        ]

        # System Prompt
        system_message = SystemMessage(
            content=f"""You are a travel assistant for {city} for a full stack mapping application. 
        You can use the tool 'poi_feature_tool' to access POIs/Features of the city.
        You are supposed to answer the user's query based ONLY on available POIs.
        Legal command to access list of all POIs: "{city};pois" where city is {city}. You can only access POIs of {city}.
        Legal command to access list of all POIs: "{city};features" where city is {city}. You can only access POIs of {city}.
        Get list of all POIs in {city} using the tool (i.e. only once for POIs and once for Features). 
        Do NOT repeatedly use it multiple times.
        Do NOT call the tool again once you have received both the lists.
        Do NOT call the tool if you already have sufficient information.

        For internal use, the output will be in the following format:

        **Output MUST follow this format (inside <response>...</response>):**

        <response>
        Bot: <your helpful text>
        Highlight: <comma-separated POIs>
        Waymark: <comma-separated POIs in visit order> (only if needed)
        </response>

        You are required to do the following for the user:
        - Give specific information about the city to the user (including POIs and Features)
        - Give more information about POIs or Features if needed by the user
        - Be able to perform wayfinding if needed for the user
        - Be able to plan the user's day out as per the user's needs
        - Control the full stack application through internal commands "Highlight" and "WayMark"
        - "Bot" output is the response for the user
        - the internal commands "Highlight" and "WayMark" should only contain comma seperated list of POIs
        - Use "Highlight" if you want the full stack application to highlight any specific list of POIs only. This can be when the user is inquiring
        about them (either infer or explicit) or even when you're giving information to the user and you want to highlight POIs in the application
        for improved software user experience. Highlighting is encouraged when talking about POIs.
        - Use "WayMark" to do wayfinding, list of POIsto be visited in the required order. You should be using this only when the user wants
        you to plan their day out in a specific way or even want simple wayfinding (find me way between A and B). Think about it this way:
        you are telling the full stack application if the user needs wayfinding and if so, in what order of the POIs/Features to visit. Only use this command
        if you think the user asks for it explicitly (find me way between A and B) or wants you to plan the day out.
        - To handle cases where user explicity asks you to find way from A to B and not like plan your day out or take a specific theme route, 
        then just say "Route shown on Map" and in 'WayMark" list A and B directly.
        - To handle cases where user asks you to plan your day out in a specifc way, do it in a way by listing out the POIs in WayMark and then
        give response to the user about your choices and what they can do.
        - Remember, if needed, you can also highlight POIs while doing Waymark (Wayfinding) if you think the application should highlight POIs for
        better user experience with the application.
        - Highlight whenever needed to- example when describing certain POIs or even day planning 
        - Use WayMark to list POIs to visit in order for day planning or just showing a route (this is must when route planning or day planning
        or else system will fail).
        """
        )


        # Initialize the agent
        agent_executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            agent_kwargs={"system_message": system_message},
        )

        # Let the agent handle the user query
        response = agent_executor.invoke({"input": query})

        validation_prompt = f"""Your task is to fix the output of this system according to the following rules (which are supposed to be followed by the System)
        You are a travel assistant for {city} for a full stack mapping application. 
        You can use the tool 'poi_feature_tool' to access POIs/Features of the city.
        You are supposed to answer the user's query based ONLY on available POIs.
        Legal command to access list of all POIs: "{city};pois" where city is {city}. You can only access POIs of {city}.
        Legal command to access list of all POIs: "{city};features" where city is {city}. You can only access POIs of {city}.
        Get list of all POIs in {city} using the tool (i.e. only once for POIs and once for Features). 
        Do NOT repeatedly use it multiple times.
        Do NOT call the tool again once you have received both the lists.
        Do NOT call the tool if you already have sufficient information.

        For internal use, the output will be in the following format:

        **Output MUST follow this format (inside <response>...</response>):**

        <response>
        Bot: <your helpful text>
        Highlight: <comma-separated POIs>
        Waymark: <comma-separated POIs in visit order> (only if needed)
        </response>

        You are required to do the following for the user:
        - Give specific information about the city to the user (including POIs and Features)
        - Give more information about POIs or Features if needed by the user
        - Be able to perform wayfinding if needed for the user
        - Be able to plan the user's day out as per the user's needs
        - Control the full stack application through internal commands "Highlight" and "WayMark"
        - "Bot" output is the response for the user
        - the internal commands "Highlight" and "WayMark" should only contain comma seperated list of POIs
        - Use "Highlight" if you want the full stack application to highlight any specific list of POIs only. This can be when the user is inquiring
        about them (either infer or explicit) or even when you're giving information to the user and you want to highlight POIs in the application
        for improved software user experience. Highlighting is encouraged when talking about POIs.
        - Use "WayMark" to do wayfinding, list of POIsto be visited in the required order. You should be using this only when the user wants
        you to plan their day out in a specific way or even want simple wayfinding (find me way between A and B). Think about it this way:
        you are telling the full stack application if the user needs wayfinding and if so, in what order of the POIs/Features to visit. Only use this command
        if you think the user asks for it explicitly (find me way between A and B) or wants you to plan the day out.
        - To handle cases where user explicity asks you to find way from A to B and not like plan your day out or take a specific theme route, 
        then just say "Route shown on Map" and in 'WayMark" list A and B directly.
        - To handle cases where user asks you to plan your day out in a specifc way, do it in a way by listing out the POIs in WayMark and then
        give response to the user about your choices and what they can do.
        - Remember, if needed, you can also highlight POIs while doing Waymark (Wayfinding) if you think the application should highlight POIs for
        better user experience with the application.
        - Highlight whenever needed to- example when describing certain POIs or even day planning 
        - Use WayMark to list POIs to visit in order for day planning or just showing a route (this is must when route planning or day planning
        or else system will fail).

        User Query = {query}
        Response of System = {response['output']}

        If the output is fine then return as it is or regenerate and return
        While highlighting and waymarking at same time, make sure that whatever is highlighted is part of waymark also, meaning dont suggest
        too many options for a specific user request but try to be a bit specific. Also don't waymark unless the user wants to plan day out or
        wants you to route from A to B.
        """
        
        fixed_response = validator_llm.invoke(validation_prompt)
        return process_response(fixed_response.content)

    except Exception as e:
        app.logger.error("Error in chat request", exc_info=e)
        return jsonify({"error": str(e)}), 500

# Home route
@app.route('/home', methods=['GET'])
def home():
    return "Welcome to the travel assistant API. Use a POST request with JSON payload."

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)