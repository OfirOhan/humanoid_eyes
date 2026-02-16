import cv2
import time
import pickle
import serial
import threading
import speech_recognition as sr
from collections import Counter
import torch
from torch import serialization as _serialization
from facial_emotion_recognition import EmotionRecognition
from difflib import SequenceMatcher

# =========================================================
# 0) CONFIGURATION
# =========================================================
ARDUINO_PORT = 'COM7'

# SAFETY FLOOR: Ignore matches below this % (prevents noise triggering commands)
# 0.7 (70%) is a good balance.
SAFETY_THRESHOLD = 0.7

COMMANDS = {
    # KEY            : [LIST OF ALIASES]
    "STOP": ["stop", "quit", "pause", "terminate", "halt", "enough", "freeze"],
    "IMITATE": ["imitate", "mirror", "copy", "start", "mimic", "begin", "emulate"],

    "HAPPY": ["happy", "happiness", "laughing", "excited", "smile", "joy"],
    "SAD": ["sad", "sadness", "crying", "depressed", "unhappy", "sorrow"],
    "ANGRY": ["angry", "anger", "furious", "rage", "mad", "mean"],

    "RIGHT": ["right", "east"],
    "LEFT": ["left", "west"],
    "MIDDLE": ["middle", "center", "centre", "front", "forward"]
}

CURRENT_MODE = "IDLE"
stop_threads = False

# =========================================================
# 1) SERIAL CONNECTION
# =========================================================
try:
    arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=1)
    time.sleep(2)
    print("Arduino Connected!")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    arduino = None


def send_raw_command(cmd_char):
    if arduino:
        arduino.write(cmd_char)
        print(f"[VOICE] Sent: {cmd_char}")


def send_state_to_arduino(state):
    if arduino is None: return
    if CURRENT_MODE != "IMITATE": return

    cmd = {"Happy": b'H', "Sad": b'S', "Angry": b'A'}.get(state)
    if cmd:
        print(f"[VISION] STATE -> {state}")
        arduino.write(cmd)


# =========================================================
# 2) THE LOGIC: FIND HIGHEST SCORE
# =========================================================
def find_best_match(heard_sentence):
    """
    Compares every heard word against every alias.
    Returns the single Command Key with the highest score.
    """
    words = heard_sentence.split()

    best_command = None
    highest_score = 0.0
    winning_pair = ""

    # 1. Iterate EVERY word heard
    for word in words:
        # 2. Iterate EVERY command category
        for command_key, alias_list in COMMANDS.items():
            # 3. Iterate EVERY alias
            for alias in alias_list:
                score = SequenceMatcher(None, word, alias).ratio()

                # 4. Track the Global Maximum
                if score > highest_score:
                    highest_score = score
                    best_command = command_key
                    winning_pair = f"'{word}' vs '{alias}'"

    # 5. Result
    if highest_score >= SAFETY_THRESHOLD:
        print(f"[LOGIC] Winner: {best_command} ({int(highest_score * 100)}%) [{winning_pair}]")
        return best_command
    else:
        if highest_score > 0.4:
            print(f"[LOGIC] Ignored: Best match {best_command} was only {int(highest_score * 100)}%")
        return None


# =========================================================
# 3) AUDIO THREAD (GOOGLE SPEECH)
# =========================================================
def audio_listener_thread():
    global CURRENT_MODE, stop_threads

    # Force Mic Index 1
    mic = sr.Microphone(device_index=1)
    recognizer = sr.Recognizer()

    # Speed Settings
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5  # Fast reaction

    print("[AUDIO] Adjusting for noise...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)

    print("[AUDIO] Listening (Google Mode)...")

    while not stop_threads:
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=None)

            # Use Google (Fast, Online)
            try:
                raw_text = recognizer.recognize_google(audio).lower().strip()
                # Clean string
                clean_text = raw_text.replace(".", "").replace(",", "").replace("?", "").replace("!", "")
                print(f"[HEARD]: {clean_text}")

                # --- DECISION TIME ---
                winner = find_best_match(clean_text)

                if winner == "STOP":
                    print(">>> ACTION: STOP")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'N')

                elif winner == "IMITATE":
                    print(">>> ACTION: IMITATE")
                    CURRENT_MODE = "IMITATE"

                elif winner == "HAPPY":
                    print(">>> ACTION: FORCE HAPPY")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'H')

                elif winner == "SAD":
                    print(">>> ACTION: FORCE SAD")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'S')

                elif winner == "ANGRY":
                    print(">>> ACTION: FORCE ANGRY")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'A')

                elif winner == "RIGHT":
                    print(">>> ACTION: LOOK RIGHT")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'R')

                elif winner == "LEFT":
                    print(">>> ACTION: LOOK LEFT")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'L')

                elif winner == "MIDDLE":
                    print(">>> ACTION: LOOK MIDDLE")
                    CURRENT_MODE = "IDLE"
                    send_raw_command(b'M')

            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print("[NET] Google API unreachable")

        except Exception:
            pass

        # =========================================================


# 4) VISION LOGIC (Unchanged)
# =========================================================
_orig_load = _serialization.load


def _load_cpu(f, map_location=None, pickle_module=pickle, **kwargs):
    if map_location is None: map_location = "cpu"
    return _orig_load(f, map_location=map_location, pickle_module=pickle, **kwargs)


RAW_EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
GROUPED_MAP = {
    "happy": "Happy", "surprise": "Happy",
    "sad": "Sad", "neutral": "Sad",
    "angry": "Angry", "disgust": "Angry", "fear": "Angry",
}

HISTORY_WINDOW_SEC = 2.0
MIN_FRAMES = 6
MIN_DOMINANCE = 0.70
MIN_MARGIN = 2
ANGRY_MIN_DOMINANCE = 0.65
MIN_STATE_DURATION = 2.0
SAD_ANGRY_PENALTY = 0.15

EMOTION_HISTORY = []
STABLE_STATE = None
LAST_STATE_TIME = 0.0
_orig_putText = cv2.putText
_orig_rect = cv2.rectangle


def update_state(now):
    global STABLE_STATE, LAST_STATE_TIME, EMOTION_HISTORY
    EMOTION_HISTORY = [(t, e) for (t, e) in EMOTION_HISTORY if now - t <= HISTORY_WINDOW_SEC]
    if len(EMOTION_HISTORY) < MIN_FRAMES: return
    counts = Counter(e for _, e in EMOTION_HISTORY)
    top, top_count = counts.most_common(1)[0]
    second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
    dominance = top_count / sum(counts.values())
    margin = top_count - second_count

    if dominance < MIN_DOMINANCE: return
    if margin < MIN_MARGIN: return
    if top == "Angry" and dominance < ANGRY_MIN_DOMINANCE: return
    if STABLE_STATE is not None:
        if now - LAST_STATE_TIME < MIN_STATE_DURATION: return
    if STABLE_STATE in ("Sad", "Angry") and top in ("Sad", "Angry"):
        if dominance < MIN_DOMINANCE + SAD_ANGRY_PENALTY: return

    if top != STABLE_STATE:
        STABLE_STATE = top
        LAST_STATE_TIME = now
        send_state_to_arduino(STABLE_STATE)


def putText_hook(*args, **kwargs):
    text = kwargs.get('text')
    if text is None and len(args) > 1: text = args[1]
    if text:
        lower = str(text).lower()
        now = time.time()
        for raw in RAW_EMOTIONS:
            if raw in lower:
                grouped = GROUPED_MAP.get(raw)
                if grouped:
                    EMOTION_HISTORY.append((now, grouped))
                    update_state(now)
                break
    return _orig_putText(*args, **kwargs)


def rectangle_hook(img, *args, **kwargs): return img


# =========================================================
# 5) MAIN
# =========================================================
def main():
    global stop_threads

    # 1. Start Fast Audio
    audio_thread = threading.Thread(target=audio_listener_thread)
    audio_thread.daemon = True
    audio_thread.start()

    # 2. Wait then Apply CPU Hack
    time.sleep(3)
    print("[SYSTEM] Applying CPU Hack for Vision...")
    _serialization.load = _load_cpu
    torch.load = _load_cpu

    # 3. Start Vision
    er = EmotionRecognition(device="cpu")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cv2.putText = putText_hook
    cv2.rectangle = rectangle_hook

    last_inference = 0.0
    smoothed_box = None
    SMOOTH_ALPHA = 0.7

    print("System ready. Commands: Imitate, Stop, Happy, Sad, Angry, Left, Right, Middle.")

    while True:
        ok, frame = cap.read()
        if not ok: continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(60, 60))

        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            if smoothed_box is None:
                smoothed_box = [x, y, w, h]
            else:
                sx, sy, sw, sh = smoothed_box
                smoothed_box = [
                    SMOOTH_ALPHA * sx + (1 - SMOOTH_ALPHA) * x,
                    SMOOTH_ALPHA * sy + (1 - SMOOTH_ALPHA) * y,
                    SMOOTH_ALPHA * sw + (1 - SMOOTH_ALPHA) * w,
                    SMOOTH_ALPHA * sh + (1 - SMOOTH_ALPHA) * h,
                ]

        display = frame.copy()
        now = time.time()

        if now - last_inference > 0.12:
            er.recognise_emotion(display, return_type="BGR")
            last_inference = now

        if smoothed_box:
            x, y, w, h = map(int, smoothed_box)
            _orig_rect(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"{STABLE_STATE if STABLE_STATE else '...'}"
            _orig_putText(display, label, (x, max(0, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        color = (0, 255, 0) if CURRENT_MODE == "IMITATE" else (0, 0, 255)
        _orig_putText(display, f"MODE: {CURRENT_MODE}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.imshow("Robot Vision", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stop_threads = True
    cap.release()
    cv2.destroyAllWindows()
    if arduino: arduino.close()


if __name__ == "__main__":
    main()