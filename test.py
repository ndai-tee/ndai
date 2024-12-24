import time
import requests
import os

# Request generation
url = "https://api.sync.so/v2/generate"
headers = {
    "x-api-key": os.getenv('SYNC_API_KEY'),
    "Content-Type": "application/json"
}
payload = {
    "model": "lipsync-1.7.1",
    "input": [
        {"type": "audio", "url": "https://cdn-2.fakeyou.com/media/2/f/d/q/z/2fdqzzxjv2vpy4pxsmqcx3p8dfy9cvx0/fakeyou_2fdqzzxjv2vpy4pxsmqcx3p8dfy9cvx0.wav"},
        {"type": "video", "url": "https://github.com/ndai-tee/clips/blob/main/elon.mov"}
    ]
}

# Send the initial request
response = requests.post(url, json=payload, headers=headers)
if response.status_code == 200:
    request_id = response.json().get("id")
    print(f"Request submitted successfully. ID: {request_id}")
else:
    print("Error submitting request:", response.text)
    exit()

# Poll for status
status_url = f"https://api.sync.so/v2/generate/{request_id}"
while True:
    result_response = requests.get(status_url, headers=headers)
    if result_response.status_code == 200:
        result_data = result_response.json()
        status = result_data.get("status")
        print(f"Current status: {status}")
        
        if status == "COMPLETED":
            output_url = result_data.get("outputUrl")
            print(f"Processing completed. Output URL: {output_url}")
            break
        elif status == "FAILED":
            error = result_data.get("error")
            print(f"Processing failed. Error: {error}")
            break
    else:
        print("Error checking status:", result_response.text)
        break
    
    # Wait before polling again
    time.sleep(5)
