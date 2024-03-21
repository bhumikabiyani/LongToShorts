import requests
import time
import streamlit as st
from moviepy.video.io.VideoFileClip import VideoFileClip
import google.generativeai as genai
import os
from pydub import AudioSegment
import spacy

@st.cache
def generate_summary(transcript_text):
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.0-pro-latest')

    ad = "/nExtract important sentences from the given video transcript, providing long detailed points with a length of more than 100 words. The extracted points should be suitable for creating concise video shorts."
    prompt = transcript_text + ad
    response = model.generate_content(prompt)
    summary = transcript_text[0:100] + response.text.replace("*", "").replace("-", "")

    return summary

@st.cache
def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000  # Converting milliseconds to seconds

@st.cache
def find_segments(video_transcript, summarized_text, total_video_duration):
    # Load spaCy models
    nlp = spacy.load("en_core_web_lg")

    try:
        doc_video = nlp(video_transcript)
        doc_summary = nlp(summarized_text)

    except Exception as e:
        st.error(f"Error reading files: {e}")
        return []

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

@st.cache
def trim_and_speedup_video(video_path, output_folder, start_time, end_time, speed_factor=1.5):
    start_seconds = start_time
    end_seconds = end_time
    output_filename = f"clip_{end_time}_speedup.mp4"
    output_path = os.path.join(output_folder, output_filename)

    command = f"ffmpeg -i {video_path} -ss {start_seconds} -to {end_seconds} -vf 'setpts={1/speed_factor}*PTS' -af 'atempo={speed_factor}' {output_path}"
    os.system(command)

@st.cache
def process_video(video_path, output_folder, matching_segments):
    os.makedirs(output_folder, exist_ok=True)
    total_video_duration = get_audio_duration(video_path)
    for start_time, end_time in matching_segments:
        start_time = start_time - 20 if start_time > 20 else start_time
        end_time = end_time + 20

        if end_time - start_time < 60:
            end_time = start_time + 60

        trim_and_speedup_video(video_path, output_folder, start_time, end_time)

    st.write("All video clips trimmed and sped up successfully!")

def main(video_path):
    video_clip = VideoFileClip(video_path)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile("output_audio.wav")

    base_url = "https://api.assemblyai.com/v2"
    headers = {
        "authorization": os.environ.get("ASSEMBLY_API_KEY")
    }
    with open("output_audio.wav", "rb") as f:
        response = requests.post(base_url + "/upload", headers=headers, data=f)

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
            transcript_text = transcription_result['text']
            break
        elif transcription_result['status'] == 'error':
            raise RuntimeError(f"Transcription failed: {transcription_result['error']}")
        else:
            time.sleep(3)

    summary = generate_summary(transcript_text)
    matching_segments = find_segments(transcript_text, summary, get_audio_duration("output_audio.wav"))
    process_video(video_path, "./output", matching_segments)

if __name__ == "__main__":
    video_path = "your_video_path.mp4"  # Provide your video path
    main(video_path)
