# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-04-27

### Added
- **Function Documentation:** Added comprehensive docstrings to each function for better understanding and maintenance.
- **Progress Indicators:** Implemented print statements to display progress during member fetching and filtering processes.
- **Case-Insensitive Filtering:** Enhanced location filtering to be case-insensitive, ensuring accurate matches regardless of text case.
- **Graceful Exits:** Added checks to gracefully exit the script if critical steps like access token validation or member fetching fail.
- **Input Validation Enhancements:** Improved input validation in the member selection process to handle invalid inputs more gracefully.

### Changed
- **Modularization and Readability:** Refactored code for better readability and modularity, ensuring consistent formatting and structure.
- **Error Handling:** Enhanced error logging with more detailed messages to provide better context during failures.
- **Concurrent Removal Optimization:** Optimized the concurrent removal process by using a dictionary to map futures to members, improving efficiency and error tracking.
- **Logging Configuration:** Updated logging configuration to include timestamps and log levels for better traceability.

### Fixed
- **Access Token Handling:** Clarified the use of access tokens in the `validate_access_token` function, noting the typical use of an app access token.
- **Parameter Reset in Pagination:** Fixed the issue where parameters were not reset correctly during pagination, ensuring seamless data fetching across pages.

### Deprecated
- None

### Removed
- None

### Security
- **Access Token Handling:** Highlighted the importance of securing access tokens and recommended using environment variables or secure storage for sensitive information in production environments.

### Performance
- **Batch Processing:** Maintained efficient batch processing for fetching member metadata and removal operations to optimize performance.

## [1.0.0] - 2024-04-20

### Added
- Initial release of the Facebook Group Member Management script.
- Features include:
  - Access token validation.
  - Fetching group members with batching.
  - Filtering members by location.
  - Interactive member selection for removal.
  - Concurrent removal of selected members.
- Error logging to `error_log.txt`.
- Command-line interface using `argparse`.

