Feature: Multi-format Export
  As a content creator
  I want to export my transcripts to various formats
  So that I can use them for different purposes (subtitles, documents, APIs)

  # Common Background
  Background:
    Given a user is logged in
    And the user has a transcript with segments
    And the transcript has 10 segments
    And each segment has text and timestamps

  # ==================== SRT Format ====================

  Scenario: Export transcript to SRT format
    Given the user selects "SRT" export format
    And the user enables "Include Timestamps"
    And the user enables "Include Speaker Labels"
    When the user requests export
    Then the export job should be created with status "PENDING"
    And the export should complete within 10 seconds
    And the exported file should have ".srt" extension
    And the file should contain valid SRT format
    And each segment should have sequence number
    And each segment should have timecode in "HH:MM:SS,mmm" format
    And speaker labels should be included as "[SPEAKER_01] Text"

  Scenario: Export to SRT with custom options
    Given the user selects "SRT" export format
    And the user disables "Include Timestamps"
    And the user disables "Include Speaker Labels"
    When the user requests export
    Then the exported file should not contain timestamps
    And the exported file should not contain speaker labels
    And the file should contain only the transcript text

  # ==================== VTT Format ====================

  Scenario: Export transcript to VTT format
    Given the user selects "VTT" export format
    And the user enables "Include Timestamps"
    And the user enables "Include Speaker Labels"
    When the user requests export
    Then the export job should be created
    And the exported file should have ".vtt" extension
    And the file should start with "WEBVTT" header
    And each segment should have timecode in "HH:MM:SS.mmm" format
    And speaker labels should be included as "<SPEAKER_01>Text"

  Scenario: Export to VTT without speaker labels
    Given the user selects "VTT" export format
    And the user enables "Include Timestamps"
    And the user disables "Include Speaker Labels"
    When the user requests export
    Then the exported file should not contain speaker tags
    And segments should contain only text with timestamps

  # ==================== JSON Format ====================

  Scenario: Export transcript to JSON format
    Given the user selects "JSON" export format
    And the user enables "Include Metadata"
    And the user enables "Include Speaker Labels"
    When the user requests export
    Then the exported file should have ".json" extension
    And the file should be valid JSON
    And the JSON should have "segments" array
    And the JSON should have "metadata" object
    And each segment should have:
      | Field | Type | Description |
      | id | string | Segment identifier |
      | startTime | number | Start timestamp in seconds |
      | endTime | number | End timestamp in seconds |
      | text | string | Transcript text |
      | speakerId | string | Speaker identifier |
    And metadata should include:
      | Field | Description |
      | transcriptId | Transcript identifier |
      | language | Language code |
      | duration | Audio duration in seconds |
      | wordCount | Total word count |

  Scenario: Export to JSON without metadata
    Given the user selects "JSON" export format
    And the user disables "Include Metadata"
    When the user requests export
    Then the JSON should not have "metadata" field
    And the JSON should only have "segments" array

  # ==================== TXT Format ====================

  Scenario: Export transcript to plain text format
    Given the user selects "TXT" export format
    And the user enables "Include Speaker Labels"
    When the user requests export
    Then the exported file should have ".txt" extension
    And the file should contain only text, no timestamps
    And segments should be separated by blank lines
    And each segment should start with "SPEAKER_XX: " if speaker labels enabled

  Scenario: Export to TXT without speaker labels
    Given the user selects "TXT" export format
    And the user disables "Include Speaker Labels"
    When the user requests export
    Then the file should contain only transcript text
    And segments should be separated by blank lines
    And no speaker labels should be present

  # ==================== DOCX Format ====================

  Scenario: Export transcript to DOCX format
    Given the user selects "DOCX" export format
    And the user enables "Include Metadata"
    And the user enables "Include Timestamps"
    And the user enables "Include Speaker Labels"
    When the user requests export
    Then the exported file should have ".docx" extension
    And the document should be readable by Microsoft Word
    And the document should have title with transcript ID
    And the document should have metadata paragraph
    And each segment should be a separate paragraph
    And timestamps should be included as "[MM:SS - MM:SS] Text"
    And speaker labels should be included as "SPEAKER_XX: Text"

  # ==================== Batch Export ====================

  Scenario: Batch export multiple transcripts
    Given the user has 5 transcripts
    And the user selects "SRT" export format
    When the user requests batch export
    Then 5 export jobs should be created
    And each export should complete independently
    And failed exports should not affect other exports
    And the user should receive notification when all complete

  Scenario: Batch export with mixed results
    Given the user has 3 transcripts
    And transcript 2 is corrupted
    When the user requests batch export
    Then transcript 1 export should succeed
    And transcript 2 export should fail with error message
    And transcript 3 export should succeed
    And the user should see 2 successful and 1 failed export

  # ==================== Error Handling ====================

  Scenario: Export fails due to invalid format
    Given the user selects an invalid format
    When the user requests export
    Then the export should fail immediately
    And the user should see error "Format not supported"
    And no export job should be created

  Scenario: Export fails during processing
    Given the user selects "SRT" export format
    And the transcript database is inaccessible during export
    When the user requests export
    Then the export job should be marked as "FAILED"
    And the user should see error message
    And the user should be able to retry the export

  Scenario: Export large transcript
    Given the user has a transcript with 100,000 words
    And the user selects "TXT" export format
    When the user requests export
    Then the export should complete within 30 seconds
    And the exported file should be complete
    And the file size should be reasonable (<5MB)

  # ==================== File Storage ====================

  Scenario: Exported file download
    Given the user has a completed export job
    When the user downloads the exported file
    Then the file should download successfully
    And the file should match the requested format
    And the file content should match the transcript
    And the download should start within 2 seconds

  Scenario: Exported file expiration
    Given an export job was completed 25 hours ago
    When the user attempts to download the file
    Then the download should fail with "File expired"
    And the user should see message "Files are retained for 24 hours"

  # ==================== Export Templates ====================

  Scenario: Export with custom template
    Given the user has created a custom export template
    And the template defines custom header and footer
    When the user exports using the custom template
    Then the exported file should use the template format
    And the file should include the custom header
    And the file should include the custom footer
    And template variables should be replaced with actual values

  # ==================== Progress Tracking ====================

  Scenario: Export progress for large file
    Given the user has a large transcript (50,000 words)
    When the user requests export
    Then the user should see progress indicator
    And the progress should update every 1 second
    And the progress should reach 100% when complete
    And the user should receive notification when ready

  # ==================== Notifications ====================

  Scenario: Export completion notification
    Given the user requests an export
    And the export takes more than 10 seconds
    When the export completes
    Then the user should receive email notification
    And the email should contain download link
    And the email should include export format and file size
    And the download link should be valid for 24 hours

  # ==================== API Export ====================

  Scenario: Export via API
    Given a developer has valid API key
    And the developer has transcript ID
    When the developer calls POST /api/v1/transcripts/{id}/export
    And specifies format as "json"
    Then the API should return export job ID
    And the export should process asynchronously
    And the developer can poll GET /api/v1/export-jobs/{id}
    And when complete, the API should return download URL
