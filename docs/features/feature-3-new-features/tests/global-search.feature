Feature: Global Search Across Transcripts
  As a researcher
  I want to search across all my transcripts for specific keywords
  So that I can find relevant content without listening to hours of audio

  # Common Background
  Background:
    Given a user has 50 transcripts in the database
    And the transcripts are in English and Russian
    And the transcripts are indexed in Qdrant
    And the search service is available

  # ==================== Basic Search ====================

  Scenario: Search for single keyword
    Given the user searches for "user experience"
    When the search completes
    Then the response should be < 500ms
    And results should be ranked by relevance
    And each result should show:
      | Field | Description |
      | transcriptId | Transcript identifier |
      | title | Transcript title |
      | snippet | Highlighted text with match |
      | language | Language code |
      | relevanceScore | Relevance (0-1) |
      | matchedAt | Timestamp of match |

  Scenario: Search with no results
    Given the user searches for "xyznonexistentword"
    When the search completes
    Then the result count should be 0
    And the user should see "No results found"
    And suggestions for similar terms should appear

  Scenario: Search with phrase
    Given the user searches for "machine learning algorithms"
    When the search completes
    Then results should contain the exact phrase
    And results should be ranked higher for exact phrase matches
    And snippets should highlight the full phrase

  # ==================== Filtering ====================

  Scenario: Search with date range filter
    Given the user searches for "interview"
    And the user filters by date range: "2024-01-01" to "2024-01-31"
    When the search completes
    Then results should only include transcripts from January 2024
    And the result count should reflect the filter

  Scenario: Search with language filter
    Given the user searches for "interview"
    And the user filters by language: "en"
    When the search completes
    Then results should only include English transcripts
    And Russian transcripts should be excluded

  Scenario: Search with multiple filters
    Given the user searches for "interview"
    And the user applies filters:
      | Filter | Value |
      | language | en |
      | dateFrom | 2024-01-01 |
      | dateTo | 2024-01-31 |
      | durationMin | 1800 |
    When the search completes
    Then results should match all filters
    And the result count should reflect combined filter

  Scenario: Search with speaker filter
    Given the user has transcripts with speaker diarization
    And the user searches for "strategy"
    And the user filters by speaker: "SPEAKER_01"
    When the search completes
    Then results should only include segments spoken by SPEAKER_01
    And segments from other speakers should be excluded

  # ==================== Pagination ====================

  Scenario: Search with pagination (first page)
    Given the user searches for a common term with 100 results
    And the page size is 20
    When the user views page 1
    Then results 1-20 should be displayed
    And the user should see "Showing 1-20 of 100 results"
    And "Next Page" button should be available

  Scenario: Search with pagination (middle page)
    Given the user searches for a common term with 100 results
    And the page size is 20
    When the user views page 3
    Then results 41-60 should be displayed
    And "Previous Page" and "Next Page" buttons should be available

  Scenario: Search with pagination (last page)
    Given the user searches for a common term with 100 results
    And the page size is 20
    When the user views page 5
    Then results 81-100 should be displayed
    And "Previous Page" button should be available
    And "Next Page" button should be disabled

  # ==================== Sorting ====================

  Scenario: Sort results by relevance (default)
    Given the user searches for "interview"
    When the results are displayed
    Then results should be sorted by relevance score descending
    And the most relevant result should appear first

  Scenario: Sort results by date
    Given the user searches for "interview"
    And the user selects "Sort by: Date (newest)"
    When the results are displayed
    Then results should be sorted by creation date descending
    And the newest transcript should appear first

  Scenario: Sort results by duration
    Given the user searches for "interview"
    And the user selects "Sort by: Duration (longest)"
    When the results are displayed
    Then results should be sorted by duration descending
    And the longest transcript should appear first

  # ==================== Context Snippets ====================

  Scenario: Search results show context snippets
    Given the user searches for "machine learning"
    When the results are displayed
    Then each result should show a snippet
    And the snippet should include 50 characters before the match
    And the snippet should include 50 characters after the match
    And the matched term should be highlighted

  Scenario: Multiple matches in same transcript
    Given a transcript contains "machine learning" 5 times
    When the user searches for "machine learning"
    Then the result should show 5 separate snippets
    Or the result should show count: "5 matches"
    And clicking should show all match positions

  # ==================== Result Actions ====================

  Scenario: Click search result to open transcript
    Given the user searches for "user experience"
    And the results are displayed
    When the user clicks on a result
    Then the transcript detail page should open
    And the page should scroll to the first match
    And the matched text should be highlighted

  Scenario: Export search results
    Given the user searches for "interview"
    And the results contain 25 matches
    When the user clicks "Export Results"
    Then a CSV file should be downloaded
    And the CSV should contain columns:
      | Column | Description |
      | Transcript ID | Identifier |
      | Title | Transcript title |
      | Matched Text | The matched segment |
      | Timestamp | Position in audio |
      | URL | Link to transcript |
      | Relevance Score | Match relevance |

  # ==================== Advanced Search (v1.2) ====================

  Scenario: Boolean search with AND
    Given the user searches for "machine AND learning"
    When the results are displayed
    Then results should contain both "machine" and "learning"
    And results should be ranked higher for proximity

  Scenario: Boolean search with OR
    Given the user searches for "ML OR machine learning"
    When the results are displayed
    Then results should contain "ML" or "machine learning"
    And results with both terms should be ranked higher

  Scenario: Boolean search with NOT
    Given the user searches for "interview NOT podcast"
    When the results are displayed
    Then results should contain "interview"
    And results should NOT contain "podcast"

  Scenario: Proximity search
    Given the user searches for "machine NEAR/5 learning"
    When the results are displayed
    Then results should have "machine" within 5 words of "learning"
    And closer matches should be ranked higher

  # ==================== Semantic Search ====================

  Scenario: Semantic search finds related concepts
    Given the user searches for "user experience design"
    When the results are displayed
    Then results should include:
      | Exact matches | "user experience design" |
      | Semantic matches | "UX design", "UI/UX", "design thinking" |
    And semantic matches should have lower but reasonable scores

  Scenario: Semantic search handles synonyms
    Given the user searches for "cost reduction"
    When the results are displayed
    Then results should include:
      | Synonyms | "cost saving", "reduce expenses", "cut costs" |
    And synonym matches should be indicated in results

  # ==================== Performance ====================

  Scenario: Search performance with large database
    Given the database has 100,000 transcripts
    And all transcripts are indexed
    When the user searches for a common term
    Then the search should complete in < 500ms
    And the results should be properly ranked

  Scenario: Search performance with complex query
    Given the database has 50,000 transcripts
    When the user searches with multiple filters and boolean operators
    Then the search should complete in < 1000ms
    And all filters should be applied correctly

  # ==================== Search Analytics ====================

  Scenario: Track search queries for analytics
    Given the user searches for "user experience"
    When the search completes
    Then the search query should be logged
    And the log should include:
      | Field | Value |
      | userId | User identifier |
      | searchTerm | "user experience" |
      | resultCount | Number of results |
      | executionTime | Search duration |
      | timestamp | Search time |

  Scenario: Popular search terms
    Given the system has tracked 1000 searches
    When the administrator views search analytics
    Then the top 10 search terms should be displayed
    And each term should show:
      | Metric | Description |
      | Term | Search term |
      | Count | Search count |
      | AvgResults | Average result count |
      | AvgTime | Average execution time |

  # ==================== Search Suggestions ====================

  Scenario: Auto-complete search suggestions
    Given the user starts typing "user ex"
    When the user has typed 3 characters
    Then suggestions should appear
    And suggestions should include:
      | "user experience" |
      | "user expectations" |
      | "user experiment" |

  Scenario: Search for typo correction
    Given the user searches for "usr experience" (typo)
    When the search completes
    Then the system should show "Did you mean: user experience?"
    And results should be shown for corrected term
    And the user can click to search corrected term

  # ==================== Search via API ====================

  Scenario: Search via API
    Given a developer has a valid API key
    When the developer calls GET /api/v1/search
    And query parameter: q="machine learning"
    And query parameter: language="en"
    And query parameter: limit=20
    Then the API should return 200 OK
    And the response should contain:
      | Field | Description |
      | results | Array of search results |
      | totalCount | Total matching transcripts |
      | page | Current page number |
      | pageSize | Results per page |
      | hasMore | Boolean for more pages |
    And each result should include transcript ID, snippet, score

  Scenario: API search pagination
    Given a developer searches via API
    And there are 100 results total
    When the developer requests page 2 with limit=20
    Then the API should return results 21-40
    And the response should indicate hasMore=true

  # ==================== Search Indexing ====================

  Scenario: Index new transcript for search
    Given a user creates a new transcript
    When the transcription completes
    Then the transcript should be automatically indexed
    And the transcript should be searchable within 5 seconds
    And an indexing event should be logged

  Scenario: Update search index on transcript edit
    Given a user edits a transcript
    And the transcript is already indexed
    When the user saves the edit
    Then the search index should be updated
    And the updated content should be reflected in search results

  Scenario: Remove from search index on deletion
    Given a user deletes a transcript
    When the deletion completes
    Then the transcript should be removed from search index
    And subsequent searches should not return the deleted transcript

  # ==================== Search History ====================

  Scenario: View recent searches
    Given a user has performed 10 searches
    When the user views their search history
    Then the last 10 searches should be displayed
    And each entry should show:
      | Field | Description |
      | Search term | The query |
      | Timestamp | When searched |
      | Result count | Number of results |
    And the user can click to re-run any search

  Scenario: Save search as alert
    Given a user searches for "competitor name"
    And the user wants to monitor mentions
    When the user saves the search as an alert
    Then the system should monitor for new matches
    And the user should be notified when new transcripts match
