import requests

# Define the URL of the Flask app
url = "https://two97agent.onrender.com/chat"

# Define test cases with POIs and features
test_cases = [
    {
        "city": "Paris",
        "query": "I love food so where should I go?",
        "pois": {"Eiffel Tower": "tourist_spot", "Louvre Museum":"museum", "Notre-Dame Cathedral":"tourist_spot"},
    }
    # {
    #     "city": "New York",
    #     "query": "What are some famous landmarks and parks?",
    #     "pois": ["Statue of Liberty", "Central Park", "Times Square"],
    #     "features": ["Hudson River", "Brooklyn Bridge", "Prospect Park"]
    # },
    # {
    #     "city": "Tokyo",
    #     "query": "What are some popular tourist spots and natural features?",
    #     "pois": ["Shibuya Crossing", "Tokyo Tower", "Meiji Shrine"],
    #     "features": ["Sumida River", "Ueno Park", "Mount Takao"]
    # }
]

# Test each case
for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest Case {i}: {test_case['city']}")
    response = requests.post(url, json=test_case)
    if response.status_code == 200:
        print("Response:", response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)