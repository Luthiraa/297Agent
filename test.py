import requests

# URL for your deployed API endpoint
url = "https://two97agent.onrender.com"

# Define your test cases with required keys: "city", "query", and "pois"
test_cases = [
    {
        "city": "New York",
        "query": "What are some good museums to visit?",
        "pois": "Metropolitan Museum of Art, Museum of Modern Art, American Museum of Natural History"
    },
    {
        "city": "San Francisco",
        "query": "Where can I find the best views?",
        "pois": "Golden Gate Bridge, Twin Peaks, Coit Tower"
    }
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
