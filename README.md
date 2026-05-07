# YouTube Music Lyrics Player

A Python application that connects to YouTube Music, fetches song lyrics from Genius, displays them with timing delays, and uses text-to-speech to "sing" the lyrics through your speakers.

## Features

- 🔍 Search songs on YouTube Music
- 📝 Fetch lyrics from Genius
- 🔤 Transliterate Hindi lyrics to Hinglish automatically
- 🌐 Open the song in your browser for real audio playback
- ⏱️ Display lyrics with realistic timing
- 🗣️ Text-to-speech "singing" through speakers
- 🎵 Interactive command-line interface

## Prerequisites

- Python 3.7+
- Genius API access token
- (Optional) YouTube Data API key for enhanced features

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

### 1. Genius API Token (Required for lyrics)

1. Go to [Genius API Clients](https://genius.com/api-clients)
2. Create a new API client
3. Copy your access token

### 2. Configuration

The app supports both `config.json` and `.env`. Use `config.json` for values that you want to manage in one place.

1. Copy `config.example.json` to `config.json`.
2. Update `config.json` with your tokens and delay settings.

Example `config.json`:

```json
{
  "genius_token": "your_genius_access_token_here",
  "youtube_api_key": "your_youtube_api_key_here",
  "lyrics_delay_multiplier": 1.0,
  "min_line_delay": 1.5,
  "max_line_delay": 5.0,
  "tts_rate": 180,
  "tts_volume": 0.8,
  "auto_open_browser": true
}
```

You can still use `.env` instead if you prefer:

```env
GENIUS_ACCESS_TOKEN=your_genius_token_here
YOUTUBE_API_KEY=your_youtube_api_key_here
```

## Usage

Activate the project virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then run the application:

```bash
python main.py
```

If you are not using the workspace virtual environment, use the full interpreter path:

```powershell
.\.venv\Scripts\python.exe main.py
```

Enter song names when prompted. The application will:
1. Search for the song on YouTube Music
2. Fetch lyrics from Genius
3. Display lyrics line by line with timing
4. Use text-to-speech to "sing" each line

Type `quit` or press Ctrl+C to exit.

## Example

```
🎵 YouTube Music Lyrics Player 🎵
========================================
🎵 Enter song name (or 'quit' to exit): Bohemian Rhapsody

🔍 Searching for: Bohemian Rhapsody
✅ Found: Bohemian Rhapsody by Queen
📝 Found 45 lines of lyrics.

🎵 Starting lyrics playback...

🎤 Is this the real life?
🎤 Is this just fantasy?
🎤 Caught in a landslide,
🎤 No escape from reality.
...
```

## Dependencies

- `ytmusicapi`: YouTube Music API client
- `lyricsgenius`: Genius lyrics API client
- `pyttsx3`: Text-to-speech engine
- `google-api-python-client`: YouTube Data API (optional)
- `python-dotenv`: Environment variable management

## Troubleshooting

### No lyrics found
- Ensure your Genius access token is valid
- Some songs may not have lyrics available on Genius
- Check your internet connection

### TTS not working
- Install additional TTS engines if needed (pyttsx3 uses system TTS)
- On Windows: Ensure Windows TTS is enabled
- On Linux: Install `espeak` or `festival`

### YouTube Music search fails
- Check your internet connection
- YouTube Music API may have rate limits

## License

This project is open source. Feel free to modify and distribute.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
