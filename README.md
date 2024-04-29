# YouTubeShorts Extractor from long videos

This project is designed to extract YouTube Shorts from long videos. YouTube Shorts are brief videos that are less than 60 seconds in duration and are designed to be concise and engaging. By extracting important sentences from long videos and providing detailed points with a length of more than 100 words, this tool helps in creating concise video shorts suitable for platforms like YouTube Shorts.

## Technologies Used
- `requests`: For making HTTP requests to APIs.
- `time`: For handling time-related operations.
- `moviepy`: For video file manipulation.
- `google.generativeai`: For utilizing Google's Generative AI model.
- `os`: For interacting with the operating system.
- `pydub`: For audio file manipulation.
- `spacy`: For natural language processing tasks.

## How to Use
1. Install the required libraries:
    ```
    pip install -r requirements.txt
    ```

2. Set up environment variables:
    - `GOOGLE_API_KEY`: Your Google API key for generative AI.
    - `ASSEMBLY_API_KEY`: Your AssemblyAI key for audio transcription.

3. Run the script `main.py` with the path to the long video as an argument:
    ```
    python main.py <path_to_long_video>
    ```

4. After execution, the tool will generate trimmed and speed-up video clips in the `output` folder.

## Deployment
This project is deployed using Streamlit, providing a user-friendly interface for users to interact with. You can deploy it to Streamlit by executing the following command:
```
streamlit run app.py
```

## It can also be checked Live on following link 
```
https://aishortsmaker.streamlit.app/
```
!! It might take time to load and I am working on it.

## Note
- Ensure that the input video is sufficiently long to extract meaningful content for YouTube Shorts.
- The extracted segments are based on similarity scores with the summarized text, so some manual curation might be required.
- Adjustments to the speed and duration of the extracted clips can be made in the code as needed.
- Make sure to comply with the terms of service of YouTube and other platforms while using this tool.

Feel free to contribute to this project by creating issues or submitting pull requests. Happy video shortening! 🎥
