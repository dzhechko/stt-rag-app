# Gherkin Test Scenarios
## Feature 1: UI/UX Improvements

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2025-02-03 | System Architect | Draft |

---

## 1. Progress Tracking Features

### 1.1 View Real-time Progress Bar

```gherkin
Feature: Real-time Progress Tracking
  As a content creator
  I want to see real-time progress of my transcription
  So that I know the system is working and when it will complete

  Background:
    Given the STT application is loaded
    And I am logged in as a user

  Scenario: View progress bar during upload
    Given I have an audio file "meeting.mp3" of 50 MB
    When I drag and drop the file onto the upload zone
    Then I should see a progress bar appear
    And the progress bar should show "0%"
    When the file starts uploading
    Then the progress bar should begin filling
    And I should see the percentage update every few seconds
    And the progress bar should be labeled "Uploading..."

  Scenario: View progress across multiple stages
    Given I have uploaded a file "interview.mp3"
    And the file is being processed
    Then I should see a stage indicator showing all stages
    And the current stage should be highlighted
    And completed stages should show checkmarks
    And upcoming stages should be grayed out

    Examples:
      | Stage          | Status      |
      | Uploading      | Completed   |
      | Validating     | Completed   |
      | Processing     | In Progress |
      | Transcribing   | Pending     |
      | Finalizing     | Pending     |

  Scenario: Progress bar reaches 100%
    Given a transcription is in progress at 95%
    When the transcription completes
    Then the progress bar should show "100%"
    And the progress bar should turn green
    And a "Complete!" message should appear
```

### 1.2 Time Estimate Display

```gherkin
Feature: Time Estimation
  As a content creator
  I want to see an estimate of how long transcription will take
  So I can plan my time accordingly

  Scenario: Initial time estimate shown
    Given I have selected a file "podcast.mp3" of 100 MB
    And the file duration is 1 hour
    When I start the upload
    Then I should see a time estimate displayed
    And the estimate should say "About 3 hours remaining"
    And a confidence indicator should show "Low"

  Scenario: Time estimate updates during processing
    Given a transcription is in progress
    And the initial estimate was "2 hours remaining"
    When 30 minutes have passed
    And the transcription is 50% complete
    Then the time estimate should update to "About 1 hour 30 minutes remaining"
    And the confidence indicator should show "High"

  Scenario: Time estimate format changes based on duration
    Given a transcription is in progress
    When the estimated time remaining is 45 seconds
    Then the display should show "< 1 minute remaining"
    When the estimated time remaining is 15 minutes
    Then the display should show "About 15 minutes remaining"
    When the estimated time remaining is 90 minutes
    Then the display should show "About 1h 30m remaining"
```

---

## 2. Notification Features

### 2.1 Browser Notifications

```gherkin
Feature: Browser Notifications
  As a content creator
  I want to receive browser notifications when my transcription completes
  So I can be notified even when working in another tab

  Scenario: Request notification permission on first interaction
    Given I have not granted notification permission
    And I navigate to the STT application
    When I click anywhere on the page
    Then I should see a permission request dialog
    And the dialog should explain why notifications are needed
    When I click "Allow"
    Then notification permission should be granted
    And a confirmation message should appear

  Scenario: Receive notification on completion
    Given notification permission is granted
    And I have a transcription in progress
    And I switch to a different browser tab
    When the transcription completes
    Then I should receive a browser notification
    And the notification title should be "Transcription Complete"
    And the notification body should describe the completed file
    And the notification should have a "View" button
    When I click the "View" button
    Then I should be navigated to the transcript page

  Scenario: Notification permission denied
    Given I have denied notification permission
    And I have a transcription in progress
    When the transcription completes
    Then I should not receive a browser notification
    And I should see an in-app toast notification instead
```

### 2.2 In-App Toast Notifications

```gherkin
Feature: In-App Toast Notifications
  As a content creator
  I want to see toast notifications within the application
  So I never miss important updates

  Scenario: Display success toast on completion
    Given a transcription completes successfully
    Then a toast notification should appear
    And the toast should be colored green
    And the toast should have a title "Transcription Complete"
    And the toast should have a "View Transcript" button
    And the toast should auto-dismiss after 5 seconds
    When I hover over the toast
    Then the auto-dismiss timer should pause
    When I move my mouse away
    Then the auto-dismiss timer should resume

  Scenario: Display error toast with retry option
    Given a transcription fails with a network error
    Then a toast notification should appear
    And the toast should be colored red
    And the toast should explain the error
    And the toast should have a "Retry" button
    And the toast should have a "Cancel" button
    And the toast should not auto-dismiss
    When I click "Retry"
    Then the transcription should restart
    And the toast should dismiss

  Scenario: Multiple toasts stack correctly
    Given 3 notifications are triggered in sequence
    Then all 3 toasts should be visible
    And they should stack vertically
    And the most recent should be at the bottom
    When I dismiss the middle toast
    Then the remaining toasts should reposition
```

---

## 3. File Upload Features

### 3.1 Drag and Drop Upload

```gherkin
Feature: Drag and Drop File Upload
  As a content creator
  I want to drag and drop files to upload them
  So I can quickly start transcribing

  Scenario: Drag file over upload zone
    Given I am on the upload page
    And I have a file "recording.mp3" on my desktop
    When I drag the file over the upload zone
    Then the upload zone should highlight
    And the message should change to "Drop to upload"
    And the border color should change to blue

  Scenario: Drop valid file
    Given I am dragging a valid audio file over the upload zone
    When I drop the file
    Then the file should be added to the upload queue
    And I should see a file preview showing:
      | Field       | Value                  |
      | Name        | recording.mp3          |
      | Size        | 45.2 MB                |
      | Format      | MP3                    |
      | Status      | Ready to upload        |

  Scenario: Drop invalid file format
    Given I am dragging a document file "transcript.docx" over the upload zone
    When I drop the file
    Then the file should be rejected
    And an error message should appear: "Invalid file format"
    And supported formats should be listed
    And the file should not be added to the queue

  Scenario: Drop file larger than limit
    Given I am dragging a file "huge-file.mp4" of 2 GB over the upload zone
    When I drop the file
    Then a warning should appear: "File is larger than 1 GB"
    And I should be asked to confirm
    When I confirm the upload
    Then the file should be added to the queue
```

### 3.2 File Validation

```gherkin
Feature: File Validation
  As a content creator
  I want immediate feedback on file validity
  So I don't waste time uploading invalid files

  Scenario: Validate supported audio format
    Given I select an MP3 file
    Then the file should be marked as valid
    And no error message should appear

  Scenario: Reject unsupported format
    Given I select a file "video.avi"
    Then the file should be marked as invalid
    And an error should state: "AVI format is not supported"
    And supported formats should be listed

  Scenario: Validate file size within limits
    Given I select a file of 500 MB
    Then the file should be accepted without warning
    Given I select a file of 800 MB
    Then a warning should appear: "Large file - may take ~30 minutes"
    Given I select a file of 1.5 GB
    Then an error should appear: "File exceeds 1 GB limit"
```

---

## 4. Transcript Display Features

### 4.1 View Transcript with Timestamps

```gherkin
Feature: Transcript Display
  As a content creator
  I want to view my transcript with clickable timestamps
  So I can navigate to specific points in the audio

  Scenario: View transcript after completion
    Given my transcription has completed
    When I navigate to the transcript page
    Then I should see the full transcript text
    And timestamps should appear at regular intervals
    And each timestamp should be formatted as HH:MM:SS
    And speaker labels should be shown where available

  Scenario: Click timestamp to seek audio
    Given I am viewing a transcript
    And the audio player is visible
    When I click on timestamp "00:15:30"
    Then the audio player should seek to 15 minutes and 30 seconds
    And the clicked timestamp should be highlighted
    And the corresponding transcript section should scroll into view

  Scenario: Toggle speaker labels
    Given I am viewing a transcript with speaker labels
    And speaker labels are currently visible
    When I click the "Show Speakers" toggle
    Then speaker labels should be hidden
    When I click the toggle again
    Then speaker labels should be visible again
```

### 4.2 Search Within Transcript

```gherkin
Feature: Transcript Search
  As a content creator
  I want to search within my transcript
  So I can quickly find specific content

  Scenario: Search for word in transcript
    Given I am viewing a transcript containing the word "meeting"
    When I type "meeting" in the search box
    Then all occurrences of "meeting" should be highlighted
    And the number of matches should be displayed
    And the first match should be scrolled into view

  Scenario: Navigate between search results
    Given I have searched for "action items" in the transcript
    And there are 5 matches found
    When I click the "Next" button
    Then the next match should be highlighted
    And the view should scroll to that match
    When I click the "Previous" button
    Then the previous match should be highlighted

  Scenario: Case-sensitive search
    Given I type "Python" in the search box
    And case-sensitive search is enabled
    Then only "Python" should be highlighted
    And "python" should not be highlighted
    When I disable case-sensitive search
    Then both "Python" and "python" should be highlighted
```

### 4.3 Export Transcript

```gherkin
Feature: Export Transcript
  As a content creator
  I want to export my transcript in different formats
  So I can use it in different applications

  Scenario: Export as plain text
    Given I am viewing a completed transcript
    When I click the "Export" button
    And I select "Plain Text (.txt)"
    Then a file named "transcript.txt" should download
    And the file should contain the full transcript text

  Scenario: Export as SRT subtitles
    Given I am viewing a completed transcript with timestamps
    When I click the "Export" button
    And I select "SubRip (.srt)"
    Then a file named "transcript.srt" should download
    And the file should be in valid SRT format
    And the file should contain sequence numbers and timestamps

  Scenario: Export with options
    Given I click the "Export" button
    When I select "Custom Export"
    Then I should see export options:
      | Option            | Default  |
      | Include Timestamps | Yes      |
      | Include Speakers   | Yes      |
      | Format            | SRT      |
```

---

## 5. Error Handling Features

### 5.1 Display Error Messages

```gherkin
Feature: Error Display
  As a content creator
  I want clear error messages when something goes wrong
  So I can understand and fix the problem

  Scenario: Network error during upload
    Given I am uploading a file
    And my network connection is lost
    Then an error message should appear
    And the message should state: "Network connection lost"
    And the message should suggest: "Please check your internet connection"
    And a "Retry" button should be displayed
    And the error icon should be visible

  Scenario: Validation error with guidance
    Given I try to upload an invalid file
    When the validation fails
    Then an inline error should appear under the file
    And the error should explain: "MP3 format is required"
    And examples of valid formats should be shown
    And the upload button should be disabled

  Scenario: Server error with recovery
    Given the transcription service returns a 500 error
    Then a friendly error message should display
    And the message should apologize for the issue
    And options should be provided:
      | Option        | Description                    |
      | Try Again     | Retry the transcription        |
      | Contact Support | Open a support ticket        |
      | View Status   | Check service status page      |
```

### 5.2 Retry Mechanism

```gherkin
Feature: Retry Failed Operations
  As a content creator
  I want to retry failed operations
  So I can complete my task without starting over

  Scenario: Retry failed upload
    Given an upload failed at 45% progress
    And the error was temporary (network timeout)
    When I click the "Retry" button
    Then the upload should resume from 45%
    And the progress bar should show the previous progress
    And a "Retrying..." message should appear

  Scenario: Retry count limit
    Given an upload has failed 3 times
    And I click the "Retry" button
    Then I should see a message: "Maximum retry attempts reached"
    And alternative options should be shown:
      | Option                | Description              |
      | Choose different file | Start over with new file  |
      | Contact support       | Get help from support    |
```

---

## 6. Theme Features

### 6.1 Dark Mode Toggle

```gherkin
Feature: Dark Mode
  As a content creator
  I want to toggle between light and dark themes
  So I can use the application comfortably in any lighting

  Scenario: Toggle to dark mode
    Given I am using the light theme
    When I click the theme toggle button
    Then the application should switch to dark theme
    And the background should become dark
    And the text should become light
    And my preference should be saved

  Scenario: Persist theme preference
    Given I have selected dark mode
    When I refresh the page
    Then the dark theme should still be active
    When I close and reopen the browser
    Then the dark theme should still be active

  Scenario: Auto-detect system theme
    Given my OS is set to dark mode
    And I visit the application for the first time
    Then the application should detect my system preference
    And the dark theme should be applied automatically
    When I change my OS theme to light
    Then the application should offer to switch to light theme
```

### 6.2 High Contrast Mode

```gherkin
Feature: High Contrast Mode
  As a visually impaired user
  I want to enable high contrast mode
  So I can better read the interface

  Scenario: Enable high contrast mode
    Given I am in the accessibility settings
    When I enable "High Contrast Mode"
    Then all colors should adjust to high contrast
    And the background should be black
    And the text should be white
    And borders should be more pronounced
    And focus indicators should be thicker

  Scenario: High contrast in all components
    Given high contrast mode is enabled
    When I view any page of the application
    Then all text should meet AAA contrast standards
    And all interactive elements should have visible borders
    And focus states should be clearly visible
```

---

## 7. Accessibility Features

### 7.1 Keyboard Navigation

```gherkin
Feature: Keyboard Navigation
  As a keyboard-only user
  I want to navigate the application without a mouse
  So I can use the application efficiently

  Scenario: Tab through upload flow
    Given I am on the upload page
    When I press Tab
    Then focus should move to the upload zone
    When I press Tab again
    Then focus should move to the file picker button
    When I press Tab again
    Then focus should move to the upload button
    And a visible focus indicator should appear on each element

  Scenario: Keyboard shortcuts for common actions
    Given I am viewing a transcript
    When I press Ctrl+F
    Then focus should move to the search box
    When I press Ctrl+E
    Then the export menu should open
    When I press Escape
    Then any open dialogs should close

  Scenario: Navigate progress bar with keyboard
    Given a progress bar is visible
    When I press Tab while the progress bar has focus
    Then I should hear the current progress percentage
    And I should hear the current stage
```

### 7.2 Screen Reader Support

```gherkin
Feature: Screen Reader Support
  As a blind user
  I want the application to work with my screen reader
  So I can use the application independently

  Scenario: Announce progress updates
    Given a transcription is in progress at 50%
    When the progress updates to 51%
    Then my screen reader should announce "51 percent complete"
    And the current stage should be announced

  Scenario: Announce completion
    Given a transcription completes
    Then my screen reader should announce "Transcription complete"
    And a link to view the transcript should be announced

  Scenario: Accessible form inputs
    Given I am on the upload page
    When I focus the file input
    Then it should be announced as "Upload audio or video file"
    And accepted formats should be announced
    And the current state should be announced
```

---

## 8. Mobile Responsive Features

### 8.1 Mobile Upload

```gherkin
Feature: Mobile File Upload
  As a mobile user
  I want to upload files from my phone
  So I can transcribe on the go

  Scenario: Upload from mobile camera
    Given I am using the mobile app
    When I tap the upload button
    Then I should see options:
      | Option              | Description              |
      | Take Photo          | Use camera               |
      | Choose from Gallery | Select from photos       |
      | Choose from Files   | Select from file manager |
    When I tap "Choose from Files"
    Then the file picker should open
    And I should be able to select an audio file

  Scenario: Touch-optimized controls
    Given I am viewing the mobile interface
    Then all buttons should be at least 44x44 pixels
    And touch targets should have adequate spacing
    And swipe gestures should work for navigation
```

### 8.2 Mobile Progress View

```gherkin
Feature: Mobile Progress Display
  As a mobile user
  I want to see progress in a mobile-optimized format
  So I can easily track my transcriptions

  Scenario: Compact progress view on mobile
    Given I am viewing progress on a mobile device
    Then the progress bar should be full-width
    And stages should be shown as icons, not text
    And time estimate should be prominent
    And unnecessary details should be hidden

  Scenario: Background notification on mobile
    Given I have a transcription in progress
    And I switch to a different app
    When the transcription completes
    Then I should receive a push notification
    And tapping the notification should open the app
    And I should be taken to the transcript page
```

---

## 9. Performance Scenarios

### 9.1 Large File Handling

```gherkin
Feature: Large File Performance
  As a content creator
  I want the UI to remain responsive with large files
  So I don't think the application has frozen

  Scenario: Progress updates don't freeze UI
    Given I am uploading a 1 GB file
    When progress updates arrive every 100ms
    Then the UI should remain responsive
    And I should be able to scroll the page
    And I should be able to interact with other elements

  Scenario: Efficient transcript rendering
    Given I have a transcript with 10,000 segments
    When I navigate to the transcript page
    Then the page should load within 2 seconds
    And scrolling should be smooth at 60 FPS
    And search should complete within 1 second
```

---

*End of Gherkin Test Scenarios*
