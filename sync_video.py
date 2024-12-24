import requests
import os
import time
from dotenv import load_dotenv

def create_synced_video(video_url, audio_url, output_path="output.mp4"):
    """
    Create a synced video using the Sync.so API
    
    Args:
        video_url (str): Public URL to the video file
        audio_url (str): Public URL to the audio file
        output_path (str): Where to save the output video
    """
    # Load environment variables
    load_dotenv()
    
    # Get API key from .env
    api_key = os.getenv('SYNC_API_KEY')
    
    url = "https://api.sync.so/v2/generate"
    
    payload = {
        "model": "lipsync-1.7.1",
        "input": [
            {
                "type": "video",
                "url": video_url
            },
            {
                "type": "audio",
                "url": audio_url
            }
        ],
        "options": {
            "pads": [0, 5, 0, 0],
            "output_format": "mp4",
            "sync_mode": "loop",
            "active_speaker": False,
            "output_resolution": [744, 692],
            "fps": 24
        }
    }
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        print("Submitting generation request...")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        request_id = result.get('id')
        print(f"\nRequest submitted successfully! Job ID: {request_id}")
        
        # Poll for status
        status_url = f"https://api.sync.so/v2/generate/{request_id}"
        while True:
            print("\nChecking status...")
            result_response = requests.get(status_url, headers=headers)
            if result_response.status_code == 200:
                result_data = result_response.json()
                status = result_data.get("status")
                print(f"Current status: {status}")
                
                if status == "COMPLETED":
                    output_url = result_data.get("outputUrl")
                    print(f"Processing completed! Downloading from: {output_url}")
                    
                    # Download the completed video
                    download_response = requests.get(output_url)
                    download_response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(download_response.content)
                    print(f"Video saved to: {output_path}")
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
        
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response details: {e.response.text}")

if __name__ == "__main__":
    # Use the raw GitHub URL for the video
    video_url = "https://raw.githubusercontent.com/ndai-tee/clips/main/elon.mov"
    audio_url = "https://cdn-2.fakeyou.com/media/2/f/d/q/z/2fdqzzxjv2vpy4pxsmqcx3p8dfy9cvx0/fakeyou_2fdqzzxjv2vpy4pxsmqcx3p8dfy9cvx0.wav"
    
    create_synced_video(video_url, audio_url) 