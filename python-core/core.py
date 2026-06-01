import sys
import requests
import subprocess
import os
import json
import time
import sounddevice as sd
import vosk
import queue
from socketIO_client import SocketIO, LoggingNamespace
from plyer import notification
import platform
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: pyttsx3 not installed. Text-to-speech disabled.")

# Initialize text-to-speech engine
if TTS_AVAILABLE:
    tts_engine = pyttsx3.init()
    # Set properties for clearer speech
    tts_engine.setProperty('rate', 150)    # Speed of speech
    tts_engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
    # Optional: Set voice (0 for male, 1 for female on many systems)
    voices = tts_engine.getProperty('voices')
    if voices:
        tts_engine.setProperty('voice', voices[0].id)  # Use first available voice

# Configuration
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"  # Adjust if needed
SOCKET_IO_HOST = "localhost"
SOCKET_IO_PORT = 5000
WAKE_WORD = "wake up"  # Change to your desired wake word

# Voice recognition setup
MODEL_PATH = "models/vosk-model-en-us"
SAMPLE_RATE = 16000
q = queue.Queue()

# Initialize Socket.IO client
socketIO = SocketIO(SOCKET_IO_HOST, SOCKET_IO_PORT, LoggingNamespace)

# Dangerous commands blacklist (Layer 1)
DANGEROUS_COMMANDS = [
    # Windows PowerShell dangerous commands
    "Remove-Item -Recurse -Force",
    "Remove-Item C:\\",
    "Format-Volume",
    "Clear-Disk",
    "Set-ItemProperty -Path HKLM:",
    "Set-ItemProperty -Path HKCU:",
    "Invoke-Expression",
    "iex ",
    "Start-Process",
    "ssh ",
    "net user",
    "net localgroup administrators",
    # Unix/Linux/macOS dangerous commands
    "rm -rf",
    "rm -rf /",
    "mkfs",
    "fdisk",
    "> /dev/sda",
    "dd if=",
    "chmod -R 777",
    "sudo rm -rf",
    "> /etc/passwd",
    "mv / /dev/null",
    # General dangerous patterns
    "format",
    "del /f /s /q",
    "shutdown",
    "restart-computer",
    "stop-service",
]

def is_windows():
    return platform.system() == "Windows"

def is_macos():
    return platform.system() == "Darwin"

def is_linux():
    return platform.system() == "Linux"

def get_os_script_type():
    if is_windows():
        return "PowerShell"
    elif is_macos() or is_linux():
        return "Bash"
    else:
        return "Unknown"

def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def listen_for_wake_word():
    """Listen for audio and detect wake word using Vosk."""
    try:
        # Check if model exists
        if not os.path.exists(MODEL_PATH):
            print(f"Model not found at {MODEL_PATH}")
            print("Please run the model download steps first.")
            print("Falling back to console input...")
            return None

        model = vosk.Model(MODEL_PATH)
        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

        print("\n=== Jarvis Assistant (Voice Mode) ===")
        print("Listening for wake word: 'wake up'")
        print("Speak now...")

        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                               channels=1, callback=audio_callback):
            while True:
                data = q.get()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').lower().strip()
                    if text:
                        print(f"You said: {text}")
                        # Check for wake word
                        if WAKE_WORD in text:
                            # Extract command after wake word
                            command = text.split(WAKE_WORD, 1)[1].strip()
                            if command:
                                print(f"Wake word detected! Command: {command}")
                                return command
                            else:
                                print("Wake word detected but no command provided.")
                                # Continue listening for command after wake word
                                return listen_for_command_after_wake(recognizer, q)
                else:
                    # Partial results (optional, for debugging)
                    # partial = json.loads(recognizer.PartialResult())
                    # print(f"Partial: {partial.get('partial', '')}", end='\r')
                    pass
    except Exception as e:
        print(f"Error in voice recognition: {e}")
        return None

def listen_for_command_after_wake(recognizer, q):
    """Continue listening for a command after wake word is detected."""
    print("Listening for command...")
    silence_count = 0
    max_silence = 25  # About 1 second of silence at 16kHz, 8000 blocksize

    while silence_count < max_silence:
        try:
            data = q.get(timeout=0.1)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').lower().strip()
                if text:
                    print(f"Command: {text}")
                    return text
                else:
                    silence_count += 1
            else:
                silence_count += 1
        except queue.Empty:
            silence_count += 1

    print("No command detected after wake word.")
    return None

def get_user_input():
    """Get user input from microphone with wake word detection."""
    # Try voice recognition first
    voice_result = listen_for_wake_word()
    if voice_result is not None:
        return voice_result

    # Fallback to console input if voice fails
    print("\n=== Jarvis Assistant (Console Fallback) ===")
    print("Say 'wake up' followed by your command (or type 'exit' to quit)")
    user_input = input("> ").strip()

    if user_input.lower() == 'exit':
        return None

    # Simulate wake word detection
    if WAKE_WORD in user_input.lower():
        # Extract command after wake word
        command = user_input.lower().split(WAKE_WORD, 1)[1].strip()
        if command:
            print(f"Wake word detected! Command: {command}")
            return command
        else:
            print("Wake word detected but no command provided.")
            return get_user_input()  # Ask again
    else:
        print(f"Wake word not detected. Please say '{WAKE_WORD}' followed by your command.")
        return get_user_input()  # Ask again

def generate_script(user_request):
    """Generate a script from the user request using Ollama."""
    system_prompt = f"""
You are an AI assistant that generates only executable {get_os_script_type()} scripts to fulfill user requests.
Your response must be ONLY the script, with no explanations, no markdown formatting, no backticks, and no additional text.
If the request cannot be fulfilled with a script, output exactly: "ERROR: Cannot generate script for this request."
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system_prompt}\nUser Request: {user_request}",
        "stream": False
    }
    try:
        response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        response.raise_for_status()
        result = response.json()
        script = result.get("response", "").strip()
        # Remove any markdown code block markers if present
        if script.startswith("```") and script.endswith("```"):
            script = "\n".join(script.split("\n")[1:-1])
        return script
    except Exception as e:
        print(f"Error generating script: {e}")
        return ""

def static_blacklist_check(script):
    """Layer 1: Check for dangerous commands in the script."""
    script_lower = script.lower()
    for command in DANGEROUS_COMMANDS:
        if command.lower() in script_lower:
            print(f"Blacklist hit: {command}")
            return True, command
    return False, None

def intent_validator_check(user_request, script):
    """Layer 2: Validate intent by asking Ollama to compare request and script."""
    system_prompt = """
Compare the User Request with the Script.
Does the script attempt to access, read, or delete files, folders, or settings that were NOT explicitly mentioned or logically required?
Output only YES or NO.
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system_prompt}\nUser Request: {user_request}\nScript: {script}",
        "stream": False
    }
    try:
        response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        response.raise_for_status()
        result = response.json()
        verdict = result.get("response", "").strip().upper()
        return verdict == "YES"
    except Exception as e:
        print(f"Error in intent validation: {e}")
        return False  # Fail safe: if validation fails, treat as overstep

def send_keep_alive_zero():
    """Send keep_alive: 0 to Ollama to flush VRAM."""
    try:
        response = requests.post(f"{OLLAMA_HOST}/api/generate",
                                json={"model": OLLAMA_MODEL, "prompt": "", "keep_alive": 0},
                                timeout=5)
        print("VRAM flush signal sent.")
    except Exception as e:
        print(f"Error sending keep_alive: {e}")

def notify_user(title, message):
    """Send a native OS notification."""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Jarvis Assistant",
            timeout=10  # seconds
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

def speak_text(text):
    """Convert text to speech using pyttsx3."""
    if TTS_AVAILABLE:
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
    else:
        print(f"(TTS would say: {text})")

def execute_script(script):
    """Execute the script using subprocess."""
    try:
        if is_windows():
            # PowerShell execution
            completed = subprocess.run(["powershell", "-Command", script],
                                       capture_output=True, text=True, timeout=30)
        else:
            # Bash execution (macOS/Linux)
            completed = subprocess.run(["bash", "-c", script],
                                       capture_output=True, text=True, timeout=30)

        if completed.returncode == 0:
            print(f"Script executed successfully.\nOutput: {completed.stdout}")
            return True, completed.stdout
        else:
            print(f"Script execution failed.\nError: {completed.stderr}")
            return False, completed.stderr
    except subprocess.TimeoutExpired:
        print("Script execution timed out.")
        return False, "Execution timed out"
    except Exception as e:
        print(f"Error executing script: {e}")
        return False, str(e)

def main():
    print("Jarvis Assistant starting in console mode (no microphone)...")
    print(f"OS: {platform.system()}")
    print(f"Script type: {get_os_script_type()}")

    # Connect Socket.IO events
    @socketIO.on('connect')
    def on_connect():
        print("Connected to backend bridge")

    @socketIO.on('disconnect')
    def on_disconnect():
        print("Disconnected from backend bridge")

    # Main loop
    while True:
        try:
            # Step 1: Get user input (simulating wake word + command)
            user_request = get_user_input()
            if user_request is None:
                print("Shutting down Jarvis Assistant...")
                break
            if not user_request:
                continue

            # Step 2: Generate script
            print("Generating script...")
            script = generate_script(user_request)
            if not script or script.startswith("ERROR"):
                print("Failed to generate script.")
                notify_user("Jarvis Error", "Failed to generate script for your request.")
                send_keep_alive_zero()
                continue

            print(f"Generated script:\n{script}")

            # Step 3: Layer 1 - Static Blacklist
            blacklisted, dangerous_cmd = static_blacklist_check(script)
            if blacklisted:
                print(f"Blocked by blacklist: {dangerous_cmd}")
                notify_user("Jarvis Alert", "Blocked unauthorized OS action.")
                speak_text("Jarvis Alert: Blocked unauthorized OS action.")
                socketIO.emit('blocked_execution', {
                    "script": script,
                    "reason": f"Blacklisted command: {dangerous_cmd}"
                })
                send_keep_alive_zero()
                continue

            # Step 4: Layer 2 - Intent Validator
            print("Validating intent...")
            overstep = intent_validator_check(user_request, script)
            if overstep:
                print("Blocked by intent validator: overstep detected.")
                notify_user("Jarvis Alert", "Blocked unauthorized OS action.")
                socketIO.emit('blocked_execution', {
                    "script": script,
                    "reason": "Intent validation failed: overstep"
                })
                send_keep_alive_zero()
                continue

            # Step 5: Safe Execution - Pending approval
            print("Script passed safety checks. Pending user approval.")
            socketIO.emit('pending_execution', {
                "script": script,
                "request": user_request
            })

            # Wait for action_approved event from the frontend
            approved = [False]  # Use a list to allow modification in nested function
            def on_action_approved(*args):
                print("Action approved by user.")
                approved[0] = True
            socketIO.on('action_approved', on_action_approved)

            # Wait for approval (with timeout to avoid hanging)
            start_time = time.time()
            while not approved[0] and (time.time() - start_time) < 30:  # 30 second timeout
                socketIO.wait(seconds=1)

            if not approved[0]:
                print("Approval timed out.")
                notify_user("Jarvis Alert", "Execution approval timed out.")
                socketIO.emit('blocked_execution', {
                    "script": script,
                    "reason": "Approval timeout"
                })
                send_keep_alive_zero()
                continue

            # Step 6: Execute the script
            print("Executing script...")
            success, output = execute_script(script)
            if success:
                print("Execution successful.")
                notify_user("Jarvis Success", "Script executed successfully.")
                speak_text("Jarvis Success: Script executed successfully.")
                socketIO.emit('execution_result', {
                    "success": True,
                    "output": output
                })
            else:
                print("Execution failed.")
                notify_user("Jarvis Error", f"Script execution failed: {output}")
                speak_text(f"Jarvis Error: Script execution failed.")
                socketIO.emit('execution_result', {
                    "success": False,
                    "output": output
                })

            # Step 7: VRAM Flush
            send_keep_alive_zero()

        except KeyboardInterrupt:
            print("\nShutting down Jarvis Assistant...")
            break
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            notify_user("Jarvis Error", f"Unexpected error: {str(e)}")
            send_keep_alive_zero()
            continue

if __name__ == "__main__":
    main()