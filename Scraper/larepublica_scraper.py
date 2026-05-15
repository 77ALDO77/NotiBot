import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse
import re

def scrape_larepublica():
    """
    Scrape latest news from La República homepage and return as JSON
    """
    base_url = "https://larepublica.pe"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Fetch homepage
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching homepage: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    
    # Find article containers - based on observed patterns
    # Looking for common patterns in news sites
    article_selectors = [
        'article',  # Generic article tag
        '.news-item', 
        '.article-item',
        '.story',
        '[class*="post-"]',
        '[class*="article-"]',
        '.listing-item',
        '.entry'
    ]
    
    article_elements = []
    for selector in article_selectors:
        elements = soup.select(selector)
        if elements:
            article_elements = elements[:20]  # Limit to first 20 matches
            break
    
    # If no specific selectors work, look for links with article patterns
    if not article_elements:
        links = soup.find_all('a', href=True)
        article_elements = [link for link in links 
                          if re.search(r'/\d{4}/\d{2}/\d{2}/[^/]+-\d+$', link['href'])][:20]
    
    for element in article_elements:
        try:
            article_data = extract_article_data(element, base_url)
            if article_data and article_data.get('title'):
                articles.append(article_data)
        except Exception as e:
            print(f"Error processing article element: {e}")
            continue
    
    return articles

def extract_article_data(element, base_url):
    """
    Extract article data from a DOM element
    """
    data = {}
    
    # If element is a link, get the URL directly
    if element.name == 'a' and element.get('href'):
        url = element['href']
        # Make absolute URL
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        data['url'] = url
        
        # Try to find title within the link or nearby
        title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'strong']) or element
        data['title'] = title_elem.get_text(strip=True) if title_elem else ''
        
        # Look for image
        img_elem = element.find('img')
        if img_elem and img_elem.get('src'):
            img_url = img_elem['src']
            if not img_url.startswith('http'):
                img_url = urljoin(base_url, img_url)
            data['image_url'] = img_url
            
        # Look for summary/description
        # Often in paragraphs or divs with specific classes
        summary_selectors = ['p', '.summary', '.excerpt', '.description']
        for selector in summary_selectors:
            summary_elem = element.select_one(selector)
            if summary_elem and len(summary_elem.get_text(strip=True)) > 20:
                data['summary'] = summary_elem.get_text(strip=True)[:300]  # Limit length
                break
                
    else:
        # Element is a container, look for link inside
        link_elem = element.find('a', href=True)
        if not link_elem:
            return None
            
        url = link_elem['href']
        if not url.startswith('http'):
            url = urljoin(base_url, url)
        data['url'] = url
        
        # Extract title
        title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.headline', 'strong']
        title_elem = None
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                break
                
        if not title_elem:
            title_elem = link_elem
            
        data['title'] = title_elem.get_text(strip=True) if title_elem else ''
        
        # Extract image
        img_elem = element.find('img')
        if img_elem and img_elem.get('src'):
            img_url = img_elem['src']
            if not img_url.startswith('http'):
                img_url = urljoin(base_url, img_url)
            data['image_url'] = img_url
        
        # Extract summary
        summary_selectors = ['p', '.summary', '.excerpt', '.description', '.content']
        for selector in summary_selectors:
            summary_elem = element.select_one(selector)
            if summary_elem:
                text = summary_elem.get_text(strip=True)
                if len(text) > 20:  # Avoid very short text that's likely not summary
                    data['summary'] = text[:300]
                    break
    
    # Extract section from URL if possible
    if data.get('url'):
        path = urlparse(data['url']).path
        # Pattern: /seccion/fecha/titulo-id
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) >= 2 and path_parts[0] in ['politica', 'deportes', 'economia', 'sociedad', 'mundo', 'ciencia', 'espectaculos', 'futbol-peruano', 'cultura']:
            data['section'] = path_parts[0]
        else:
            data['section'] = 'unknown'
    
    # Only return if we have essential data
    if not data.get('title') or len(data['title']) < 5:
        return None
        
    return data

def main():
    """
    Main function to run scraper and output JSON
    """
    print("Scraping La República...")
    articles = scrape_larepublica()
    
    if not articles:
        print("No articles found")
        return
    
    # Output as JSON
    output = {
        'source': 'La República',
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_articles': len(articles),
        'articles': articles
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()