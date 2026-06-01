# AgeisOS2 - Jarvis Assistant

An AI-powered voice assistant with multi-layer security for safe script execution.

## Project Structure

- `frontend-ui/` - React/Vite frontend with TailwindCSS
- `backend-bridge/` - Express/Socket.IO server for communication
- `python-core/` - Core assistant logic with voice recognition and AI integration

## Features

- Voice wake word detection ("wake up")
- AI-powered script generation using Ollama (llama3.2:3b)
- Multi-layer security:
  - Static blacklist of dangerous commands
  - Intent validation via AI
  - Manual approval before execution
- Cross-platform support (Windows PowerShell, macOS/Linux Bash)
- Native OS notifications and text-to-speech
- Real-time communication via Socket.IO

## Security Layers

1. **Static Blacklist**: Blocks known dangerous command patterns
2. **Intent Validator**: Uses AI to verify script matches user request
3. **Manual Approval**: Requires explicit user confirmation before execution
4. **VRAM Flush**: Sends keep_alive: 0 to Ollama after execution to clear memory

## Setup

1. Install Ollama and pull llama3.2:3b model
2. Install Vosk model for speech recognition:
   ```bash
   # Download Vosk model (small English)
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   mv vosk-model-small-en-us-0.15 python-core/models/vosk-model-en-us
   ```
3. Install dependencies:
   ```bash
   # Backend
   cd backend-bridge && npm install
   
   # Frontend  
   cd frontend-ui && npm install
   
   # Python core
   cd python-core && pip install -r requirements.txt
   ```
4. Start the system:
   ```bash
   # Terminal 1: Backend
   cd backend-bridge && npm start
   
   # Terminal 2: Frontend
   cd frontend-ui && npm run dev
   
   # Terminal 3: Python core
   cd python-core && python core.py
   ```

## Usage

Say "wake up" followed by your command, for example:
- "wake up open notepad"
- "wake up create a file called test.txt with content hello world"
- "wake up list files in current directory"

The assistant will:
1. Listen for wake word
2. Capture your command
3. Generate a script using AI
4. Validate the script for safety
5. Request your approval
6. Execute if approved
7. Flush AI model memory

## Files of Interest

- `python-core/core.py` - Main assistant logic
- `backend-bridge/server.js` - Socket.IO bridge
- `frontend-ui/src/main.jsx` - React entry point
- `python-core/requirements.txt` - Python dependencies

## License

MIT
