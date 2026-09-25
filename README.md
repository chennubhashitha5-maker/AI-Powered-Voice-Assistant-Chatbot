# AI-Powered Voice Assistant Chatbot for Faculty Information and Timetable Retrieval

## Project Overview

The **AI-Powered Voice Assistant Chatbot for Faculty Information and Timetable Retrieval** is a voice-enabled academic assistant developed to simplify access to faculty information and class timetables within a college environment.

Instead of manually searching through faculty records or timetable documents, users can interact with the system using natural voice commands. The assistant converts speech into text, understands the user's query, retrieves the required information from the database, generates a natural language response using a Large Language Model (LLM), and finally speaks the answer back to the user.

The project combines Artificial Intelligence, Retrieval-Augmented Generation (RAG), Speech Processing, and Database Retrieval to provide a fast and user-friendly academic assistant.

---

## Features

- Voice-based interaction
- Faculty information retrieval
- Timetable retrieval
- Speech-to-Text using Whisper
- Query classification and routing
- Retrieval-Augmented Generation (RAG)
- Response generation using Mistral (Ollama)
- Text-to-Speech response
- PostgreSQL database integration
- ChromaDB-based document retrieval

---

## System Architecture

```text
                 Voice Input
                      │
                      ▼
          Speech-to-Text (Whisper)
                      │
                      ▼
            Query Classification
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 Faculty Information      Timetable Retrieval
      Retrieval
          └───────────┬───────────┘
                      ▼
        PostgreSQL / ChromaDB Retrieval
                      │
                      ▼
            Mistral LLM (Ollama)
                      │
                      ▼
             Natural Language Answer
                      │
                      ▼
              Text-to-Speech Output
```

---

## Workflow

1. Capture the user's voice through a microphone.
2. Convert speech into text using **Whisper**.
3. Classify the user's query.
4. Retrieve the required faculty or timetable information.
5. Generate a natural language response using **Mistral (Ollama)**.
6. Convert the generated response into speech.
7. Play the voice response to the user.

---

## Technologies Used

| Category | Technology |
|----------|------------|
| Programming Language | Python |
| Database | PostgreSQL |
| Vector Database | ChromaDB |
| LLM | Mistral (Ollama) |
| Speech-to-Text | Whisper |
| Text-to-Speech | pyttsx3 |
| AI | Retrieval-Augmented Generation (RAG) |

---

## Project Structure

```text
voice_assistant/
│
├── voice_assistant.py
├── answer_generate.py
├── router.py
├── query_classifier.py
├── service_classifier.py
├── faculty_retriever.py
├── timetable_retriever.py
├── timetable_service.py
├── speech_to_text.py
├── text_to_speech.py
├── record_audio.py
├── play_audio.py
├── faculty_name_matcher.py
├── prepare_documents2.py
├── build_chroma.py
├── ingest.py
├── faculty.csv
├── time_table.csv
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/chennubhashitha5-maker/AI-Powered-Voice-Assistant-Chatbot.git
```

Move into the project folder:

```bash
cd AI-Powered-Voice-Assistant-Chatbot
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Ensure the following are installed and running:

- PostgreSQL
- Ollama
- Whisper
- Mistral model
- ChromaDB

---

## Sample Queries

Faculty Information

- Who is M. Aruna Safali?
- What is the qualification of P. Narasimham?
- When did A. Sudhakar join?

Timetable

- Who teaches Machine Learning?
- Show today's timetable.
- What is the next class for CSM-2?
- Which room has DBMS now?
- Show Friday timetable.

---

## Screenshots

### Voice Assistant Workflow

![Voice Assistant Workflow](screenshots/voice_assistant_workflow.png)

---

### Assistant Taking Input

![Assistant Taking Input](screenshots/Assistant_taking_input.png)

---

### Faculty Profile Result

![Faculty Profile Result](screenshots/faculty_profile_result.png)

---

### Timetable Result

![Timetable Result](screenshots/timetable_result.png)

---

## Future Enhancements

- Web interface
- Mobile application
- Multi-language support
- Real-time timetable updates
- Authentication system
- Cloud deployment

---

## Author

**Chennu Bhashitha**

B.Tech – Computer Science and Engineering (AI & ML)

GitHub: https://github.com/chennubhashitha5-maker