Feature: Language Auto-detection
  As a multilingual user
  I want the system to automatically detect the language of my audio
  So that I don't have to manually specify it before transcription

  # ==================== Basic Detection ====================

  Scenario: Detect language from audio file
    Given a user uploads an audio file
    And the audio file is in English
    And the audio is at least 30 seconds long
    When the system performs language detection
    Then the detected language should be "en"
    And the confidence score should be >= 0.95
    And the detection should complete within 5 seconds

  Scenario: Detect Russian language
    Given a user uploads an audio file in Russian
    And the audio is at least 30 seconds long
    When the system performs language detection
    Then the detected language should be "ru"
    And the confidence score should be >= 0.95

  Scenario: Detect Spanish language
    Given a user uploads an audio file in Spanish
    And the audio is at least 30 seconds long
    When the system performs language detection
    Then the detected language should be "es"
    And the confidence score should be >= 0.90

  # ==================== Low Confidence Handling ====================

  Scenario: Low confidence detection with warning
    Given a user uploads a short audio file (10 seconds)
    And the audio has background noise
    When the system performs language detection
    Then the detection should return a result
    And the confidence score should be between 0.70 and 0.95
    And the user should see a warning message
    And the user can proceed with detected language

  Scenario: Very low confidence requires manual selection
    Given a user uploads a very short audio file (5 seconds)
    And the audio has multiple speakers
    When the system performs language detection
    Then the confidence score should be < 0.70
    And the user should be prompted to manually select language
    And a default language should be suggested

  Scenario: Detection failure fallback
    Given the language detection service is unavailable
    When a user uploads an audio file
    Then the system should fall back to user's preferred language
    Or the system should fall back to English
    And the user should be notified of the fallback

  # ==================== Supported Languages ====================

  Scenario Outline: Detect supported languages
    Given a user uploads an audio file in <language>
    And the audio is clear and at least 30 seconds long
    When the system performs language detection
    Then the detected language code should be "<code>"
    And the confidence should be >= <min_confidence>

    Examples:
      | language | code | min_confidence |
      | English  | en   | 0.95           |
      | Russian  | ru   | 0.95           |
      | Spanish  | es   | 0.90           |
      | French   | fr   | 0.90           |
      | German   | de   | 0.90           |
      | Portuguese | pt | 0.85           |
      | Italian  | it   | 0.85           |
      | Dutch    | nl   | 0.80           |
      | Polish   | pl   | 0.80           |
      | Chinese  | zh   | 0.75           |

  # ==================== Multi-language Audio ====================

  Scenario: Detect dominant language in multi-language audio
    Given a user uploads an audio file
    And the audio contains 70% English and 30% Spanish
    When the system performs language detection
    Then the detected language should be "en"
    And the confidence should reflect the dominant portion

  Scenario: Detect language from mixed content (intro different language)
    Given a user uploads a podcast episode
    And the episode starts with a Spanish intro (10 seconds)
    And the rest is in English (50 minutes)
    When the system performs language detection
    Then the detected language should be "en"
    And the confidence should be >= 0.90

  # ==================== User Override ====================

  Scenario: User overrides detected language
    Given the system detects language as "en" with 0.80 confidence
    When the user manually selects "ru" as the language
    Then the transcription should use Russian
    And the system should remember the user's preference
    And future detections should default to Russian for this user

  Scenario: User confirms detected language
    Given the system detects language as "en" with 0.97 confidence
    When the user confirms the detected language
    Then the transcription should proceed with English
    And no confirmation prompt should appear for high confidence

  # ==================== Batch Detection ====================

  Scenario: Detect language for multiple files in batch
    Given a user uploads 5 audio files in a batch
    And the files are in different languages
    When the system processes the batch
    Then language detection should run for each file
    And detections should run in parallel (max 3 concurrent)
    And each file should get its detected language
    And the total detection time should be < 15 seconds

  Scenario: Batch with one detection failure
    Given a user uploads 3 audio files
    And file 2 is corrupted
    When the system detects languages for the batch
    Then file 1 should have its language detected
    And file 2 should fall back to default language
    And file 3 should have its language detected
    And the batch should not fail completely

  # ==================== Performance ====================

  Scenario: Fast detection for short audio
    Given a user uploads a 30-second audio clip
    When the system performs language detection
    Then the detection should complete in < 3 seconds

  Scenario: Detection for long audio
    Given a user uploads a 2-hour audio recording
    When the system performs language detection
    Then only the first 30 seconds should be analyzed
    And the detection should complete in < 5 seconds
    And the result should apply to the entire file

  Scenario: Detection does not delay transcription
    Given a user uploads an audio file
    When the system starts processing
    Then language detection should run in parallel with upload
    Or language detection should complete during upload
    And transcription should start immediately after detection

  # ==================== Error Handling ====================

  Scenario: Handle invalid audio for detection
    Given a user uploads a file that is not valid audio
    When the system attempts language detection
    Then the detection should fail gracefully
    And the user should see error "Unable to detect language from audio"
    And the user should be prompted to select language manually

  Scenario: Handle empty audio file
    Given a user uploads an audio file with 0 duration
    When the system attempts language detection
    Then the detection should fail immediately
    And the error should indicate "Audio file is empty or too short"

  # ==================== API Detection ====================

  Scenario: Language detection via API
    Given a developer has a valid API key
    When the developer calls POST /api/v1/detect-language
    And provides fileUrl: "https://example.com/audio.mp3"
    Then the API should return 200 OK
    And the response should contain:
      | Field | Type | Description |
      | language | string | ISO 639-1 code |
      | languageName | string | Full language name |
      | confidence | number | Confidence score (0-1) |
      | detectionDuration | number | Seconds to detect |

  Scenario: API detection with low confidence
    Given a developer requests language detection via API
    And the audio quality is poor
    When the detection completes with confidence < 0.70
    Then the API response should include "isFallback": true
    And the response should include "fallbackReason": string

  # ==================== Caching ====================

  Scenario: Cache detection results
    Given a user uploads an audio file
    And the system detects the language as "en"
    When the user uploads the same file again
    Then the system should use the cached detection result
    And the detection should be instant (<100ms)

  Scenario: Cache invalidation on file change
    Given a user uploads an audio file
    And the language is cached as "en"
    When the user uploads a modified version of the same file
    Then the cache should be invalidated
    And the system should re-detect the language

  # ==================== User Preferences ====================

  Scenario: Remember user's preferred language
    Given a user has previously selected "ru" as manual language
    When the user uploads a new audio file
    And the detection confidence is < 0.70
    Then the system should default to "ru"
    And the user should see "Using your preferred language: Russian"

  Scenario: Update user preference after confirmation
    Given a user's preferred language is "en"
    When the user uploads a file detected as "ru" with 0.96 confidence
    And the user confirms the detection
    Then the user's preferred language should update to "ru"
