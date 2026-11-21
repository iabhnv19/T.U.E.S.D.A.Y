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
        self.recognizer.energy_threshold = 250
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 1.2  # 1.2s prevents premature cutoff on natural pauses
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.6
        self._is_listening = False
        self._stop_speaking_flag = False
        self._calibrated = False

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

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Strip markdown markers, asterisks, and pronounce acronyms properly for TTS."""
        if not text:
            return ""
        c = text
        # Strip code blocks
        c = re.sub(r"```[\s\S]*?```", "", c)
        # Strip markdown bold, italics, inline code, headers, bullets, strikethrough
        c = re.sub(r"\*\*([^*]+)\*\*", r"\1", c)  # **text** -> text
        c = re.sub(r"\*([^*]+)\*", r"\1", c)      # *text* -> text
        c = re.sub(r"__([^_]+)__", r"\1", c)
        c = re.sub(r"_([^_]+)_", r"\1", c)
        c = re.sub(r"`([^`]+)`", r"\1", c)
        c = re.sub(r"~~([^~]+)~~", r"\1", c)
        c = re.sub(r"[*_~#`>]", "", c)            # Stray asterisks or markdown symbols
        # Pronounce T.U.E.S.D.A.Y cleanly as "Tuesday"
        c = re.sub(r"\bT\.?U\.?E\.?S\.?D\.?A\.?Y\.?\b", "Tuesday", c, flags=re.IGNORECASE)
        # Remove emojis
        c = re.sub(r'[\U00010000-\U0010ffff]', '', c)
        c = re.sub(r'[\u2600-\u27BF]', '', c)
        c = re.sub(r'[\uD83C-\uDBFF\uDC00-\uDFFF]', '', c)
        # Compress excessive dots / commas
        c = re.sub(r'\.{2,}', '.', c)
        c = re.sub(r'--+', '-', c)
        c = re.sub(r'[,;]{2,}', ',', c)
        return c.strip()

    def _speak_phrase(self, text: str):
        """Speak a single phrase/sentence synchronously."""
        if not text or not text.strip():
            return
        if self._stop_speaking_flag:
            return

        clean = self._clean_for_tts(text)
        if not clean:
            return

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
        clean = self._clean_for_tts(sentence)
        if not clean or self._stop_speaking_flag:
            return
        if not self._is_streaming:
            self.start_speech_stream()
        self._sentence_queue.put(clean)

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
                # Calibrate once on startup instead of every turn to prevent user speech from inflating noise floor
                if not self._calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    if self.recognizer.energy_threshold > 400:
                        self.recognizer.energy_threshold = 280
                    elif self.recognizer.energy_threshold < 150:
                        self.recognizer.energy_threshold = 200
                    self._calibrated = True

                if on_partial:
                    on_partial("Listening...")

                # phrase_time_limit=12.0 gives ample time for complete thoughts without word trimming
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=12.0)

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
