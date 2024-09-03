import streamlit as st
import requests
import time
from moviepy.video.io.VideoFileClip import VideoFileClip
import google.generativeai as genai
import os
from pydub import AudioSegment
import spacy
import assemblyai as aai
import shutil
from dotenv import load_dotenv
load_dotenv()

# Initialize Streamlit app
st.title("Video Transcript Processing and Segment Extraction")

# Step 1: Upload video file
video_file = st.file_uploader("Upload your video file", type=["mp4"])

if video_file:
    # Ensure the temp directory exists
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)

    # Save uploaded video
    video_path = os.path.join(temp_dir, video_file.name)
    with open(video_path, "wb") as f:
        f.write(video_file.getbuffer())
    st.video(video_path)

    # Add a button to start the process
    if st.button("Start Processing"):
        # Initialize progress bar with percentage
        progress_bar = st.progress(0)
        progress_step = 20  # Each step is 20% of the progress
        progress_text = st.empty()  # This creates an empty placeholder

        def update_progress(progress_bar, step, total_steps):
            percentage = int((step / total_steps) * 100)
            progress_bar.progress(percentage)

        total_steps = 5  # Total number of steps in the process

        # Extract audio from video
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_path = os.path.join(temp_dir, "output_audio.wav")
        audio_clip.write_audiofile(audio_path)
        
        update_progress(progress_bar, 1, total_steps)

        # Step 2: Transcribe audio using AssemblyAI
        base_url = "https://api.assemblyai.com/v2"
        headers = {
            "authorization": os.getenv("ASSEMBLY_API_KEY")
        }

        with open(audio_path, "rb") as f:
            response = requests.post(base_url + "/upload", headers=headers, data=f)

        upload_url = response.json()["upload_url"]

        aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(upload_url)

        while True:
            if transcript.status == aai.TranscriptStatus.error:
                st.error("Transcription error: " + transcript.error)
                break
            elif transcript.status == aai.TranscriptStatus.completed:
                transcript_text = transcript.text
                with open(os.path.join(temp_dir, 'transcript.txt'), 'w', encoding='utf-8') as file:
                    file.write(transcript_text)
                update_progress(progress_bar, 2, total_steps)
                break
            else:
                time.sleep(3)

        # Step 3: Generate summary using Google Generative AI
        ad = "\nExtract important sentences from the given video transcript. The extracted points should be suitable for creating concise video shorts and do not output anything else along with the segments."
        prompt = transcript_text + ad

        # Configure the API key for Google Generative AI
        genai.configure(os.getenv("GOOGLE_API_KEY"))

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

        response = model.generate_content(prompt)
        summary = transcript_text[:100] + response.text.replace("*", "").replace("-", "")
        with open(os.path.join(temp_dir, 'summary.txt'), 'w') as file:
            file.write(summary)
        
        update_progress(progress_bar, 3, total_steps)

        # Step 4: Find matching segments
        nlp = spacy.load("en_core_web_lg")

        def get_audio_duration(file_path):
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000  # Convert milliseconds to seconds

        def find_segments(transcript_text, summary, total_video_duration):
            doc_video = nlp(transcript_text)
            doc_summary = nlp(summary)

            matching_segments = []

            for sentence in doc_video.sents:
                similarity_score = sentence.similarity(doc_summary)

                similarity_threshold = 0.5
                if similarity_score > similarity_threshold:
                    start_char = sentence.start_char
                    end_char = sentence.end_char

                    start_time = round(start_char / len(doc_video.text) * total_video_duration, 0)
                    end_time = round(end_char / len(doc_video.text) * total_video_duration, 0)
                    if end_time - start_time > 10 and end_time - start_time < 90:
                        matching_segments.append((start_time, end_time))

            return matching_segments

        total_video_duration = get_audio_duration(audio_path)
        matching_segments = find_segments(transcript_text, summary, total_video_duration)
        
        update_progress(progress_bar, 4, total_steps)

        # Step 5: Trim video based on segments
        output_folder = "./output"
        os.makedirs(output_folder, exist_ok=True)

        # Define the number of columns you want to display
        num_columns = 3
        clips_per_column = len(matching_segments) // num_columns + (len(matching_segments) % num_columns > 0)

        columns = st.columns(num_columns)

        for i, (start_time, end_time) in enumerate(matching_segments):
    # Update the text with a moving effect
            progress_text.text(f"Creating clips {'.' * ((i % 3) + 1)}")
    
    # Ensure the end time does not exceed the video duration
            if start_time >= total_video_duration:
                st.warning(f"Skipping segment starting at {start_time} seconds because it exceeds the video duration.")
                continue
    
    # Rest of your loop code for trimming and saving clips           
            end_time = min(end_time, total_video_duration)  # Adjust end time if it exceeds video duration

            start_time = max(start_time - 20, 0)  # Adjust start time if needed
            end_time = start_time + 60 if end_time - start_time < 60 else end_time  # Ensure clip is at least 60 seconds

            trimmed_clip = video_clip.subclip(start_time, end_time)
            output_filename = f"clip_{int(start_time)}_{int(end_time)}.mp4"
            output_path = os.path.join(output_folder, output_filename)
            
            try:
                trimmed_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
                # Display the video in the appropriate column
                col = columns[i % num_columns]
                col.video(output_path)
            except OSError as e:
                st.error(f"Error trimming video: {e}")

        update_progress(progress_bar, 5, total_steps)
        progress_text.text("Clips creation complete!")
        st.success("Video processing completed.")

        video_clip.close()

        # Step 6: Delete temporary files
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            st.error(f"Error deleting temporary files: {e}")
