import requests
from bs4 import BeautifulSoup
import time
import json
import re
from urllib.parse import urljoin

BASE_URL = "https://www.gamesradar.com"
GENRES = {
    "Action Games": "/uk/games/action/",
    "RPGs": "/uk/games/rpgs/",
    "Action RPGs": "/uk/games/action-rpgs/",
    "Adventure Games": "/uk/games/adventure/",
    "Third Person Shooters": "/uk/games/third-person-shooters/",
    "FPS Games": "/uk/games/fps-games/",
}

NON_GAME_KEYWORDS = ["Reviews", "Mobile", "Nintendo", "PC", "Playstation", "Xbox", "Guide", "News", "Tips", "Best", "Deals", "Games"]

def get_soup(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def is_game_link(text, url):
    text_lower = text.lower()
    for kw in NON_GAME_KEYWORDS:
        if kw.lower() in text_lower:
            return False
    if any(kw.lower() in url.lower() for kw in ["reviews", "mobile", "nintendo", "pc", "playstation", "xbox", "guide", "news"]):
        return False
    return True

def extract_articles_from_hub(soup):
    """
    Extract article entries from a game hub page.
    Returns a list of dicts: {title, url, author, date, category}
    """
    articles = []

    # 1. Primary method: look for wdn-listv2-item containers (the pattern you provided)
    article_items = soup.find_all('li', class_='wdn-listv2-item')
    for item in article_items:
        # The main link is inside an <a> with target="_self"
        link_tag = item.find('a', href=True, target='_self')
        if not link_tag:
            continue
        url = urljoin(BASE_URL, link_tag['href'])

        # Title is inside <h2 class="wdn-listv2-item-content-title">
        title_tag = link_tag.find('h2', class_='wdn-listv2-item-content-title')
        title = title_tag.get_text(strip=True) if title_tag else 'Not Available'

        # Author: inside <span class="wdn-listv2-item-content-byline-author-name">
        author_tag = link_tag.find('span', class_='wdn-listv2-item-content-byline-author-name')
        author = author_tag.get_text(strip=True) if author_tag else 'Not Available'

        # Date: inside <time> element
        date_tag = link_tag.find('time', class_='date')
        if date_tag and date_tag.has_attr('datetime'):
            date = date_tag['datetime'][:10]  # YYYY-MM-DD
        else:
            date = 'Not Available'

        # Category: often a span with "News", "Guides", etc.
        cat_tag = link_tag.find('span', class_='wdn-listv2-item-content-title-label')
        category = cat_tag.get_text(strip=True) if cat_tag else 'Not Available'

        articles.append({
            "title": title,
            "url": url,
            "author": author,
            "date": date,
            "category": category
        })

    # 2. Fallback: If no wdn-listv2-item found, try generic patterns
    if not articles:
        # Try li with classes containing article/post/entry
        fallback_items = soup.find_all('li', class_=re.compile(r'article|post|entry', re.I))
        if not fallback_items:
            fallback_items = soup.find_all('a', href=True, class_=re.compile(r'title|headline', re.I))

        for item in fallback_items:
            # Get title from link
            title_link = item.find('a') if item.name != 'a' else item
            if not title_link or not title_link.get('href'):
                continue
            title = title_link.get_text(strip=True)
            if not title:
                continue

            url = urljoin(BASE_URL, title_link['href'])
            author = 'Not Available'
            date = 'Not Available'
            category = 'Not Available'

            # Try to find author and date in parent elements
            parent = title_link.find_parent()
            for _ in range(4):
                if not parent:
                    break
                # Look for author byline
                author_span = parent.find('span', class_=re.compile(r'author|byline', re.I))
                if author_span:
                    author = author_span.get_text(strip=True).replace('By', '').strip()
                # Look for date
                date_meta = parent.find('time', class_=re.compile(r'date|time', re.I))
                if date_meta and date_meta.has_attr('datetime'):
                    date = date_meta['datetime'][:10]
                # Look for category (if any)
                cat_span = parent.find('span', class_=re.compile(r'category|label', re.I))
                if cat_span:
                    category = cat_span.get_text(strip=True)
                parent = parent.parent

            articles.append({
                "title": title,
                "url": url,
                "author": author,
                "date": date,
                "category": category
            })

    return articles

def extract_game_info(soup, url):
    """Extract all required fields plus articles list."""
    info = {
        "Game Title": "Not Available",
        "Release Date": "Not Available",
        "Key Features": "Not Available",
        "Platform Availability": "Not Available",
        "Developer Information": "Not Available",
        "Articles": []  # will hold list of {title, publisher}
    }

    # Game Title - try h1
    title_elem = soup.find('h1')
    if title_elem:
        info["Game Title"] = title_elem.get_text(strip=True)

    # Release Date - look for meta or specific element
    release_meta = soup.find('meta', {'property': 'article:published_time'})
    if release_meta and release_meta.get('content'):
        info["Release Date"] = release_meta['content'][:10]
    else:
        date_elem = soup.find(class_=re.compile('release|date'))
        if date_elem:
            info["Release Date"] = date_elem.get_text(strip=True)

    # Key Features - look for a section with features
    features_section = soup.find('section', class_=re.compile('features', re.I))
    if features_section:
        features_list = features_section.find_all('li')
        if features_list:
            info["Key Features"] = ', '.join(li.get_text(strip=True) for li in features_list)
    else:
        possible_features = soup.find('div', string=re.compile('Features', re.I))
        if possible_features:
            parent = possible_features.find_parent()
            if parent:
                items = parent.find_all('li')
                if items:
                    info["Key Features"] = ', '.join(item.get_text(strip=True) for item in items)

    # Platform Availability
    platform_elem = soup.find(class_=re.compile('platforms', re.I))
    if platform_elem:
        platforms = platform_elem.find_all('span') or platform_elem.find_all('a')
        if platforms:
            info["Platform Availability"] = ', '.join(p.get_text(strip=True) for p in platforms)
    else:
        meta_platform = soup.find('meta', {'name': 'platform'})
        if meta_platform and meta_platform.get('content'):
            info["Platform Availability"] = meta_platform['content']

    # Developer Information
    dev_elem = soup.find(class_=re.compile('developer', re.I))
    if dev_elem:
        info["Developer Information"] = dev_elem.get_text(strip=True)
    else:
        meta_dev = soup.find('meta', {'name': 'developer'})
        if meta_dev and meta_dev.get('content'):
            info["Developer Information"] = meta_dev['content']

    # Extract articles from hub page
    info["Articles"] = extract_articles_from_hub(soup)

    return info

def scrape_genre(genre_name, genre_url):
    full_url = urljoin(BASE_URL, genre_url)
    soup = get_soup(full_url)
    if not soup:
        return []

    # Try to find the exact container class first
    explore_container = soup.find('ul', class_=re.compile(r'mx-2\.5 my-2\.5 mb-0 flex flex-row flex-wrap justify-center'))
    if not explore_container:
        # Fallback: look for any container with 'explore' in class
        explore_container = soup.find('div', class_=re.compile('explore', re.I)) or soup.find('section', class_=re.compile('explore', re.I))

    if not explore_container:
        print(f"Could not find Explore container for {genre_name}")
        return []

    links = explore_container.find_all('a', href=True)
    game_links = []
    for link in links:
        text = link.get_text(strip=True)
        href = link['href']
        if text and href and is_game_link(text, href):
            full_link = urljoin(BASE_URL, href)
            game_links.append((text, full_link))

    print(f"Found {len(game_links)} game links for {genre_name}")
    return game_links

def scrape_all():
    all_games = []
    for genre_name, genre_path in GENRES.items():
        print(f"Scraping {genre_name}...")
        game_links = scrape_genre(genre_name, genre_path)
        for game_name, game_url in game_links:
            print(f"  Scraping {game_name}...")
            soup = get_soup(game_url)
            if soup:
                game_info = extract_game_info(soup, game_url)
                game_info["Genre"] = genre_name
                game_info["Game URL"] = game_url
                if game_info["Game Title"] == "Not Available" and game_name:
                    game_info["Game Title"] = game_name
                all_games.append(game_info)
            time.sleep(1)
        time.sleep(2)

    return all_games

if __name__ == "__main__":
    data = scrape_all()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Scraped {len(data)} games. Data saved to data.json")
