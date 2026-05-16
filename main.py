#!/usr/bin/env python3
"""
YouTube Music Lyrics Player
A Python application that connects to YouTube Music, fetches lyrics,
displays them with timing, and uses text-to-speech to "sing" songs.
"""

import time
import sys
import os
import re
import json
import webbrowser
from typing import Optional, List, Tuple

from dotenv import load_dotenv, find_dotenv

try:
    import yaml
except ImportError:
    yaml = None

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print('Warning: no .env file found; using environment variables only.')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')
DEFAULT_CONFIG = {
    'genius_token': '',
    'youtube_api_key': '',
    'lyrics_delay_multiplier': 3.25,
    'auto_calculate_delay': True,
    'word_delay':1.15,
    'min_word_delay': 0.08,
    'max_word_delay': 1.25,
    'browser_start_delay': 4.0,
    'tts_enabled': False,
    'min_line_delay': 1.5,
    'max_line_delay': 5.0,
    'tts_rate': 180,
    'tts_volume': 0.8,
    'auto_open_browser': True
}

DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')

VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ii', 'उ': 'u', 'ऊ': 'uu',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
}
CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
}
MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ii', 'ु': 'u', 'ू': 'uu', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ः': 'h'
}
VIRAMA = '्'


def load_yaml_config() -> dict:
    if os.path.exists(CONFIG_FILE) and yaml:
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
                return {**DEFAULT_CONFIG, **yaml.safe_load(file)}
        except Exception as e:
            print(f'Warning: could not read config.yaml: {e}')
    elif os.path.exists(CONFIG_FILE):
        print('Warning: PyYAML is not installed; cannot read config.yaml.')
    return DEFAULT_CONFIG.copy()


CONFIG = load_yaml_config()


def get_config_value(key: str, default=None):
    env_key = key.upper()
    env_value = os.getenv(env_key)
    if env_value is not None:
        if isinstance(default, bool):
            return env_value.lower() in ('1', 'true', 'yes', 'on')
        if isinstance(default, float):
            try:
                return float(env_value)
            except ValueError:
                return default
        if isinstance(default, int):
            try:
                return int(env_value)
            except ValueError:
                return default
        return env_value
    return CONFIG.get(key, default)


def parse_duration(duration: str) -> Optional[int]:
    if not duration:
        return None
    if isinstance(duration, (int, float)):
        return int(duration)
    parts = duration.split(':')
    try:
        parts = [int(p.strip()) for p in parts if p.strip()]
    except ValueError:
        return None
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def is_bgm_line(line: str) -> bool:
    normalized = line.strip().lower()
    if not normalized:
        return False
    if normalized.startswith('[') and normalized.endswith(']'):
        return True
    if any(keyword in normalized for keyword in ['instrumental', 'intro', 'outro', 'interlude', 'music', 'background']):
        return True
    words = [w.strip('.,!?;"\'') for w in normalized.split() if w.strip('.,!?;"\'')]
    if words and all(w in {'la', 'na', 'oh', 'hey', 'woo', 'ya', 'aah', 'ohh', 'ah', 'ooh', 'hey', 'ho', 'uh', 'yeah'} for w in words):
        return True
    return False


def calculate_word_delay(lyrics: str, song_info: dict, delay_multiplier: float, default_delay: float,
                         min_delay: float, max_delay: float, auto_calc: bool,
                         analysis: Optional[dict] = None) -> float:
    words = []
    for line in lyrics.split('\n'):
        if is_bgm_line(line):
            continue
        words.extend([w for w in line.split() if w])

    if analysis:
        recommended = analysis.get('recommended_word_delay')
        if recommended is not None:
            try:
                delay = float(recommended) * delay_multiplier
                return max(min_delay, min(max_delay, delay))
            except (ValueError, TypeError):
                pass

    if auto_calc:
        duration_source = song_info.get('duration_seconds') or song_info.get('duration')
        duration = parse_duration(duration_source)
        if duration and duration > 0 and words:
            base_delay = duration / len(words)
            delay = base_delay * 0.95 * delay_multiplier
            return max(min_delay, min(max_delay, delay))

    manual_delay = default_delay * delay_multiplier
    return max(min_delay, min(max_delay, manual_delay))


def analyze_lyrics_for_timing(song_info: dict, lyrics: str) -> dict:
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    content_lines = [line for line in lines if not is_bgm_line(line)]
    if not content_lines:
        return {'recommended_word_delay': None, 'timing_notes': 'No lyric lines found for analysis.'}

    total_words = sum(len(line.split()) for line in content_lines)
    duration_source = song_info.get('duration_seconds') or song_info.get('duration')
    duration = parse_duration(duration_source)
    if duration and duration > 0 and total_words:
        base_delay = duration / total_words
    else:
        base_delay = None

    punctuation_count = sum(line.count(',') + line.count('.') + line.count('!') + line.count('?') for line in content_lines)
    line_density = total_words / max(1, len(content_lines))
    repeated_lines = len([line for line in content_lines if content_lines.count(line) > 1])
    smooth_factor = 1.0 + min(0.25, punctuation_count / max(1, len(content_lines)) * 0.04)
    repeat_factor = 1.0 + min(0.2, repeated_lines / max(1, len(content_lines)) * 0.05)

    if base_delay:
        recommended = base_delay * smooth_factor * repeat_factor
    else:
        recommended = None

    if recommended is not None:
        note_parts = [
            f"Derived from {total_words} words over {duration_source or 'unknown duration'}.",
            f"Detected average line density {line_density:.1f} words/line.",
        ]
        if punctuation_count > len(content_lines):
            note_parts.append("Punctuation-heavy lyrics slow timing slightly.")
        if repeated_lines:
            note_parts.append("Repeated lines may require a gentler pace.")
        timing_notes = ' '.join(note_parts)
    else:
        timing_notes = 'No duration available; using fallback delay.'

    has_bgm = any(is_bgm_line(line) for line in lines)

    return {
        'recommended_word_delay': round(recommended, 3) if recommended is not None else None,
        'timing_notes': timing_notes,
        'has_bgm': has_bgm,
        'bgm_sections': [line for line in lines if is_bgm_line(line)][:5]
    }


def contains_devanagari(text: str) -> bool:
    return bool(DEVANAGARI_PATTERN.search(text))


def transliterate_hinglish(text: str) -> str:
    output = []
    i = 0
    while i < len(text):
        char = text[i]
        if char in VOWELS:
            output.append(VOWELS[char])
        elif char in CONSONANTS:
            base = CONSONANTS[char]
            next_char = text[i + 1] if i + 1 < len(text) else ''
            if next_char == VIRAMA:
                output.append(base)
                i += 1
            elif next_char in MATRAS:
                output.append(base + MATRAS[next_char])
                i += 1
            else:
                output.append(base + 'a')
        elif char in MATRAS:
            output.append(MATRAS[char])
        elif char == VIRAMA:
            pass
        else:
            output.append(char)
        i += 1
    return ''.join(output)


# Third-party imports
try:
    from ytmusicapi import YTMusic
    import lyricsgenius
    try:
        import pyttsx3
    except ImportError:
        pyttsx3 = None
    try:
        from gtts import gTTS
        from playsound import playsound
    except ImportError:
        gTTS = None
        playsound = None
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"Missing dependencies. Please install required packages: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)


class YouTubeMusicLyricsPlayer:
    """Main class for YouTube Music lyrics player functionality."""

    def __init__(self):
        """Initialize the player with API clients."""
        self.ytmusic = YTMusic()

        self.genius_token = get_config_value('genius_token', '')
        if not self.genius_token:
            self.genius_token = os.getenv('GENIUS_ACCESS_TOKEN', '')

        if self.genius_token:
            try:
                self.genius = lyricsgenius.Genius(self.genius_token)
            except Exception as e:
                print(f"Warning: Genius client initialization failed: {e}")
                self.genius = None
        else:
            self.genius = None

        self.auto_open_browser = bool(get_config_value('auto_open_browser', True))
        self.delay_multiplier = float(get_config_value('lyrics_delay_multiplier', 1.0))
        self.auto_calculate_delay = bool(get_config_value('auto_calculate_delay', True))
        self.word_delay = float(get_config_value('word_delay', 0.12))
        self.min_word_delay = float(get_config_value('min_word_delay', 0.08))
        self.max_word_delay = float(get_config_value('max_word_delay', 0.45))
        self.browser_start_delay = float(get_config_value('browser_start_delay', 4.0))
        self.tts_enabled = bool(get_config_value('tts_enabled', False))
        self.min_line_delay = float(get_config_value('min_line_delay', 1.5))
        self.max_line_delay = float(get_config_value('max_line_delay', 5.0))
        self.tts_rate = int(get_config_value('tts_rate', 180))
        self.tts_volume = float(get_config_value('tts_volume', 0.8))

        self.tts_engine = None
        self.use_pyttsx3 = False
        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.tts_rate)
                self.tts_engine.setProperty('volume', self.tts_volume)
                self.use_pyttsx3 = True
            except Exception as e:
                print(f"Warning: pyttsx3 initialization failed: {e}")
                self.tts_engine = None

        self.tts_fallback_available = bool(gTTS and playsound)
        if not self.tts_engine and not self.tts_fallback_available:
            print("Warning: No TTS engine available. Install pyttsx3 or gtts and playsound.")

        # YouTube API (optional, for additional features)
        self.youtube_api = None
        if os.getenv('YOUTUBE_API_KEY'):
            try:
                self.youtube_api = build('youtube', 'v3',
                                       developerKey=os.getenv('YOUTUBE_API_KEY'))
            except Exception as e:
                print(f"YouTube API initialization failed: {e}")

    def open_song_in_browser(self, video_id: str):
        """Open the found song video in the default browser."""
        try:
            url = f"https://music.youtube.com/watch?v={video_id}"
            print(f"🌐 Opening song in browser: {url}")
            webbrowser.open(url)
        except Exception as e:
            print(f"Warning: could not open browser for song playback: {e}")

    def search_song(self, song_name: str) -> Optional[dict]:
        """
        Search for a song on YouTube Music.

        Args:
            song_name: Name of the song to search for

        Returns:
            Song information dictionary or None if not found
        """
        try:
            search_results = self.ytmusic.search(song_name, filter='songs')
            if search_results:
                return search_results[0]  # Return first result
            return None
        except Exception as e:
            print(f"Error searching for song: {e}")
            return None

    def get_lyrics(self, song_title: str, artist: str) -> Optional[str]:
        """
        Fetch lyrics from Genius API.

        Args:
            song_title: Title of the song
            artist: Artist name

        Returns:
            Lyrics text or None if not found
        """
        try:
            if not self.genius:
                print("Warning: Genius access token not set. Lyrics may not be available.")
                return None

            song = self.genius.search_song(song_title, artist)
            if not song:
                return None

            lyrics = song.lyrics or ''
            lyrics = lyrics.strip()
            if contains_devanagari(lyrics):
                print("🔤 Hindi lyrics detected. Translating to Hinglish...")
                lyrics = transliterate_hinglish(lyrics)
            return lyrics
        except Exception as e:
            print(f"Error fetching lyrics: {e}")
            return None

    def parse_lyrics_with_timing(self, lyrics: str) -> List[List[str]]:
        """
        Parse lyrics into a list of word lists for each line.

        Args:
            lyrics: Raw lyrics text

        Returns:
            List of word list tuples for each line
        """
        lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
        parsed = []

        for line in lines:
            # Skip section headers like [Verse 1], [Chorus], etc.
            if line.startswith('[') and line.endswith(']'):
                continue

            words = line.split()
            if words:
                parsed.append(words)

        return parsed

    def format_highlighted_line(self, words: List[str], current_index: int) -> str:
        highlighted = []
        for idx, word in enumerate(words):
            if idx == current_index:
                highlighted.append(f"\033[1;32m{word}\033[0m")
            else:
                highlighted.append(word)
        return ' '.join(highlighted)

    def display_and_speak_lyrics(self, parsed_lyrics: List[List[str]], word_delay: float):
        """
        Display lyrics word-by-word with highlighting and speak them using TTS.

        Args:
            parsed_lyrics: List of word lists for each line
            word_delay: Delay between words in seconds
        """
        print("\n🎵 Starting lyrics playback...\n")

        for words in parsed_lyrics:
            line_text = ' '.join(words)
            if is_bgm_line(line_text):
                sys.stdout.write(f"\r\033[K🎵 music...")
                sys.stdout.flush()
                time.sleep(max(word_delay, 1.2))
                sys.stdout.write('\n')
                continue

            for idx, word in enumerate(words):
                display_text = self.format_highlighted_line(words, idx)
                sys.stdout.write(f"\r\033[K🎤 {display_text}")
                sys.stdout.flush()

                if self.tts_enabled:
                    self.speak_text(word)
                time.sleep(word_delay)

            sys.stdout.write('\n')

        print("\n🎵 Lyrics display complete! (Actual song may continue in the browser.)")

    def speak_text(self, text: str):
        """Speak a text line using the available TTS engine."""
        if self.use_pyttsx3 and self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return
            except Exception as e:
                print(f"Warning: pyttsx3 playback failed: {e}")

        if self.tts_fallback_available:
            try:
                temp_file = os.path.join(os.path.dirname(__file__), 'tts_temp.mp3')
                tts = gTTS(text=text, lang='en')
                tts.save(temp_file)
                playsound(temp_file)
                os.remove(temp_file)
                return
            except Exception as e:
                print(f"Warning: gTTS playback failed: {e}")

        print("⚠️  Audio playback unavailable for this line.")

    def play_song(self, song_name: str):
        """
        Main method to search for a song, get lyrics, and play them.

        Args:
            song_name: SAAWALI
        """
        print(f"🔍 Searching for: {song_name}")

        # Search for the song
        song_info = self.search_song(song_name)
        if not song_info:
            print("❌ Song not found on YouTube Music.")
            return

        print(f"✅ Found: {song_info['title']} by {song_info['artists'][0]['name']}")

        # Get lyrics
        artist = song_info['artists'][0]['name']
        lyrics = self.get_lyrics(song_info['title'], artist)

        if not lyrics:
            print("❌ Lyrics not found. You can still enjoy the music!")
            return

        # Open the song in the browser for actual music playback
        video_id = song_info.get('videoId')
        if video_id and self.auto_open_browser:
            self.open_song_in_browser(video_id)
            print(f"⏳ Waiting {self.browser_start_delay:.1f}s for browser playback to start...")
            time.sleep(self.browser_start_delay)
        elif video_id:
            print('ℹ️  Song found, but browser playback is disabled in config.')

        # Parse lyrics with timing
        parsed_lyrics = self.parse_lyrics_with_timing(lyrics)

        if not parsed_lyrics:
            print("❌ Could not parse lyrics.")
            return False

        analysis = analyze_lyrics_for_timing(song_info, lyrics)
        if analysis.get('timing_notes'):
            print(f"🧠 Timing notes: {analysis.get('timing_notes')}")
        if analysis.get('has_bgm'):
            print("⚠️  Possible BGM/section markers detected. Timing may vary.")

        word_delay = calculate_word_delay(
            lyrics,
            song_info,
            self.delay_multiplier,
            self.word_delay,
            self.min_word_delay,
            self.max_word_delay,
            self.auto_calculate_delay,
            analysis,
        )

        print(f"📝 Found {len(parsed_lyrics)} lines of lyrics.")
        print(f"⏱️  Using word delay: {word_delay:.2f}s")

        # Display and speak lyrics
        self.display_and_speak_lyrics(parsed_lyrics, word_delay)
        return True


def main():
    """Main entry point of the application."""
    load_dotenv()

    print("🎵 YouTube Music Lyrics Player 🎵")
    print("=" * 40)

    # Check for required configuration values
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN') or get_config_value('genius_token', '')
    if not genius_token:
        print("⚠️  Warning: Genius access token not set.")
        print("   Lyrics functionality will be limited.")
        print("   Add GENIUS_ACCESS_TOKEN to .env or genius_token to config.yaml")
        print()
    else:
        print("✅ Genius access token loaded.")
        print()

    youtube_api_key = os.getenv('YOUTUBE_API_KEY') or get_config_value('youtube_api_key', '')
    if not youtube_api_key:
        print("ℹ️  Note: YOUTUBE_API_KEY not set (optional).")
        print("   Some features may be limited.")
        print()

    # Initialize the player
    player = YouTubeMusicLyricsPlayer()

    # Main loop
    while True:
        try:
            # Get song name from user
            song_name = input("🎵 Enter song name (or 'quit' to exit): ").strip()

            if song_name.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if not song_name:
                continue

            # Play the song
            played = player.play_song(song_name)
            print()
            while played:
                action = input("Playback complete. [r]epeat / [n]ew song / [q]uit: ").strip().lower()
                if action in ['r', 'repeat']:
                    played = player.play_song(song_name)
                    print()
                    continue
                if action in ['q', 'quit', 'exit']:
                    print("👋 Goodbye!")
                    sys.exit(0)
                break

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print()


if __name__ == "__main__":
    main()