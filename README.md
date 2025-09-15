# 🤖 AI Excel Interviewer

An AI-powered mock interviewer for Excel jobs. This full-stack application provides realistic, voice-based practice using Google Gemini for dynamic questions and Whisper for speech-to-text. The React and FastAPI platform records the session and generates a private feedback report for evaluation.

---

## ✨ Features

* **Dynamic Conversations**: Uses the Google Gemini API to generate natural greetings and dynamic follow-up questions based on the candidate's introduction.
* **Voice-to-Voice Interaction**: Leverages `faster-whisper` for real-time Speech-to-Text and `pyttsx3` for Text-to-Speech, creating a seamless conversational experience.
* **Full Session Recording**: Captures the candidate's video throughout the interview, saving chunked recordings that are merged into a single file upon completion.
* **Automated Feedback**: Generates a private, high-level performance report for review by a hiring manager.
* **Structured Interview Flow**: Blends a set of predefined technical questions with AI-generated follow-ups for a comprehensive interview.

---

## 🛠️ Technology Stack

* **Backend**: Python, FastAPI, Uvicorn
* **Frontend**: React.js, Axios
* **AI & ML**:
    * **LLM**: Google Gemini API
    * **Speech-to-Text**: `faster-whisper`
    * **Text-to-Speech**: `pyttsx3`
* **Tools & Dependencies**:
    * `ffmpeg` (for video merging)

---

## 🚀 Getting Started

Follow these instructions to set up and run the project on your local machine.

### Prerequisites

Ensure you have the following installed on your system. These specific versions and tools are required to ensure all dependencies build and run correctly.

* **Python 3.11** ([Download](https://www.python.org/downloads/windows/))
* **Node.js and npm** ([Download](https://nodejs.org/en))
* **Git** ([Download](https://git-scm.com/downloads))
* **ffmpeg**: Required for audio and video processing.
    * *Windows*: Install via Chocolatey: `choco install ffmpeg`
    * *macOS*: Install via Homebrew: `brew install ffmpeg`
* **Microsoft Visual C++ 14.0 or greater** (Windows only)
    * Install the "Desktop development with C++" workload from the [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

### Installation

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
    cd your-repository-name
    ```

2.  **Set up the Backend:**
    ```sh
    # Navigate to the backend directory
    cd backend

    # Create and activate a Python 3.11 virtual environment
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # macOS/Linux

    # Install the required Python packages
    pip install -r requirements.txt
    ```

3.  **Set up the Frontend:**
    ```sh
    # Navigate to the frontend directory from the root
    cd frontend

    # Install the required npm packages
    npm install
    ```

### Configuration

The backend requires an API key for the Google Gemini service.

1.  In the `backend` directory, create a new file named `.env`.
2.  Open the `.env` file and add your API key in the following format:

    ```env
    GOOGLE_API_KEY="your_google_api_key_here"
    ```
    You can also optionally specify a different Gemini model:
    ```env
    GEMINI_MODEL="gemini-1.5-flash-latest"
    ```

---

## ▶️ Running the Application

You will need to run two separate terminal sessions.

1.  **Start the Backend Server:**
    * Open a terminal, navigate to the `backend` folder, and activate the virtual environment.
    * Run the following command:
        ```sh
        uvicorn main:app --reload --port 8000
        ```

2.  **Start the Frontend Server:**
    * Open a **second** terminal and navigate to the `frontend` folder.
    * Run the following command:
        ```sh
        npm start
        ```

The application will automatically open in your browser at **`http://localhost:3000`**.

---