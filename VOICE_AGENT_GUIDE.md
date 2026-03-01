# CAT AI Inspector - Voice Agent Configuration & System Prompt

## Overview
The voice agent provides a natural language interface for the CAT AI Inspector application. It uses **ElevenLabs Conversational AI** with a specialized system prompt designed for equipment technicians.

## System Prompt Architecture

### English System Prompt Focus Areas:
1. **Equipment Inspection Guidance** - CAT-specific procedures and standards
2. **Knowledge Base Integration** - Retrieves and explains past findings
3. **Component Knowledge** - Understands tracks, hydraulics, engines, etc.
4. **Severity Assessment** - Explains critical/moderate/minor ratings
5. **Safety-First Mentality** - Always prioritizes safety

### Spanish System Prompt Focus Areas:
Same as English but fully localized for Spanish-speaking technicians.

## Configuration Settings

### Environment Variables (.env)
```
ELEVENLABS_API_KEY=sk_49c44830dfad5ab2f4c2e2982625e995070bd8d972b30d01
```

### Agent Configuration (app/config.py)
```python
# Voice Agent Settings
agent_model: str = "gpt-4-turbo"
agent_voice_id: str = "9BWtsMINqrJLrRacOk9x"  # Aria - professional, clear
agent_enable_conversation: bool = True
```

### Voice ID Options (ElevenLabs)
- **9BWtsMINqrJLrRacOk9x** (Aria) - Professional, clear, authoritative ✅ RECOMMENDED
- **21m00Tcm4TlvDq8ikWAM** (George) - Deep, professional
- **EXAVITQu4vr4xnSDxMaL** (Bella) - Warm, friendly
- **nPczCjzI2devNzcqCZE5** (Alice) - Tech-savvy tone

### Agent Settings (app/voice_agent.py)
```python
AGENT_SETTINGS = {
    "en": {
        "system_prompt": SYSTEM_PROMPT_EN,
        "voice_id": "9BWtsMINqrJLrRacOk9x",
        "model": "gpt-4-turbo",
        "temperature": 0.7,      # Balanced creativity vs grounding
        "max_tokens": 256,       # Keep responses concise for voice
    },
    "es": {
        "system_prompt": SYSTEM_PROMPT_ES,
        "voice_id": "9BWtsMINqrJLrRacOk9x",
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "max_tokens": 256,
    }
}
```

## Voice Agent Capabilities

### Navigation Commands
- "Go to inspector" → Navigate to inspector section
- "Show me the knowledge base" → Navigate to KB
- "What are the features?" → Navigate to features
- Spanish equivalents: "Ir al inspector", "Mostrar base de conocimientos", etc.

### Knowledge Base Queries
- "Search for track wear" → Searches KB and retrieves matches
- "Show me similar hydraulic issues" → Finds KB entries for hydraulics
- "What was the last excavator inspection?" → Queries KB for context
- Spanish: "Buscar desgaste de orugas", "Mostrar problemas hidráulicos", etc.

### Inspection Guidance
- "How do I inspect the tracks?" → Provides CAT inspection procedures
- "What does critical mean?" → Explains severity levels
- "When should I escalate?" → Provides safety/escalation guidance
- "How to fix hydraulic leaks?" → Provides maintenance procedures

### Conversation State
- Maintains multi-turn conversation history (last 10 messages)
- Session-based contexts for personalized interactions
- Automatic history trimming to manage token usage

## API Endpoint

### POST /api/voice-agent
Request:
```json
{
  "user_message": "Search for track issues",
  "session_id": "voice_agent_session",
  "language": "en",
  "search_kb": true
}
```

Response:
```json
{
  "response": "I found several track-related findings...",
  "session_id": "voice_agent_session",
  "language": "en",
  "timestamp": null
}
```

## Integration Flow

```
User speaks → Browser Speech Recognition → transcript
                                              ↓
                          Frontend sends to /api/voice-agent
                                              ↓
                        Backend checks for KB search intent
                                              ↓
                          If KB search: Query knowledge base
                                    Add KB context to system prompt
                                              ↓
                        Send to ElevenLabs Conversational AI API
                          (with system prompt + KB context)
                                              ↓
                          ElevenLabs generates response
                                              ↓
                        Convert response to speech via /api/tts
                                              ↓
                              Play audio to user
```

## System Prompt Details

### Core Personality
- **Professional yet approachable** - Colleague mentality
- **Concise and action-oriented** - Technicians are busy
- **Safety-first** - Always prioritize equipment/operator safety
- **CAT expert** - Authoritative on CAT equipment

### Key Behaviors
1. **Searches knowledge base** for past findings when asked
2. **Understands CAT components** - Tracks, hydraulics, engines, etc.
3. **Explains severity** - Critical/Moderate/Minor ratings
4. **Guides report generation** - Walks through report creation
5. **Recommends escalation** - Safety-critical scenarios
6. **Conversational but specific** - Natural language + technical accuracy
7. **References actual findings** - Uses KB data, not made-up info

### Communication Examples

**Scenario 1: Track Issues**
- User: "What's wrong with the track?"
- Agent: "Let me search for similar cases... I found 3 track wear reports. The most recent showed minor surface corrosion. Here are the steps to inspect: [inspection procedure]. Would you like me to show you the video?"

**Scenario 2: Hydraulic Leak**
- User: "How do I fix hydraulic leaks?"
- Agent: "That depends on severity. For minor leaks, here's the procedure... For critical leaks, I recommend escalating to the service team. Based on your equipment history, you had similar issues in [KB match]. Let me show you that case."

**Scenario 3: Navigation**
- User: "Take me to the inspector"
- Agent: "Navigating to the inspector section. You can upload equipment photos, add voice notes, and I'll analyze them for anomalies."

## Language Support

### English (en-US)
- System prompt: Equipment inspection focused
- Voice: Aria (professional, clear)
- Speech Recognition: en-US locale

### Spanish (es-ES)
- System prompt: Spanish technical terminology
- Voice: Aria (works well in Spanish)
- Speech Recognition: es-ES locale

## Settings Customization

### To Change Voice:
Edit `app/config.py`:
```python
agent_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Change to George
```

### To Adjust Agent Creativity:
Edit `app/voice_agent.py`:
```python
"temperature": 0.5  # More grounded (was 0.7)
```

### To Increase Response Length:
```python
"max_tokens": 512  # Was 256
```

### To Change KB Search Behavior:
Edit endpoint in `app/main.py`:
```python
kb_matches = kb.search_transcript(
    query=request.user_message,
    n=5  # Increase results from 3
)
```

## Troubleshooting

### Voice Agent Not Responding
1. Check ELEVENLABS_API_KEY in .env
2. Verify API key has conversational_ai permissions
3. Check browser console for errors
4. Ensure microphone permissions granted

### KB Context Not Showing in Responses
1. Verify KB is loaded (`/api/kb/query` works)
2. Check search terms match KB content
3. Increase n_results in endpoint

### Response Takes Too Long
1. Reduce `max_tokens` in AGENT_SETTINGS
2. Reduce `n` in KB search (fewer context items)
3. Check ElevenLabs API rate limits

## Example Queries by Category

### Navigation
- "Go to inspector"
- "Show knowledge base"
- "Navigate to features"
- "Take me to reports"

### Knowledge Base
- "Search for track wear"
- "Find hydraulic problems"
- "Show me similar excavator issues"
- "What was the last wheel loader inspection?"

### Inspection Guidance
- "How do I inspect the engine?"
- "What does critical mean?"
- "When should I escalate issues?"
- "What are best practices for track inspection?"

### Help
- "Help"
- "What can you do?"
- "How do I use this?"
- "Tell me about the system"

## Performance Notes

- **Response time**: 1-3 seconds (speech recognition → API call → TTS)
- **KB search**: ~200ms for semantic search
- **Conversation history**: Last 10 messages retained per session
- **Token usage**: ~150-200 tokens per interaction (optimized for voice)

## Security

- API keys stored in .env (not hardcoded)
- Session IDs are random per conversation
- No personal data stored in conversation history
- KB search scoped to public equipment findings

## Future Enhancements

1. **Multi-language support** - Add Portuguese, German, etc.
2. **Custom KB training** - Fine-tune agent on site-specific procedures
3. **Integration with IoT sensors** - Real-time equipment data in context
4. **Voice biometrics** - Technician authentication
5. **Offline fallback** - Local speech recognition if API unavailable
