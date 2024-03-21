import requests
import time
from moviepy.video.io.VideoFileClip import VideoFileClip
import google.generativeai as genai
import os
from pydub import AudioSegment
import spacy

def final(video_path):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.0-pro-latest')

    generation_config = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
    }

    safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_ONLY_HIGH"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_ONLY_HIGH"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_ONLY_HIGH"
    },
    ]

    model = genai.GenerativeModel(model_name="gemini-1.0-pro",
                                generation_config=generation_config,
                                safety_settings=safety_settings)



    video_clip = VideoFileClip(video_path)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile("output_audio.wav")

    base_url = "https://api.assemblyai.com/v2"
    headers = {
        "authorization": os.environ.get("ASSEMBLY_API_KEY")
    }
    with open("output_audio.wav", "rb") as f:
        response = requests.post(base_url + "/upload",
                        headers=headers,
                        data=f)

    upload_url = response.json()["upload_url"]
    data = {
        "audio_url": upload_url
    }
    url = base_url + "/transcript"
    response = requests.post(url, json=data, headers=headers)
    transcript_id = response.json()['id']
    polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        transcription_result = requests.get(polling_endpoint, headers=headers).json()
        if transcription_result['status'] == 'completed':
            # Saved the transcription result to a text file named 'transcript.txt'
            with open('transcript.txt', 'w', encoding='utf-8') as file:
                transcript_text=transcription_result['text']
                # file.write(transcription_result['text'])
            # print(transcription_result['text'])
            break
        elif transcription_result['status'] == 'error':
            raise RuntimeError(f"Transcription failed: {transcription_result['error']}")
        else:
            time.sleep(3)
    # with open("transcript.txt", "r") as file:
    #     transcript_text = file.read()
    ad="/nExtract important sentences from the given video transcript, providing long detailed points with a length of more than 100 words. The extracted points should be suitable for creating concise video shorts."
    prompt= transcript_text + ad
    response = model.generate_content(prompt)
    summary = transcript_text[0:100] + response.text.replace("*","").replace("-","")
    # with open('summary.txt', 'w') as file:
    #     file.write(transcript_text[0:100])
    #     file.write((response.text).replace("*","").replace("-",""))
    


    def get_audio_duration(file_path):
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000  # Converting milliseconds to seconds


    def find_segments(video_transcript, summarized_text):
        # Load spaCy models
        nlp = spacy.load("en_core_web_lg")

        try:
            # Read the video transcript
            # with open(video_transcript, 'r', encoding='utf-8') as file:
            doc_video = nlp(transcript_text)

            # Read the summarized text
            # with open(summarized_text, 'r', encoding='utf-8') as file:
            doc_summary = nlp(summary)

        except Exception as e:
            print(f"Error reading files: {e}")
            return []

        # Initialized an empty list to store matching segments
        matching_segments = []

        # Iterating over sentences in the video transcript
        for sentence in doc_video.sents:
            # Calculating the similarity between the summarized text and the current sentence in the video transcript
            similarity_score = sentence.similarity(doc_summary)

            # Defined a similarity threshold
            similarity_threshold = 0.5

            # If the similarity score is above the threshold, consider it a match
            if similarity_score > similarity_threshold:
                # Extract the start and end character offsets of the matching sentence
                start_char = sentence.start_char
                end_char = sentence.end_char

                # Convert character offsets to time (in seconds) using the start and end time of the video
                start_time = round(start_char / len(doc_video.text) * total_video_duration,0)
                end_time = round(end_char / len(doc_video.text) * total_video_duration,0)
                if end_time - start_time > 10  and end_time - start_time < 90:
                # Add the matching segment to the list
                    matching_segments.append((start_time, end_time))
        return matching_segments
    audio_path="output_audio.wav"
    total_video_duration= get_audio_duration(audio_path)
    video_transcript = "transcript.txt"
    summarized_text = "summary.txt"
    matching_segments = find_segments(video_transcript, summarized_text)
    print("Matching Segments:", matching_segments)


    for start_time, end_time in matching_segments:
        print(f"Cut video from {start_time} seconds to {end_time} seconds.")


    def trim_and_speedup_video(video_path, output_folder, start_time, end_time, speed_factor=1.5):
        """
        Trims a video based on timestamps, speeds it up, and saves the clip as a separate file.
        """
        start_seconds = start_time
        end_seconds = end_time
        output_filename = f"clip_{end_time}_speedup.mp4"
        output_path = os.path.join(output_folder, output_filename)

        # Use FFmpeg to trim and speed up the video
        command = f"ffmpeg -i {video_path} -ss {start_seconds} -to {end_seconds} -vf 'setpts={1/speed_factor}*PTS' -af 'atempo={speed_factor}' {output_path}"
        print(f"Trimming and speeding up video: {output_path}")
        os.system(command)

    # Define the video path and output folder
    output_folder = "./output"

    # Read the list of timestamps
    timestamps = matching_segments  # Replace with your actual timestamps

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Trim and speed up each clip based on the timestamps
    for i in timestamps:
        start_time = i[0] - 20 if i[0] > 20 else i[0]
        end_time = i[1] + 20

        # Ensure the difference between start_time and end_time is at least 60 seconds
        if end_time - start_time < 60:
            end_time = start_time + 60

        trim_and_speedup_video(video_path, output_folder, start_time, end_time)

    print("All video clips trimmed and sped up successfully!")