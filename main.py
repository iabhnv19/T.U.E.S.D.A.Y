import sys
import threading
import time
import os

# Suppress Qt font enumeration warnings on Windows
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false;qt.qpa.*=false"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from core.config import Config
from core.brain import AIBrain
from core.voice import VoiceEngine
from core.scheduler import BackgroundScheduler
from modules.pc_control import PCController
from modules.utilities import Utilities
from modules.overlay import DynamicIsland, TrayIcon
from modules.command_parser import CommandParser


TUESDAY_ASCII_BANNER = r"""
                              *$:::::::::::::::::::::::::::::::::::::$$$$$$:::***$$:
             :***%%%%###################%$$$$$$  ::::::::: :::   ::$$$$%####@@@@@@@@#@@@@@@@#####%%**
         :*%#@@@@####%%%%%%%%%%%%%%%%%%####@@@#%                 %#@@@@###%%%%%%%%%%%%%%%%%%%%%###@@@@%**:
      *%*%@@#$*:                            *%@@#              :#@@%*:                             *$@@#***:
    :%% *@@*  $                               *@@#:$$*$$$$$$$$*#@@*                                $ :@@% :$*:
   *%$* #@#     $                              *@@$$$::    $$$%@@*                                $   %@@**$$$:
   $$$$$#@%      $                             *@@$           $@@*                               $    *@#$$$$$:
    $$$$%@%       $$                           %@#            *@@#                              $     *@@$
       *@@%         $                         :@@% $*         *%@@*                           $$$     *@@*
       :@@#         $                         %@@$$$          :$#@#                           $$      *@@*
        #@@:       ::                        *@@$$$             $@@%                                  #@#
        *@@%                                *@@$$                $@@%                                *@@%
         %@@:                              :#@#                   %@@*                               %@@:
         :@@#                             *#@#:                    %@@*                             *@@%
          *@@%                           *@@%:                      %@@%:                          *@@%
           *@@#*                       *#@@$                         *@@@%:                     :*#@@#
            *%@@#%%****::  :::::***%%%#@@%*                           :%@@@#%%****:::::::****%%##@@#*
              :*%##@@@@@@@@@@@@@@@@@##%*:                                *%##@@@@@@@@@@@@@@@@@##%%*:::
              ::::**********************::                           :::::::***************:::::
"""


class Tuesday:
    """Core orchestrator tying together voice, PC control, Groq brain, and overlay."""

    def __init__(self):
        print("\033[96m" + TUESDAY_ASCII_BANNER + "\033[0m")
        print("  " + "═" * 70)
        print("   T.U.E.S.D.A.Y  —  Tactical Unified Electronic Systematic Digital Assistant")
        print("  " + "═" * 70 + "\n")

        print("  [1/5] Initializing AI brain...")
        self.brain = AIBrain()

        print("  [2/5] Setting up voice engine...")
        self.voice = VoiceEngine()

        print("  [3/5] Loading PC controller...")
        self.pc = PCController()

        print("  [4/5] Preparing utilities...")
        self.utils = Utilities()
        self.utils.set_timer_callback(self._on_timer_fire)

        print("  [5/5] Building command parser...")
        self.parser = CommandParser(self.pc, self.utils, self.brain)

        self.scheduler = BackgroundScheduler()
        self.scheduler.register_callback(self._on_reminder_fire)

        self._is_active = False
        self._running = True

    def run(self, app: QApplication, overlay: DynamicIsland):
        """Register hotkey, start system tray, and show startup state."""
        self.app = app
        self.overlay = overlay

        self._register_hotkey()

        self.tray = TrayIcon(
            on_quit=self._quit,
            on_toggle=self._toggle_active_mode,
        )
        self.tray.start()

        greeting = f"{Config.NAME} online. All systems operational."
        print(f"\n  ✓ {greeting}")
        print(f"  ✓ Press [{Config.HOTKEY_MODIFIER} + {Config.HOTKEY_KEY}] for Active Mode\n")

        self.scheduler.start()
        # Launch initial startup briefing check in background thread
        threading.Thread(target=self._run_startup_sequence, daemon=True).start()

    def _run_startup_sequence(self):
        """Initial run startup prompt: greets user as Sir and asks if they want a quick daily briefing."""
        time.sleep(0.5)
        startup_prompt = "Tuesday online. Would you like to begin your session with a quick briefing, Sir?"
        print(f"  [{Config.NAME}] 🎙️ {startup_prompt}")
        self.overlay.show_status("speaking", startup_prompt)
        self.voice.speak(startup_prompt)

        self.overlay.update_status("listening", "Listening for reply...")
        user_answer = self.voice.listen(timeout=4.5)

        if user_answer:
            ans = user_answer.strip().lower()
            print(f"  You: {ans}")
            affirmative_words = ["yes", "haan", "sure", "briefing", "chalo", "kar do", "batao", "yeah", "yep", "ha", "bilkul", "start", "ok", "okay"]
            if any(w in ans for w in affirmative_words):
                self.overlay.update_status("thinking", "Preparing daily briefing...")
                self.voice.speak("Preparing your briefing now, Sir.")
                try:
                    from modules.productivity_tools import get_daily_briefing
                    briefing = get_daily_briefing()
                    print(f"  [{Config.NAME}] Daily Briefing:\n{briefing}")
                    self.overlay.update_status("speaking", "Delivering Daily Briefing...")
                    self.voice.speak(briefing)
                except Exception as e:
                    print(f"  [ERROR] Daily briefing error: {e}")

                self.overlay.show_status("sleeping", "Standing by", auto_hide_ms=2000)
                self.voice.speak("Standing by, Sir. Press Right Shift + Enter whenever needed.")
                return

        # If user said no, or silence/timeout:
        self.overlay.show_status("sleeping", "Standing by", auto_hide_ms=2000)
        self.voice.speak("Standing by, Sir.")

    def _register_hotkey(self):
        """Global toggle hotkey (Right Shift + Enter)."""
        import keyboard

        hotkey_combo = f"{Config.HOTKEY_MODIFIER}+{Config.HOTKEY_KEY}"

        def on_hotkey():
            if not self._is_active:
                thread = threading.Thread(target=self._run_active_session, daemon=True)
                thread.start()
            else:
                self._is_active = False

        keyboard.add_hotkey(hotkey_combo, on_hotkey, suppress=True)
        print(f"  ✓ Hotkey registered: {hotkey_combo}")

    def _toggle_active_mode(self):
        """Toggle active listening from system tray."""
        if self._is_active:
            self._is_active = False
        else:
            thread = threading.Thread(target=self._run_active_session, daemon=True)
            thread.start()

    def _run_active_session(self):
        """Active listening loop: stays open until 5 seconds of silence."""
        if self._is_active:
            return
        self._is_active = True

        print(f"\n  [{Config.NAME}] 🎙️ Active Mode engaged — listening continuously...")
        self.overlay.show_status("listening", "Listening...")

        silence_count = 0

        try:
            while self._is_active and self._running:
                self.overlay.update_status("listening", "Listening...")

                user_input = self.voice.listen(
                    timeout=5.0,
                    on_partial=lambda s: self.overlay.update_status(s.lower(), s),
                )

                if not user_input:
                    silence_count += 1
                    if silence_count >= 1:
                        print(f"  [{Config.NAME}] Silence detected. Going to sleep.")
                        self.overlay.show_status("sleeping", "Going to sleep...", auto_hide_ms=1200)
                        break
                    continue

                silence_count = 0
                user_input = user_input.strip()
                print(f"  You: {user_input}")

                if any(x in user_input.lower() for x in ["go to sleep", "sleep now", "so jao", "bye tuesday", "stop listening"]):
                    response = "Standing by boss. Call me when needed."
                    print(f"  {Config.NAME}: {response}")
                    self.overlay.update_status("speaking", response)
                    self.voice.speak(response)
                    self.overlay.show_status("sleeping", "Asleep", auto_hide_ms=1500)
                    break

                self.overlay.update_status("thinking", f'"{user_input}"')

                # Check local fast-path commands first
                direct_result = self.parser.try_parse(user_input)

                if direct_result:
                    response = direct_result
                    print(f"  {Config.NAME} [local]: {response}")
                    interrupted_text = self._speak_with_bargein(response)
                else:
                    # Pass through to Groq agentic brain with Real-Time Streaming TTS
                    self.voice.start_speech_stream()

                    def _on_chunk(sentence_chunk: str):
                        self.overlay.update_status("speaking", sentence_chunk)
                        self.voice.speak_stream_chunk(sentence_chunk)

                    response = self.brain.think(
                        user_input,
                        on_status=lambda s: self.overlay.update_status("thinking", s),
                        on_sentence=_on_chunk,
                    )
                    print(f"  {Config.NAME}: {response}")
                    self.voice.finish_speech_stream(wait=False)

                    # Monitor for real-time barge-in while streaming sentences finish playing
                    interrupted_text = self._wait_for_speech_with_bargein()

                if interrupted_text:
                    print(f"  You (Interrupted): {interrupted_text}")
                    user_input = interrupted_text
                    continue

                time.sleep(0.2)

        except Exception as e:
            print(f"  [ERROR] {e}")
            self.overlay.show_status("error", f"Error: {str(e)[:45]}", auto_hide_ms=2500)
        finally:
            self._is_active = False
            time.sleep(0.5)
            self.overlay.hide_bar()
            print(f"  [{Config.NAME}] 💤 Sleep mode. Press Right Shift + Enter to wake.")

    def _wait_for_speech_with_bargein(self):
        """Monitors mic while streaming sentences finish playing out loud."""
        import speech_recognition as sr
        try:
            with sr.Microphone() as source:
                while self.voice.is_speaking:
                    try:
                        self.voice.recognizer.energy_threshold = 450
                        audio = self.voice.recognizer.listen(source, timeout=0.4, phrase_time_limit=4.0)

                        heard = self.voice.recognizer.recognize_google(
                            audio, language=Config.VOICE_LANGUAGE
                        ).strip().lower()

                        is_targeted_stop = any(k in heard for k in [
                            "tuesday stop", "tuesday chup", "tuesday ruko", "tuesday sun",
                            "tuesday meri baat", "stop tuesday", "chup ho jao"
                        ])
                        is_new_tuesday_query = heard.startswith("tuesday") or "tuesday " in heard
                        is_urgent_stop = heard in ["stop", "ruko", "chup", "shant"]

                        if is_targeted_stop or is_new_tuesday_query or is_urgent_stop:
                            print(f"\n  [{Config.NAME}] 🛑 Intentional interruption detected: '{heard}'")
                            self.voice.stop_speaking()

                            if (is_targeted_stop or is_urgent_stop) and len(heard.split()) <= 2:
                                return "Standing by."

                            clean_query = heard.replace("tuesday", "").strip()
                            return clean_query or heard
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            self.voice.recognizer.energy_threshold = 300

        return None

    def _speak_with_bargein(self, response: str):
        """Speaks in a background thread while monitoring mic for intentional interruption."""
        import speech_recognition as sr

        self.overlay.update_status("speaking", response)
        speak_thread = threading.Thread(target=self.voice.speak, args=(response,), daemon=True)
        speak_thread.start()

        try:
            with sr.Microphone() as source:
                while speak_thread.is_alive():
                    try:
                        self.voice.recognizer.energy_threshold = 450
                        audio = self.voice.recognizer.listen(source, timeout=0.5, phrase_time_limit=4.0)

                        heard = self.voice.recognizer.recognize_google(
                            audio, language=Config.VOICE_LANGUAGE
                        ).strip().lower()

                        is_targeted_stop = any(k in heard for k in [
                            "tuesday stop", "tuesday chup", "tuesday ruko", "tuesday sun",
                            "tuesday meri baat", "stop tuesday", "chup ho jao"
                        ])
                        is_new_tuesday_query = heard.startswith("tuesday") or "tuesday " in heard
                        is_urgent_stop = heard in ["stop", "ruko", "chup", "shant"]

                        if is_targeted_stop or is_new_tuesday_query or is_urgent_stop:
                            print(f"\n  [{Config.NAME}] 🛑 Intentional interruption detected: '{heard}'")
                            self.voice.stop_speaking()
                            speak_thread.join(timeout=0.6)

                            if (is_targeted_stop or is_urgent_stop) and len(heard.split()) <= 2:
                                return "Standing by."

                            clean_query = heard.replace("tuesday", "").strip()
                            return clean_query or heard
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        continue
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            self.voice.recognizer.energy_threshold = 300

        speak_thread.join()
        return None

    def _on_timer_fire(self, message: str):
        """Handle background timer callback."""
        print(f"  {Config.NAME}: {message}")
        self.overlay.show_status("ready", message, auto_hide_ms=4000)
        self.voice.speak_async(message)

    def _on_reminder_fire(self, title: str, recurring: str):
        """Handle due persistent reminder from background scheduler."""
        msg = f"Reminder: {title}"
        print(f"\n[Scheduler] ⏰ {msg}")
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.show_status("alert", f"⏰ {msg}", auto_hide_ms=6000)
        rec_tag = " (Daily)" if recurring == "daily" else (" (Weekly)" if recurring == "weekly" else "")
        self.voice.speak_async(f"Sir, aapka reminder hai: {title}{rec_tag}")

    def _quit(self):
        """Clean shutdown."""
        self._running = False
        self._is_active = False
        self.scheduler.stop()
        self.voice.speak("Shutting down. Goodbye.")
        print(f"\n  {Config.NAME} shutting down...")
        self.tray.stop()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = DynamicIsland()
    tuesday = Tuesday()
    tuesday.run(app, overlay)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
