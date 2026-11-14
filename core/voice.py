import os
import re
import tempfile
import threading
from typing import Optional, Callable

import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import pygame

from core.config import Config


class VoiceEngine:
    """Handles text-to-speech and speech-to-text with bilingual Hinglish support."""

    def __init__(self):
        # Slightly higher frequency playback gives crisper, more natural pacing
        try:
            pygame.mixer.init(frequency=27500)
            self._pygame_ready = True
        except Exception:
            try:
                pygame.mixer.init()
                self._pygame_ready = True
            except Exception:
                self._pygame_ready = False

        self.offline_engine = pyttsx3.init()
        self._setup_fallback_voice()

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self._is_listening = False
        self._stop_speaking_flag = False

    def _setup_fallback_voice(self):
        """Configure local SAPI5 voice for offline situations."""
        try:
            voices = self.offline_engine.getProperty("voices")
            female_voice = None
            for voice in voices:
                v_name = voice.name.lower()
                if "zira" in v_name or "female" in v_name or "hazel" in v_name:
                    female_voice = voice
                    break

            if female_voice:
                self.offline_engine.setProperty("voice", female_voice.id)
            elif voices:
                self.offline_engine.setProperty("voice", voices[0].id)

            self.offline_engine.setProperty("rate", Config.VOICE_RATE)
            self.offline_engine.setProperty("volume", Config.VOICE_VOLUME)
        except Exception:
            pass

    def _has_hindi_or_hinglish(self, text: str) -> bool:
        """Heuristic check for Devanagari script or common Hinglish words."""
        if re.search(r"[\u0900-\u097F]", text):
            return True
        hinglish_markers = {
            "karo", "kardo", "karna", "nahi", "nahin", "hain", "hai", "kya", "bhai",
            "raha", "rahe", "khol", "kholo", "chalao", "band", "batao", "kaise", "thik",
            "acha", "achha", "shukriya", "dost", "kehti", "hota", "hoti", "aur", "toh",
            "mein", "yeh", "woh", "yaar"
        }
        words = set(re.findall(r"\w+", text.lower()))
        return bool(words.intersection(hinglish_markers))

    def stop_speaking(self):
        """Stops audio output immediately when barge-in is triggered."""
        self._stop_speaking_flag = True
        if self._pygame_ready:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
        try:
            self.offline_engine.stop()
        except Exception:
            pass

    def speak(self, text: str):
        """Speak text aloud using gTTS with offline pyttsx3 fallback."""
        if not text:
            return

        self._stop_speaking_flag = False
        cleaned_text = text.strip()

        # Primary online natural voice
        if self._pygame_ready:
            try:
                if self._has_hindi_or_hinglish(cleaned_text):
                    tts = gTTS(text=cleaned_text, lang="hi", slow=False)
                else:
                    tts = gTTS(text=cleaned_text, lang="en", tld="co.in", slow=False)

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                    temp_audio_path = fp.name

                tts.save(temp_audio_path)

                pygame.mixer.music.load(temp_audio_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if self._stop_speaking_flag:
                        pygame.mixer.music.stop()
                        break
                    pygame.time.Clock().tick(20)

                pygame.mixer.music.unload()
                try:
                    os.remove(temp_audio_path)
                except Exception:
                    pass
                return
            except Exception:
                # If network drops, fall back to offline engine
                pass

        # Offline fallback
        try:
            self.offline_engine.say(cleaned_text)
            self.offline_engine.runAndWait()
        except Exception:
            pass

    def speak_async(self, text: str):
        """Background thread wrapper for non-blocking voice output."""
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread

    def listen(self, timeout: float = 6.0, on_partial: Optional[Callable] = None) -> Optional[str]:
        """Captures mic input with en-IN primary and hi-IN secondary fallback."""
        self._is_listening = True
        result_text = None

        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)

                if on_partial:
                    on_partial("Listening...")

                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10.0)

                if on_partial:
                    on_partial("Processing...")

                # First try Indian English (handles code-mixed phonetics well)
                try:
                    result_text = self.recognizer.recognize_google(
                        audio,
                        language=Config.VOICE_LANGUAGE
                    )
                except sr.UnknownValueError:
                    # Retry with native Hindi language tag
                    try:
                        result_text = self.recognizer.recognize_google(audio, language="hi-IN")
                    except Exception:
                        pass

                if result_text:
                    result_text = result_text.strip()

        except (sr.WaitTimeoutError, sr.UnknownValueError):
            pass
        except sr.RequestError as e:
            print(f"[{Config.NAME}] Speech recognition service error: {e}")
        except Exception as e:
            print(f"[{Config.NAME}] Audio input error: {e}")
        finally:
            self._is_listening = False
        self._stop_speaking_flag = False

        return result_text

    def stop_listening(self):
        self._is_listening = False
        self._stop_speaking_flag = False

    @property
    def stt_available(self) -> bool:
        return True
