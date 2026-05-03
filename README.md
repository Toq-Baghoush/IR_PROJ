# TV Show Scraper

This Scrapy spider crawls TV show data from seriesgraph.com.


## Setup

1. Install dependencies:
   ```bash
   pip install scrapy
   ```

## Usage

The spider collects show URLs from the 43 paginated seriesgraph "all-shows" pages internally, then follows each show page and extracts metadata from the site's own JSON endpoints.

To run:
```bash
scrapy crawl shows -o output.json
```

## Output Fields

- `showname`: Show name extracted from HTML
- `link`: URL to the show page
- `rating`: Rating (float) from seriesgraph data
- `poster`: Poster image URL
- `seasons`: Number of seasons
- `episodes`: List of episode counts per season
- `episode_names`: List of episode title lists per season

