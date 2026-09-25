# AI-Powered Voice Assistant Chatbot for Faculty Information and Timetable Retrieval

## Project Overview

The AI-Powered Voice Assistant for Faculty Information and Timetable Retrieval is a voice-enabled academic assistant developed to simplify the process of accessing faculty information and class timetables within a college environment.

Users can interact with the system using natural voice commands. The assistant converts speech to text, understands the user's query, retrieves the required information, generates a response using a Large Language Model (LLM), and speaks the answer back to the user.

The project combines Artificial Intelligence, Retrieval-Augmented Generation (RAG), and database retrieval to provide a fast and user-friendly academic assistant.

## Features

- Voice-based interaction
- Faculty information retrieval
- Timetable retrieval
- Speech-to-Text using Whisper
- Response generation using Mistral (Ollama)
- Retrieval-Augmented Generation (RAG) with ChromaDB
- Text-to-Speech response
- PostgreSQL database integration

## Technologies Used

- Python
- PostgreSQL
- Ollama
- Mistral
- Whisper
- ChromaDB
- Sentence Transformers
- pyttsx3

## Project Structure

```text
voice_assistant/
├── voice_assistant.py
├── answer_generate.py
├── router.py
├── faculty_retriever.py
├── timetable_retriever.py
├── speech_to_text.py
├── text_to_speech.py
├── faculty.csv
├── time_table.csv
├── chroma_db/
```

## Future Enhancements

- Web interface
- Mobile application
- Multi-language support
- Real-time timetable updates