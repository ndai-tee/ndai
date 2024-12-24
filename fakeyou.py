import os
import time
import uuid
import requests
import nltk
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydub import AudioSegment

# Download the punkt tokenizer for sentence splitting
nltk.download('punkt', quiet=True)

class FakeYouAPI:
    def __init__(self):
        self.base_url = "https://api.fakeyou.com"
        self.audio_base_url = "https://cdn-2.fakeyou.com"
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum seconds between API requests
        
    def _wait_for_rate_limit(self):
        """Ensure minimum time between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            print(f"Rate limiting: waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
        
    def get_voice_list(self) -> list:
        """Get list of available voices."""
        self._wait_for_rate_limit()
        response = requests.get(f"{self.base_url}/tts/list")
        if response.status_code == 200:
            data = response.json()
            if not data.get("success"):
                raise Exception("API returned unsuccessful response")
            return data.get("models", [])
        raise Exception(f"Failed to get voice list: {response.status_code}")

    def search_voice(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a voice by name.
        If multiple models exist, returns the most recently updated one.
        """
        voices = self.get_voice_list()
        if not voices:
            return None
            
        query = query.lower()
        matching_voices = [
            voice for voice in voices 
            if query in voice["title"].lower()
        ]
        
        if not matching_voices:
            return None
            
        # Sort by updated_at timestamp in descending order (most recent first)
        matching_voices.sort(
            key=lambda x: x["updated_at"],
            reverse=True
        )
        
        return matching_voices[0]

    def generate_tts(self, model_token: str, text: str) -> Optional[str]:
        """Generate TTS audio and return the path to the WAV file."""
        # Submit TTS request
        inference_payload = {
            "uuid_idempotency_token": str(uuid.uuid4()),
            "tts_model_token": model_token,
            "inference_text": text
        }
        
        print(f"Submitting TTS request for text: '{text}'")
        self._wait_for_rate_limit()
        response = requests.post(
            f"{self.base_url}/tts/inference",
            json=inference_payload
        )

        if response.status_code != 200:
            print(f"TTS request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"Failed to submit TTS request: {response.status_code}")
            
        result = response.json()
        if not result["success"]:
            print(f"TTS request unsuccessful: {result}")
            raise Exception("Failed to submit TTS request")
            
        job_token = result["inference_job_token"]
        print(f"Job token received: {job_token}")
        
        # Poll for completion
        while True:
            print(f"Checking status for job {job_token}...")
            self._wait_for_rate_limit()
            status_response = requests.get(f"{self.base_url}/tts/job/{job_token}")
            if status_response.status_code != 200:
                print(f"Status check failed: {status_response.text}")
                raise Exception(f"Failed to get job status: {status_response.status_code}")
                
            status = status_response.json()
            if not status["success"]:
                print(f"Status check unsuccessful: {status}")
                raise Exception("Failed to get job status")
                
            state = status["state"]["status"]
            print(f"Current state: {state}")
            
            if state == "complete_success":
                audio_path = status["state"]["maybe_public_bucket_wav_audio_path"]
                print(f"Audio path received: {audio_path}")
                return audio_path
            elif state in ["complete_failure", "dead"]:
                print(f"Job failed with state: {state}")
                raise Exception(f"TTS generation failed with status: {state}")
                
            time.sleep(2)  # Increased wait time between status checks

    def download_audio(self, audio_path: str, output_path: str):
        """Download the generated audio file."""
        url = f"{self.audio_base_url}{audio_path}"
        print(f"Downloading audio from: {url}")
        
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        self._wait_for_rate_limit()
        response = requests.get(url, headers=headers)
        print(f"Download response status: {response.status_code}")
        
        if response.status_code == 403:
            print(f"403 Error response content: {response.text}")
            # Try alternative URL format
            alt_url = f"https://fakeyou.com{audio_path}"
            print(f"Trying alternative URL: {alt_url}")
            self._wait_for_rate_limit()
            response = requests.get(alt_url, headers=headers)
            print(f"Alternative download response status: {response.status_code}")
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Audio saved to: {output_path}")
        else:
            print(f"Failed to download. Response: {response.text}")
            raise Exception(f"Failed to download audio: {response.status_code}")

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using NLTK."""
    sentences = nltk.sent_tokenize(text)
    return [s.strip() for s in sentences if s.strip()]

def combine_short_sentences(sentences: List[str], max_words: int = 20) -> List[str]:
    """
    Combine sentences that are shorter than max_words into longer segments.
    """
    if not sentences:
        return []
        
    combined = []
    current = sentences[0]
    current_words = len(current.split())
    
    for sentence in sentences[1:]:
        next_words = len(sentence.split())
        combined_words = current_words + next_words
        
        # If current sentence is already long, or combining would make it too long
        if current_words >= max_words or combined_words >= max_words:
            combined.append(current)
            current = sentence
            current_words = next_words
        else:
            # Combine sentences with a space
            current = f"{current} {sentence}"
            current_words = combined_words
    
    # Add the last segment
    if current:
        combined.append(current)
    
    return combined

def generate_celebrity_voice(celebrity: str, text: str, output_dir: str = "audio_output") -> str:
    """
    Generate TTS audio for a given celebrity and text.
    
    Args:
        celebrity: Name of the celebrity voice to use
        text: Text to convert to speech
        output_dir: Directory to save the audio file
        
    Returns:
        Path to the generated audio file
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for sentence audio files
    temp_dir = os.path.join(output_dir, "temp")
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize API
    api = FakeYouAPI()
    
    # Search for voice
    print(f"\nSearching for voice: {celebrity}")
    voice = api.search_voice(celebrity)
    if not voice:
        raise Exception(f"Could not find voice for celebrity: {celebrity}")
    print(f"Found voice: {voice['title']} (Token: {voice['model_token']})")
    
    # Split text into sentences and combine short ones
    sentences = split_into_sentences(text)
    print(f"\nSplit text into {len(sentences)} initial sentences")
    
    combined_sentences = combine_short_sentences(sentences)
    print(f"Combined into {len(combined_sentences)} segments")
    for i, segment in enumerate(combined_sentences, 1):
        word_count = len(segment.split())
        print(f"Segment {i}: {word_count} words")
    
    # Generate audio for each sentence
    temp_files = []
    try:
        for i, sentence in enumerate(combined_sentences, 1):
            print(f"\nProcessing segment {i}/{len(combined_sentences)}")
            print(f"Text: '{sentence}'")
            
            # Generate TTS
            audio_path = api.generate_tts(voice["model_token"], sentence)
            if not audio_path:
                raise Exception("Failed to generate TTS")
            
            # Download audio
            temp_file = os.path.join(temp_dir, f"sentence_{i}.wav")
            api.download_audio(audio_path, temp_file)
            temp_files.append(temp_file)
        
        # Combine all audio files with pauses
        print("\nCombining audio files...")
        combined = AudioSegment.empty()
        pause = AudioSegment.silent(duration=100)  # 0.1 second pause
        
        for temp_file in temp_files:
            audio = AudioSegment.from_wav(temp_file)
            combined += audio + pause
        
        # Save final audio
        timestamp = int(time.time())
        output_file = os.path.join(output_dir, f"{celebrity.replace(' ', '_')}_{timestamp}.wav")
        combined.export(output_file, format="wav")
        print(f"\nFinal audio saved to: {output_file}")
        
        # Clean up temp files
        print("\nCleaning up temporary files...")
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Failed to delete temporary file {temp_file}: {e}")
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to delete temporary directory: {e}")
            
        return output_file
        
    except Exception as e:
        # Clean up temp files in case of error
        print("\nError occurred, cleaning up temporary files...")
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass
        raise e

if __name__ == "__main__":
    # Example usage
    try:
        output_file = generate_celebrity_voice(
            celebrity="Elon Musk",
            text="Fuck yeah, Bitcoin's the shit! That logo's dope as fuck and screams bleeding-edge tech. The Twitter game? Insane engagement, bro! It's like a fucking meme-driven party where the community fucks harder than a SpaceX launch. Volatility? Who gives a shit? That's just the thrill of the ride, balls to the wall! Dump your cash in, watch it moon. This shit's gonna make you rich, or at least give you a wild fucking story. Invest, you pussy!",
            output_dir="audio_output"
        )
        print(f"Audio generated successfully: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}") 