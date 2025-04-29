# import requests

# # Define the URL of the Flask app
# url = "https://two97agent.onrender.com"  # Update if needed

# # Define test cases
# test_cases = [
#     {
#         "title": "Highlight Only - Paris",
#         "input": {
#             "city": "Paris",
#             "query": "What are some famous landmarks to visit?",
#             "pois": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral"],
#             "features": ["Seine River", "Montmartre"]
#         }
#     },
#     {
#         "title": "Day Plan - Toronto",
#         "input": {
#             "city": "Toronto",
#             "query": "I want to start with some coffee, then visit a historic site, and end with Japanese dinner.",
#             "pois": ["Distillery District", "Royal Ontario Museum", "CN Tower", "Kensington Market", "Hakata Ikkousha Ramen"],
#             "features": ["Lake Ontario", "Historic Sites"]
#         }
#     },
#     {
#         "title": "Wayfinding Direct - New York",
#         "input": {
#             "city": "New York",
#             "query": "Find me the way from Statue of Liberty to Times Square.",
#             "pois": ["Statue of Liberty", "Central Park", "Times Square"],
#             "features": ["Hudson River", "Brooklyn Bridge", "Prospect Park"]
#         }
#     },
#     {
#         "title": "Sceneic Route - Toronto",
#         "input": {
#             "city": "Toronto",
#             "query": "Plan my route from Hakata Ramen to Hilton Toronto through important tourist locations in downtown.",
#             "pois": ["Distillery District", "Royal Ontario Museum", "CN Tower", "Kensington Market", "Hakata Ikkousha Ramen", "Hilton Toronto"],
#             "features": ["Lake Ontario", "Grange Park"]
#         }
#     }
# ]

# # Send each test case
# for i, case in enumerate(test_cases, 1):
#     print(f"\nTest Case {i}: {case['title']}")
#     try:
#         response = requests.post(url, json=case["input"])
#         if response.status_code == 200:
#             data = response.json()
#             print("Bot Response:", data.get("response", "No response"))
#             print("Highlights:", data.get("highlight", []))
#             print("Waymark:", data.get("waymark", []))

#             # Small smart checks (optional, not raising error just printing)
#             if case['title'].lower().startswith("highlight only"):
#                 if data.get("waymark"):
#                     print("⚠️ Unexpected waymark found!")
#             if case['title'].lower().startswith("wayfinding direct"):
#                 waymark = data.get("waymark", [])
#                 if not waymark or len(waymark) < 2:
#                     print("⚠️ Wayfinding missing or incomplete!")
#                 else:
#                     if "Statue of Liberty" not in waymark[0] or "Times Square" not in waymark[-1]:
#                         print("⚠️ Start or End point not correctly in waymark!")
#             if case['title'].lower().startswith("scenic route"):
#                 waymark = " ".join(data.get("waymark", [])).lower()
#                 if not any(word in waymark for word in ["park", "river", "mount"]):
#                     print("⚠️ Scenic waymark not detected!")
#         else:
#             print(f"Error {response.status_code}: {response.text}")
#     except Exception as e:
#         print(f"Exception during request: {str(e)}")



import requests
import json

# Define the URL of the Flask app
url = "https://two97agent.onrender.com"  # Update if needed

# Load input from toronto.json
with open('toronto.json', 'r', encoding='utf-8') as f:
    toronto_data = json.load(f)

# Send test case
print("\nTest Case: Toronto JSON Input")
try:
    response = requests.post(url, json=toronto_data)
    if response.status_code == 200:
        data = response.json()
        print("Bot Response:", data.get("response", "No response"))
        print("Highlights:", data.get("highlight", []))
        print("Waymark:", data.get("waymark", []))

        # Small smart checks
        waymark = data.get("waymark", [])
        if not waymark:
            print(":warning: No waymark generated.")
        if not data.get("highlight") and not waymark:
            print(":warning: No highlights or waymarks found!")
    else:
        print(f"Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"Exception during request: {str(e)}")