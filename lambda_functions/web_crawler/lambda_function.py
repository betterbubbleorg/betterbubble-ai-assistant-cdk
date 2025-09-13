"""
Web Crawler Lambda Function
Crawls websites and searches the internet, storing content in S3 for Bedrock Knowledge Base.
Supports multiple search engines: DuckDuckGo (free), Google Custom Search, Bing.
"""

import json
import boto3
import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import quote_plus, urlparse


def search_duckduckgo(query, max_results=5):
    """Search using DuckDuckGo (free, no API key needed)."""
    try:
        # DuckDuckGo instant answer API
        search_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        
        response = requests.get(search_url, timeout=10)
        data = response.json()
        
        urls = []
        
        # Get related topics
        if 'RelatedTopics' in data:
            for topic in data['RelatedTopics'][:max_results]:
                if 'FirstURL' in topic:
                    urls.append(topic['FirstURL'])
        
        # Get abstract URL if available
        if 'AbstractURL' in data and data['AbstractURL']:
            urls.append(data['AbstractURL'])
        
        return urls[:max_results]
        
    except Exception as e:
        print(f"DuckDuckGo search error: {str(e)}")
        return []


def search_google_knowledge_graph(query, api_key, max_results=5):
    """Search using Google Knowledge Graph API for structured data."""
    try:
        search_url = "https://kgsearch.googleapis.com/v1/entities:search"
        params = {
            'query': query,
            'limit': min(max_results, 10),
            'indent': True,
            'key': api_key
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        data = response.json()
        
        urls = []
        
        # Extract URLs from Knowledge Graph results
        if 'itemListElement' in data:
            for item in data['itemListElement']:
                if 'result' in item and 'detailedDescription' in item['result']:
                    if 'url' in item['result']['detailedDescription']:
                        urls.append(item['result']['detailedDescription']['url'])
                elif 'result' in item and 'url' in item['result']:
                    urls.append(item['result']['url'])
        
        return urls[:max_results]
        
    except Exception as e:
        print(f"Google Knowledge Graph search error: {str(e)}")
        return []


def search_google_custom(query, api_key, search_engine_id, max_results=5):
    """Search using Google Custom Search API."""
    try:
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(max_results, 10)
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        data = response.json()
        
        urls = []
        if 'items' in data:
            for item in data['items']:
                urls.append(item['link'])
        
        return urls
        
    except Exception as e:
        print(f"Google Custom Search error: {str(e)}")
        return []


def search_bing(query, api_key, max_results=5):
    """Search using Bing Search API."""
    try:
        search_url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {'Ocp-Apim-Subscription-Key': api_key}
        params = {'q': query, 'count': min(max_results, 10)}
        
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        urls = []
        if 'webPages' in data and 'value' in data['webPages']:
            for page in data['webPages']['value']:
                urls.append(page['url'])
        
        return urls
        
    except Exception as e:
        print(f"Bing search error: {str(e)}")
        return []


def crawl_url(url, s3_client, bucket_name):
    """Crawl a single URL and store content in S3."""
    try:
        print(f"Crawling {url}...")
        
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, timeout=15, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text content
        text_content = soup.get_text()
        
        # Clean up text
        text_content = ' '.join(text_content.split())
        
        # Limit content size (Lambda has memory limits)
        if len(text_content) > 100000:  # 100KB limit
            text_content = text_content[:100000] + "... [truncated]"
        
        # Create safe filename
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        path = parsed_url.path.replace('/', '_') or 'index'
        filename = f"{domain}{path}.txt"
        
        # Store in S3
        key = f"web-crawled-data/{filename}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=text_content,
            ContentType='text/plain',
            Metadata={
                'source_url': url,
                'crawled_at': str(int(time.time())),
                'content_length': str(len(text_content))
            }
        )
        
        return f"Successfully processed {url} ({len(text_content)} chars)"
        
    except Exception as e:
        error_msg = f"Error processing {url}: {str(e)}"
        print(error_msg)
        return error_msg


def get_ssm_parameter(parameter_name):
    """Get parameter value from SSM Parameter Store."""
    if not parameter_name:
        return ''
    
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        value = response['Parameter']['Value']
        # Return empty string if parameter is not set (placeholder value)
        return '' if value == 'NOT_SET' else value
    except Exception as e:
        print(f"Error getting SSM parameter {parameter_name}: {str(e)}")
        return ''


def handler(event, context):
    """Main handler function for web crawling and searching."""
    
    s3 = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    
    # Get configuration from environment variables
    search_queries = os.environ.get('SEARCH_QUERIES', 'AI news,technology updates,programming tutorials').split(',')
    search_engines = os.environ.get('SEARCH_ENGINES', 'duckduckgo,google_kg').split(',')  # duckduckgo, google_kg, google, bing
    
    # Get API keys from SSM Parameter Store
    google_api_key_param = os.environ.get('GOOGLE_API_KEY_PARAM', '')
    google_search_engine_id_param = os.environ.get('GOOGLE_SEARCH_ENGINE_ID_PARAM', '')
    bing_api_key_param = os.environ.get('BING_API_KEY_PARAM', '')
    
    google_api_key = get_ssm_parameter(google_api_key_param)
    google_search_engine_id = get_ssm_parameter(google_search_engine_id_param)
    bing_api_key = get_ssm_parameter(bing_api_key_param)
    
    # Fallback URLs if search fails
    fallback_urls = [
        "https://news.ycombinator.com",
        "https://www.reddit.com/r/technology",
        "https://techcrunch.com",
    ]
    
    results = []
    all_urls = set()
    
    # Perform searches based on queries using multiple engines
    for query in search_queries:
        query = query.strip()
        if not query:
            continue
            
        print(f"Searching for: {query}")
        
        query_urls = set()
        
        # Search with each configured engine
        for search_engine in search_engines:
            search_engine = search_engine.strip()
            if not search_engine:
                continue
                
            search_urls = []
            
            if search_engine == 'duckduckgo':
                search_urls = search_duckduckgo(query)
                print(f"DuckDuckGo found {len(search_urls)} URLs for: {query}")
            elif search_engine == 'google_kg' and google_api_key:
                search_urls = search_google_knowledge_graph(query, google_api_key)
                print(f"Google Knowledge Graph found {len(search_urls)} URLs for: {query}")
            elif search_engine == 'google' and google_api_key and google_search_engine_id:
                search_urls = search_google_custom(query, google_api_key, google_search_engine_id)
                print(f"Google Custom Search found {len(search_urls)} URLs for: {query}")
            elif search_engine == 'bing' and bing_api_key:
                search_urls = search_bing(query, bing_api_key)
                print(f"Bing found {len(search_urls)} URLs for: {query}")
            else:
                print(f"Search engine {search_engine} not configured or missing API keys")
                continue
            
            query_urls.update(search_urls)
        
        all_urls.update(query_urls)
        results.append(f"Found {len(query_urls)} total URLs for query: {query} using {len(search_engines)} engines")
    
    # Add fallback URLs if no search results
    if not all_urls:
        print("No search results, using fallback URLs")
        all_urls.update(fallback_urls)
    
    # Crawl all URLs
    for url in list(all_urls)[:20]:  # Limit to 20 URLs per run
        result = crawl_url(url, s3, bucket_name)
        results.append(result)
        time.sleep(1)  # Be respectful to servers
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Web crawling and searching completed',
            'search_engines': search_engines,
            'queries_searched': search_queries,
            'urls_found': len(all_urls),
            'results': results
        })
    }
