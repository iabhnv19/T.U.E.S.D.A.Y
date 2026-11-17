import os
import re
import queue
import tempfile
import threading
from typing import Optional, Callable

import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import pygame

from core.config import Config


class VoiceEngine:
    """Handles text-to-speech and speech-to-text with bilingual Hinglish and Real-Time Streaming TTS."""

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

        # Streaming TTS sentence queue
        self._sentence_queue: queue.Queue = queue.Queue()
        self._is_streaming: bool = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_busy: bool = False

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
        self._is_streaming = False

        # Drain pending sentences
        try:
            while not self._sentence_queue.empty():
                self._sentence_queue.get_nowait()
                self._sentence_queue.task_done()
        except Exception:
            pass

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

    def _synthesize_audio_file(self, text: str, output_path: str) -> bool:
        """Synthesize text to MP3 using edge-tts (primary) or gTTS (fallback)."""
        clean = text.strip()
        if not clean:
            return False

        # 1. Edge-TTS High-Definition Neural Voice (Fastest & Most Natural)
        try:
            import asyncio
            import edge_tts
            voice = Config.EDGE_VOICE_HI if self._has_hindi_or_hinglish(clean) else Config.EDGE_VOICE_EN

            async def _run():
                comm = edge_tts.Communicate(clean, voice, rate="+12%")
                await comm.save(output_path)

            asyncio.run(_run())
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception:
            pass

        # 2. gTTS Online Fallback
        try:
            if self._has_hindi_or_hinglish(clean):
                tts = gTTS(text=clean, lang="hi", slow=False)
            else:
                tts = gTTS(text=clean, lang="en", tld="co.in", slow=False)
            tts.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception:
            pass

        return False

    def _speak_phrase(self, text: str):
        """Speak a single phrase/sentence synchronously."""
        if not text or not text.strip():
            return
        if self._stop_speaking_flag:
            return

        clean = text.strip()

        if self._pygame_ready:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                    temp_path = fp.name

                success = self._synthesize_audio_file(clean, temp_path)
                if success and not self._stop_speaking_flag:
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if self._stop_speaking_flag:
                            pygame.mixer.music.stop()
                            break
                        pygame.time.Clock().tick(50)
                    pygame.mixer.music.unload()
                    return
            except Exception:
                pass
            finally:
                if temp_path:
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        # 3. Offline SAPI5 Fallback
        if not self._stop_speaking_flag:
            try:
                self.offline_engine.say(clean)
                self.offline_engine.runAndWait()
            except Exception:
                pass

    def speak(self, text: str):
        """Speak full text aloud using neural Edge-TTS with online/offline fallbacks."""
        if not text:
            return
        self._stop_speaking_flag = False
        self._speak_phrase(text)

    # ── Real-Time Streaming TTS ──────────────────────────────────────────────

    def start_speech_stream(self):
        """Initialize the real-time sentence streaming queue and playback worker."""
        self._stop_speaking_flag = False
        self._is_streaming = True
        self._sentence_queue = queue.Queue()

        self._stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
        self._stream_thread.start()

    def speak_stream_chunk(self, sentence: str):
        """Enqueue a newly completed sentence from the LLM for immediate speech synthesis."""
        if not sentence or not sentence.strip() or self._stop_speaking_flag:
            return
        if not self._is_streaming:
            self.start_speech_stream()
        self._sentence_queue.put(sentence.strip())

    def finish_speech_stream(self, wait: bool = True):
        """Mark end of streaming input and wait for queued audio playback to complete."""
        if not self._is_streaming:
            return
        self._sentence_queue.put(None)  # Sentinel to stop worker
        if wait and self._stream_thread and self._stream_thread.is_alive():
            while self._stream_thread.is_alive():
                if self._stop_speaking_flag:
                    break
                self._stream_thread.join(timeout=0.1)

    def _stream_worker(self):
        """Worker thread that continuously pulls sentences and plays them sequentially."""
        while self._is_streaming and not self._stop_speaking_flag:
            try:
                sentence = self._sentence_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if sentence is None:  # Stream finished
                self._sentence_queue.task_done()
                break

            if self._stop_speaking_flag:
                self._sentence_queue.task_done()
                break

            self._stream_busy = True
            try:
                self._speak_phrase(sentence)
            finally:
                self._stream_busy = False
                self._sentence_queue.task_done()

        self._is_streaming = False

    @property
    def is_speaking(self) -> bool:
        """Returns True if audio is actively playing or streaming."""
        if self._pygame_ready and pygame.mixer.music.get_busy():
            return True
        return self._stream_busy or not self._sentence_queue.empty()

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
