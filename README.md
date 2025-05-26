# Broken Image Checker

A Python script to scan web pages for broken images, either from a single URL or a sitemap, with detailed CSV reporting.

## Overview

`check_broken_images.py` scans web pages to identify broken images, flagging HTTP errors, network issues, or Content Security Policy (CSP) violations. It supports single-page checks or bulk processing via a user-provided sitemap, classifying image storage locations (e.g., AWS, Base64, WordPress) and outputting results to a timestamped CSV file.

### Features
- **Flexible Input**: Check a single page or an entire sitemap.
- **Site-Agnostic**: Configurable sitemap URL, allowed domains, and output directory.
- **Robust Validation**: Detects broken images using HTTP HEAD/GET requests (10-second timeout).
- **Storage Classification**: Categorizes image sources (e.g., Amazon S3, Google CDN, Local).
- **Concurrent Processing**: Processes sitemap pages with configurable threading (default: 2 threads).
- **Detailed Reports**: Generates CSV files with Article ID, Title, Page URL, Broken Image URL, Error, and Storage Location.

## Requirements

- Python 3.6+
- Dependencies:
  - `requests`
  - `beautifulsoup4`
  - `lxml` (optional, for faster XML parsing)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/broken-image-checker.git
   cd broken-image-checker
   ```

2. Install dependencies:
   ```bash
   pip install requests beautifulsoup4 lxml
   ```

3. Verify Python version:
   ```bash
   python --version
   ```

## Usage

Run the script and follow the prompts to check for broken images.

### Command
```bash
python check_broken_images.py
```

### Modes

#### Single Page Check
- Select `single` when prompted.
- Enter a page URL (e.g., `https://example.com/article/123`).
- Provide allowed domains (comma-separated, or press Enter for defaults: `example.com,cdn.example.com`).
- Specify output directory (or press Enter for default: `reports/broken_images`).
- Output: CSV file (e.g., `broken_images_single_page_20250526_110600.csv`).

#### Sitemap Check
- Select `all` when prompted.
- Enter the sitemap URL (e.g., `https://example.com/sitemap.xml`).
- Provide allowed domains and output directory as above.
- Output: CSV file (e.g., `broken_images_all_pages_20250526_110600.csv`).

### Example
```bash
$ python check_broken_images.py
Enter 'single' to check a single page or 'all' to check all pages: single
Enter allowed image domains (comma-separated, press Enter for defaults): example.com
Enter output directory path: /path/to/reports
Enter the page URL to check: https://example.com/article/123
```

### Output Format
The CSV report includes:
- **Article ID**: Extracted from the URL (if applicable).
- **Title**: Page title.
- **Page URL**: Scanned page URL.
- **Broken Image URL**: URL of the broken image.
- **HTTP Status Code**: Error (e.g., `HTTP 404`, `Network Error`, `CSP Violation`).
- **Storage Location**: Storage type (e.g., `Amazon Web Services`, `Base64 Encoded Image`).

## Configuration

- **Allowed Domains**: Set via prompt; defines CSP-compliant image domains.
- **Storage Classification**: Predefined mappings (e.g., AWS, Google CDN). Modify `get_storage_classification()` for custom mappings.
- **Output Directory**: Set via prompt; defaults to `reports/broken_images`.
- **Request Delay**: 1-second delay between requests (adjust `REQUEST_DELAY`).
- **Concurrency**: 2 threads for sitemap processing (adjust `max_threads` in `check_all_pages()`).
- **HTML Selector**: Default container is `.article-detail-card-content`. Update `container_selectors` in `scrape_and_check_images()` if needed.

## Notes

- Sitemaps must be XML with `<loc>` tags. Non-standard formats require code changes.
- Logging is set to `DEBUG` for detailed output. Set to `INFO` in `logging.basicConfig()` for less verbosity.
- Ensure the target site’s HTML structure matches the container selector, or adjust accordingly.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Commit changes: `git commit -m 'Add your feature'`.
4. Push to the branch: `git push origin feature/your-feature`.
5. Open a Pull Request.

Please include tests or documentation updates with your changes.

## Contact

For issues or questions, open an issue on the [GitHub repository](https://github.com/your-username/broken-image-checker) or contact:
- **Author**: Jeremy Henricks
- **Email**: info@henricksmedia.com

## Acknowledgments

- Powered by [Python](https://www.python.org/), [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/), and [Requests](https://requests.readthedocs.io/).
- Built to simplify web content maintenance.
