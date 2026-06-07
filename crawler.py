import requests
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import urljoin, urlparse
import pandas as pd
import re

def get_page_data(url, session):
    try:
        response = session.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract metadata
        title = soup.title.string.strip() if soup.title else ''
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ''
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = meta_keywords['content'].strip() if meta_keywords and meta_keywords.get('content') else ''

        # URL structure analysis using Regex
        parsed = urlparse(url)
        path = parsed.path
        has_numbers_in_url = bool(re.search(r'\d{4,}', path))  # long numbers in URL = bad SEO
        url_depth = len([p for p in path.split('/') if p])

        # Extract all links on the page for BFS
        links = []
        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(url, a_tag['href'])
            links.append(full_url)

        # Flag SEO issues
        issues = []
        if not title:
            issues.append('Missing title')
        elif len(title) > 60:
            issues.append('Title too long')
        if not description:
            issues.append('Missing meta description')
        elif len(description) > 160:
            issues.append('Meta description too long')
        if not keywords:
            issues.append('Missing keywords')
        if has_numbers_in_url:
            issues.append('URL contains numeric IDs - bad for SEO')
        if url_depth > 3:
            issues.append('URL too deep')

        return {
            'url': url,
            'title': title,
            'description': description,
            'keywords': keywords,
            'url_depth': url_depth,
            'issues': ', '.join(issues) if issues else 'None'
        }, links

    except Exception as e:
        return None, []


def crawl(start_url, max_pages=20):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    base_domain = urlparse(start_url).netloc
    visited = set()
    queue = deque([start_url])
    results = []

    print(f"Starting crawl on: {start_url}\n")

    while queue and len(visited) < max_pages:
        url = queue.popleft()

        # Skip already visited or external links
        if url in visited:
            continue
        if urlparse(url).netloc != base_domain:
            continue

        print(f"Crawling: {url}")
        visited.add(url)

        data, links = get_page_data(url, session)
        if data:
            results.append(data)
            for link in links:
                if link not in visited:
                    queue.append(link)  # BFS - add to queue

    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv('seo_report.csv', index=False)
    print(f"\nDone! Crawled {len(results)} pages.")
    print("Report saved to seo_report.csv")
    return df


if __name__ == "__main__":
    start_url = "https://books.toscrape.com"  # safe practice website
    df = crawl(start_url, max_pages=20)
    print("\nSEO Issues Summary:")
    print(df[['url', 'issues']])