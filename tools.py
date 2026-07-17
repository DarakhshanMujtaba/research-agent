from ddgs import DDGS


def is_low_quality(snippet: str, title: str = "") -> bool:
    """
    Checks if a search result looks unreliable - either the snippet
    reads like a spammy keyword list, or the title looks corrupted
    (multiple page titles merged together, which happens sometimes
    with search engine scraping).

    Returns True if the result should be DISCARDED (low quality).
    """
    snippet = snippet.strip()
    title = title.strip()

    # Too short to be useful information
    if len(snippet) < 30:
        return True

    # Count commas vs total words - a real sentence has few commas
    # relative to its length. A tag-list like "Bank Pakistan, Pakistan
    # energy, Home battery..." has a comma almost every 2-3 words.
    word_count = len(snippet.split())
    comma_count = snippet.count(",")

    if word_count > 0 and (comma_count / word_count) > 0.3:
        return True

    # Title too long usually means multiple page titles got merged
    # together during scraping (a sign of a corrupted/unreliable result).
    if len(title) > 100:
        return True

    # Too many capitalized "words stuck together" in the title
    # (e.g. "ELETRICITYcREVIEW2025PAKISTANELE") is another sign of
    # merged/corrupted text rather than a real page title.
    stuck_together_count = sum(
        1 for word in title.split() if len(word) > 20
    )
    if stuck_together_count > 0:
        return True

    return False


def web_search(query: str, max_results: int = 4) -> str:
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results + 3))

        for r in raw_results:
            snippet = r.get("body", "")
            title = r.get("title", "")

            if is_low_quality(snippet, title):
                continue

            results.append(
                f"Title: {title}\n"
                f"Snippet: {snippet}\n"
                f"Source: {r.get('href', '')}\n"
            )

            if len(results) >= max_results:
                break

        if not results:
            return f"No good results found for query: '{query}'"

        return "\n---\n".join(results)

    except Exception as e:
        return f"Search failed for query '{query}': {str(e)}"


def web_search_structured(query: str, max_results: int = 4) -> list:
    """
    Same as web_search, but returns a list of dicts instead of a single
    string - this makes it easy to assign a numbered ID to each source
    later, for clean [1] [2] style citations.
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results + 3))

        for r in raw_results:
            snippet = r.get("body", "")
            title = r.get("title", "")

            if is_low_quality(snippet, title):
                continue

            results.append({
                "title": title,
                "snippet": snippet,
                "url": r.get("href", ""),
            })

            if len(results) >= max_results:
                break

        return results

    except Exception:
        return []


if __name__ == "__main__":
    result = web_search("Pakistan renewable energy targets 2024")
    print(result)