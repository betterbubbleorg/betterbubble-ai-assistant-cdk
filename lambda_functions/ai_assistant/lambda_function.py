import json
import boto3
import os
from datetime import datetime
import jwt
import requests
from urllib.parse import quote_plus

# Initialize clients
bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb')

def verify_jwt_token(token, user_pool_id, region='us-west-2'):
    """Verify JWT token and extract user information"""
    try:
        # Get the public keys from Cognito
        jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        jwks = requests.get(jwks_url).json()
        
        # Decode the token header to get the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header['kid']
        
        # Find the matching key
        key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == kid:
                from jwt.algorithms import RSAAlgorithm
                key = RSAAlgorithm.from_jwk(json.dumps(jwk))
                break
        
        if not key:
            raise ValueError('Unable to find appropriate key')
        
        # Verify and decode the token
        expected_audience = os.environ.get('COGNITO_USER_POOL_CLIENT_ID')
        expected_issuer = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
        
        # For Cognito access tokens, we need to verify client_id instead of aud
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            issuer=expected_issuer,
            options={"verify_aud": False, "verify_iss": True}
        )
        
        # Verify the client_id matches our expected audience
        if payload.get('client_id') != expected_audience:
            raise ValueError(f"Invalid client_id: {payload.get('client_id')}")
        
        # Verify token use is 'access'
        if payload.get('token_use') != 'access':
            raise ValueError(f"Invalid token_use: {payload.get('token_use')}")
        
        return payload
    except Exception as e:
        print(f"JWT verification error: {str(e)}")
        return None

def get_conversation_history(user_id, dynamodb, topic='General', limit=10):
    """Retrieve recent conversation history for context, filtered by topic"""
    try:
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        
        # Query recent conversations for this user and topic
        response = conversations_table.query(
            KeyConditionExpression='user_id = :user_id',
            FilterExpression='topic = :topic',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':topic': topic
            },
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        conversations = []
        for item in response.get('Items', []):
            conversations.append({
                'user_message': item.get('user_message', ''),
                'ai_response': item.get('ai_response', ''),
                'timestamp': item.get('timestamp', ''),
                'thread_id': item.get('thread_id', ''),
                'topic': item.get('topic', 'General')
            })
        
        # Reverse to get chronological order (oldest first)
        conversations.reverse()
        return conversations
        
    except Exception as e:
        print(f"Error retrieving conversation history: {str(e)}")
        return []

def get_current_datetime():
    """Get current date and time information"""
    now = datetime.utcnow()
    return {
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S UTC'),
        'day_of_week': now.strftime('%A'),
        'month': now.strftime('%B'),
        'year': now.strftime('%Y'),
        'full_datetime': now.strftime('%A, %B %d, %Y at %H:%M:%S UTC')
    }

def get_admin_knowledge(dynamodb):
    """Get all admin-defined permanent knowledge."""
    try:
        admin_knowledge_table = dynamodb.Table(os.environ.get('ADMIN_KNOWLEDGE_TABLE_NAME', 'aiassistant-dev-admin-knowledge'))
        
        response = admin_knowledge_table.scan()
        knowledge_items = response.get('Items', [])
        
        # Format knowledge for the AI
        knowledge_text = ""
        if knowledge_items:
            knowledge_text = "\n\n🧠 ADMIN FACTS (ALWAYS TRUE):\n"
            for item in knowledge_items:
                knowledge_text += f"- {item.get('knowledge', '')}\n"
            knowledge_text += "\nThese facts override all other information. When correcting users, be brief and direct.\n"
        
        return knowledge_text
        
    except Exception as e:
        print(f"Error retrieving admin knowledge: {str(e)}")
        return ""

def save_admin_knowledge(knowledge_text, dynamodb):
    """Save new admin knowledge permanently."""
    try:
        admin_knowledge_table = dynamodb.Table(os.environ.get('ADMIN_KNOWLEDGE_TABLE_NAME', 'aiassistant-dev-admin-knowledge'))
        
        knowledge_id = f"knowledge_{int(datetime.utcnow().timestamp())}"
        
        knowledge_item = {
            'knowledge_id': knowledge_id,
            'knowledge': knowledge_text,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': 'admin',
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 365 * 10))  # 10 years TTL
        }
        
        admin_knowledge_table.put_item(Item=knowledge_item)
        print(f"Saved admin knowledge: {knowledge_text}")
        return True
        
    except Exception as e:
        print(f"Error saving admin knowledge: {str(e)}")
        return False

def is_admin_knowledge_command(message):
    """Check if the message is an admin knowledge command."""
    message_lower = message.lower()
    admin_commands = [
        "remember that",
        "remember the",
        "permanently remember",
        "admin knowledge",
        "set knowledge",
        "permanent fact"
    ]
    
    return any(cmd in message_lower for cmd in admin_commands)

def extract_knowledge_from_command(message):
    """Extract the knowledge to remember from the command."""
    # Remove command words and extract the knowledge
    message_lower = message.lower()
    
    # Find the knowledge part after command words
    knowledge_starters = [
        "remember that ",
        "remember the ",
        "permanently remember ",
        "admin knowledge: ",
        "set knowledge: ",
        "permanent fact: "
    ]
    
    for starter in knowledge_starters:
        if starter in message_lower:
            start_index = message_lower.find(starter) + len(starter)
            return message[start_index:].strip()
    
    # If no specific starter found, try to extract after "remember"
    if "remember" in message_lower:
        remember_index = message_lower.find("remember")
        # Find the next word after "remember"
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() == "remember":
                if i + 1 < len(words):
                    # Get everything after "remember"
                    return " ".join(words[i+1:]).strip()
    
    return message.strip()

def is_user_admin(user_id, dynamodb):
    """Check if a user has admin role."""
    try:
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        
        response = users_table.get_item(Key={'user_id': user_id})
        user = response.get('Item')
        
        if user:
            return user.get('role', 'user') == 'admin'
        else:
            # If user not found in users table, check if they're in Cognito admin group
            # For now, return False - user must be explicitly added as admin
            return False
            
    except Exception as e:
        print(f"Error checking admin status for user {user_id}: {str(e)}")
        return False

def is_budget_command(message):
    """Check if the message is a budget tracking command."""
    message_lower = message.lower()
    budget_indicators = [
        "spent",
        "spend",
        "budget",
        "expense",
        "cost",
        "paid",
        "bought",
        "purchased",
        "invested"
    ]
    
    # Check for spending patterns
    spending_patterns = [
        "spent $",
        "spent ",
        "spend $",
        "cost $",
        "paid $",
        "bought ",
        "purchased ",
        "invested $"
    ]
    
    return any(indicator in message_lower for indicator in budget_indicators) or \
           any(pattern in message_lower for pattern in spending_patterns)

def extract_budget_info(message):
    """Extract budget information from the message."""
    import re
    
    # Extract amount (look for $X, $X.XX, X dollars, etc.)
    amount_patterns = [
        r'\$(\d+(?:\.\d{2})?)',  # $500, $500.50
        r'(\d+(?:\.\d{2})?)\s*dollars?',  # 500 dollars
        r'(\d+(?:\.\d{2})?)\s*bucks?',  # 500 bucks
    ]
    
    amount = None
    for pattern in amount_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            amount = float(match.group(1))
            break
    
    # Extract category (look for "on X", "for X", "on X category")
    category_patterns = [
        r'on\s+([^,.!?]+?)(?:\s+for|\s+will|\s+to|\s+and|$)',
        r'for\s+([^,.!?]+?)(?:\s+will|\s+to|\s+and|$)',
        r'([^,.!?]+?)\s+expense',
        r'([^,.!?]+?)\s+cost',
    ]
    
    category = None
    for pattern in category_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            category = match.group(1).strip()
            # Clean up common words
            category = re.sub(r'\b(today|this|that|the|a|an)\b', '', category, flags=re.IGNORECASE).strip()
            if category:
                break
    
    # Extract duration (look for "for X months", "will last X", etc.)
    duration_patterns = [
        r'for\s+(\d+)\s+(?:months?|weeks?|days?|years?)',
        r'will\s+last\s+(\d+)\s+(?:months?|weeks?|days?|years?)',
        r'(\d+)\s+(?:months?|weeks?|days?|years?)\s+(?:of|worth)',
    ]
    
    duration = None
    duration_unit = None
    for pattern in duration_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            duration = int(match.group(1))
            # Extract unit
            unit_match = re.search(r'(\d+)\s+(months?|weeks?|days?|years?)', message, re.IGNORECASE)
            if unit_match:
                duration_unit = unit_match.group(2).rstrip('s')  # Remove 's' for singular
            break
    
    # Extract description (the main part of the message)
    description = message
    if category:
        description = description.replace(f"on {category}", "").replace(f"for {category}", "")
    if amount:
        description = re.sub(r'\$\d+(?:\.\d{2})?', '', description)
        description = re.sub(r'\d+(?:\.\d{2})?\s*dollars?', '', description, flags=re.IGNORECASE)
    
    description = re.sub(r'\s+', ' ', description).strip()
    
    return {
        'amount': amount,
        'category': category or 'General',
        'duration': duration,
        'duration_unit': duration_unit,
        'description': description,
        'date': datetime.utcnow().isoformat()
    }

def save_budget_entry(user_id, budget_info, dynamodb):
    """Save budget entry to DynamoDB."""
    try:
        budget_table = dynamodb.Table(os.environ.get('BUDGET_TABLE_NAME', 'aiassistant-dev-budget'))
        
        budget_id = f"budget_{int(datetime.utcnow().timestamp())}"
        
        budget_item = {
            'budget_id': budget_id,
            'user_id': user_id,
            'amount': budget_info['amount'],
            'category': budget_info['category'],
            'description': budget_info['description'],
            'duration': budget_info['duration'],
            'duration_unit': budget_info['duration_unit'],
            'date': budget_info['date'],
            'created_at': datetime.utcnow().isoformat(),
            'organization': 'BetterBubble',
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 365 * 5))  # 5 years TTL
        }
        
        budget_table.put_item(Item=budget_item)
        print(f"Budget entry saved: {budget_id}")
        return True
        
    except Exception as e:
        print(f"Error saving budget entry: {str(e)}")
        return False

def get_budget_summary(organization='BetterBubble', dynamodb=None):
    """Get budget summary for organization."""
    try:
        budget_table = dynamodb.Table(os.environ.get('BUDGET_TABLE_NAME', 'aiassistant-dev-budget'))
        
        # Scan for all budget entries for the organization
        response = budget_table.scan(
            FilterExpression='organization = :org',
            ExpressionAttributeValues={':org': organization}
        )
        
        entries = response.get('Items', [])
        
        # Calculate totals
        total_spent = sum(entry.get('amount', 0) for entry in entries if entry.get('amount'))
        
        # Group by category
        category_totals = {}
        for entry in entries:
            category = entry.get('category', 'General')
            amount = entry.get('amount', 0)
            if category in category_totals:
                category_totals[category] += amount
            else:
                category_totals[category] = amount
        
        # Get recent entries (last 10)
        recent_entries = sorted(entries, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
        
        return {
            'total_spent': total_spent,
            'total_entries': len(entries),
            'category_breakdown': category_totals,
            'recent_entries': recent_entries,
            'organization': organization
        }
        
    except Exception as e:
        print(f"Error getting budget summary: {str(e)}")
        return None

def search_duckduckgo(query, max_results=3):
    """Search using DuckDuckGo web search (free, no API key needed)."""
    try:
        # First try instant answer API for well-known entities
        instant_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        instant_response = requests.get(instant_url, timeout=10)
        instant_data = instant_response.json()
        
        results = []
        
        # Get instant answer if available
        if 'Abstract' in instant_data and instant_data['Abstract']:
            results.append({
                'title': instant_data.get('Heading', 'Instant Answer'),
                'content': instant_data['Abstract'],
                'url': instant_data.get('AbstractURL', ''),
                'source': 'DuckDuckGo Instant Answer'
            })
        
        # Get related topics from instant answer
        if 'RelatedTopics' in instant_data:
            for topic in instant_data['RelatedTopics'][:max_results]:
                if 'Text' in topic and 'FirstURL' in topic:
                    results.append({
                        'title': topic.get('Text', '')[:100] + '...' if len(topic.get('Text', '')) > 100 else topic.get('Text', ''),
                        'content': topic.get('Text', ''),
                        'url': topic['FirstURL'],
                        'source': 'DuckDuckGo Related Topics'
                    })
        
        # If we don't have enough results, try web search
        if len(results) < max_results:
            # Use DuckDuckGo HTML search to get actual web results
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                'User-Agent': 'BetterBubble AI Web Scraper v1.0 - Intelligent Research Assistant (https://betterbubble.ai)'
            }
            
            search_response = requests.get(search_url, headers=headers, timeout=15)
            search_response.raise_for_status()
            
            # Parse HTML results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(search_response.content, 'html.parser')
            
            # Find search result links
            result_links = soup.find_all('a', class_='result__a')
            for link in result_links[:max_results - len(results)]:
                title = link.get_text(strip=True)
                url = link.get('href', '')
                
                # Get snippet from parent result div
                result_div = link.find_parent('div', class_='result')
                snippet = ""
                if result_div:
                    snippet_elem = result_div.find('a', class_='result__snippet')
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                
                if title and url:
                    results.append({
                        'title': title,
                        'content': snippet or title,
                        'url': url,
                        'source': 'DuckDuckGo Web Search'
                    })
        
        return results[:max_results]
        
    except Exception as e:
        print(f"DuckDuckGo search error: {str(e)}")
        return []

def search_google_knowledge_graph(query, api_key, max_results=3):
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
        
        results = []
        
        # Extract results from Knowledge Graph
        if 'itemListElement' in data:
            for item in data['itemListElement']:
                if 'result' in item:
                    result = item['result']
                    results.append({
                        'title': result.get('name', ''),
                        'content': result.get('description', ''),
                        'url': result.get('url', ''),
                        'source': 'Google Knowledge Graph'
                    })
        
        return results[:max_results]
        
    except Exception as e:
        print(f"Google Knowledge Graph search error: {str(e)}")
        return []

def get_search_history(user_id, topic, dynamodb):
    """Get search history for a user and topic to avoid repetition."""
    try:
        search_history_table = dynamodb.Table(os.environ.get('SEARCH_HISTORY_TABLE_NAME', 'aiassistant-dev-search-history'))
        
        # Use the GSI to query by user_id and topic
        response = search_history_table.query(
            IndexName='topic-index',
            KeyConditionExpression='user_id = :user_id AND topic = :topic',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':topic': topic
            },
            ScanIndexForward=False,  # Most recent first
            Limit=50  # Get last 50 searches
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error getting search history: {str(e)}")
        return []

def save_search_results(user_id, topic, search_query, results, dynamodb):
    """Save search results to avoid repetition."""
    try:
        search_history_table = dynamodb.Table(os.environ.get('SEARCH_HISTORY_TABLE_NAME', 'aiassistant-dev-search-history'))
        
        # Save each result
        for i, result in enumerate(results):
            search_item = {
                'user_id': user_id,
                'topic': topic,
                'search_id': f"{user_id}_{topic}_{int(datetime.utcnow().timestamp())}_{i}",
                'search_query': search_query,
                'result_title': result.get('title', ''),
                'result_url': result.get('url', ''),
                'result_source': result.get('source', ''),
                'searched_at': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow().timestamp() + 86400 * 7))  # 7 days TTL
            }
            search_history_table.put_item(Item=search_item)
        
        print(f"Saved {len(results)} search results to history")
        
    except Exception as e:
        print(f"Error saving search results: {str(e)}")

def get_unseen_results(all_results, search_history):
    """Filter out results that have already been seen."""
    seen_urls = set()
    for history_item in search_history:
        if history_item.get('result_url'):
            seen_urls.add(history_item['result_url'])
    
    unseen_results = []
    for result in all_results:
        if result.get('url') not in seen_urls:
            unseen_results.append(result)
    
    return unseen_results

def crawl_website(url, max_depth=2):
    """Crawl a website to extract more detailed information."""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time
        
        print(f"Crawling website: {url}")
        
        headers = {
            'User-Agent': 'BetterBubble AI Web Scraper v1.0 - Intelligent Research Assistant (https://betterbubble.ai)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content
        content = ""
        
        # Try to find main content areas
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            content = main_content.get_text(strip=True)
        else:
            # Fallback to body content
            body = soup.find('body')
            if body:
                content = body.get_text(strip=True)
        
        # Clean up content
        content = ' '.join(content.split())
        content = content[:2000]  # Limit content length
        
        # Extract title
        title = soup.find('title')
        title = title.get_text(strip=True) if title else "No title"
        
        # Extract links for further crawling
        links = []
        for link in soup.find_all('a', href=True)[:10]:  # Limit to 10 links
            href = link['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                # Convert relative URL to absolute
                from urllib.parse import urljoin
                links.append(urljoin(url, href))
        
        return {
            'title': title,
            'content': content,
            'url': url,
            'links': links[:5],  # Return top 5 links
            'source': 'Website Crawl'
        }
        
    except Exception as e:
        print(f"Error crawling {url}: {str(e)}")
        return None

def generate_follow_up_queries(topic, initial_results):
    """Generate follow-up queries based on initial search results."""
    follow_up_queries = []
    
    # Extract key terms from the topic
    topic_lower = topic.lower()
    
    if "technology" in topic_lower or "ai" in topic_lower or "artificial intelligence" in topic_lower:
        follow_up_queries = [
            f"latest {topic} news 2024",
            f"{topic} applications and use cases",
            f"{topic} challenges and limitations",
            f"{topic} future trends and predictions",
            f"{topic} companies and startups"
        ]
    elif "science" in topic_lower:
        follow_up_queries = [
            f"recent {topic} research studies",
            f"{topic} scientific discoveries",
            f"{topic} experiments and findings",
            f"{topic} scientific community",
            f"{topic} breakthrough developments"
        ]
    elif "business" in topic_lower or "finance" in topic_lower:
        follow_up_queries = [
            f"{topic} market analysis",
            f"{topic} industry trends",
            f"{topic} investment opportunities",
            f"{topic} business strategies",
            f"{topic} economic impact"
        ]
    else:
        # Generic follow-up queries
        follow_up_queries = [
            f"recent {topic} developments",
            f"{topic} latest news",
            f"{topic} important facts",
            f"{topic} key insights",
            f"{topic} expert opinions"
        ]
    
    return follow_up_queries[:3]  # Return top 3 follow-up queries

def search_web_for_query(user_message, user_id, topic, max_results=5, enable_deep_research=True):
    """Search the web with intelligent iteration and deep research capabilities."""
    try:
        # Get API keys from SSM Parameter Store
        ssm_client = boto3.client('ssm')
        
        google_api_key = ''
        try:
            google_api_key_param = os.environ.get('GOOGLE_API_KEY_PARAM', '')
            if google_api_key_param:
                response = ssm_client.get_parameter(Name=google_api_key_param, WithDecryption=True)
                google_api_key = response['Parameter']['Value']
                if google_api_key == 'NOT_SET':
                    google_api_key = ''
        except:
            pass
        
        # Get search history to avoid repetition
        search_history = get_search_history(user_id, topic, dynamodb)
        print(f"Found {len(search_history)} previous searches for this topic")
        
        # Extract key terms from the user's message for better search
        search_query = user_message.strip()
        
        # Create simplified search terms
        search_terms = []
        search_lower = search_query.lower()
        
        # Check for specific phrases and topics first
        if "quantum computing" in search_lower:
            search_terms.extend(["quantum computing", "quantum computers", "quantum technology"])
        elif "artificial intelligence" in search_lower or "ai" in search_lower:
            search_terms.extend(["artificial intelligence", "AI developments", "machine learning"])
        elif "machine learning" in search_lower:
            search_terms.extend(["machine learning", "ML algorithms", "deep learning"])
        elif "blockchain" in search_lower:
            search_terms.extend(["blockchain", "cryptocurrency", "distributed ledger"])
        elif "mazda" in search_lower and "cx-30" in search_lower:
            search_terms.extend(["Mazda CX-30", "Mazda CX-30 price", "Mazda CX-30 financing"])
        elif "mazda" in search_lower:
            search_terms.extend(["Mazda", "Mazda cars", "Mazda pricing"])
        elif "financing" in search_lower or "loan" in search_lower or "credit union" in search_lower:
            search_terms.extend(["auto financing", "car loans", "credit union rates"])
        elif "date" in search_lower or "today" in search_lower:
            search_terms.extend(["current date", "today's date", "what day is it"])
        else:
            # Extract key phrases and words from the query
            # Look for 2-word phrases first
            words = search_query.split()
            phrases = []
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 5 and phrase.lower() not in ['tell me', 'what are', 'can you', 'i want', 'i need', 'need to', 'to research', 'to know']:
                    phrases.append(phrase)
            
            # Add phrases first, then individual words
            search_terms.extend(phrases[:2])  # Take first 2 phrases
            
            # Add individual key words (prioritize important terms)
            important_words = []
            for w in words:
                if (len(w) > 3 and 
                    w.lower() not in ['what', 'are', 'the', 'latest', 'developments', 'in', 'can', 'you', 'tell', 'me', 'everything', 'about', 'need', 'to', 'research', 'know', 'zip', 'code', 'monthly', 'payment', 'down', 'upfront'] and
                    w.lower() not in ['if', 'someone', 'can', 'afford', 'for', 'months', 'how', 'much', 'do', 'have', 'give', 'her', 'today', 'and', 'low', 'get', 'my', 'contribution', 'buy', 'that', 'car', 'tomorrow']):
                    important_words.append(w)
            
            search_terms.extend(important_words[:3])  # Take first 3 important words
            
            if not search_terms:
                search_terms.append(search_query)
        
        all_results = []
        
        # Phase 1: Initial search
        print("=== PHASE 1: Initial Search ===")
        for term in search_terms[:3]:  # Limit to 3 terms
            print(f"Searching DuckDuckGo for: {term}")
            duckduckgo_results = search_duckduckgo(term, max_results)
            all_results.extend(duckduckgo_results)
            print(f"DuckDuckGo found {len(duckduckgo_results)} results for '{term}'")
            
            if len(all_results) >= max_results * 2:
                break
        
        # Try Google Knowledge Graph if we have API key and need more results
        if len(all_results) < max_results and google_api_key:
            for term in search_terms[:2]:  # Try top 2 terms
                print(f"Searching Google Knowledge Graph for: {term}")
                google_results = search_google_knowledge_graph(term, google_api_key, max_results - len(all_results))
                all_results.extend(google_results)
                print(f"Google Knowledge Graph found {len(google_results)} results for '{term}'")
                
                if len(all_results) >= max_results:
                    break
        
        # Phase 2: Deep research with follow-up queries
        if enable_deep_research and len(all_results) > 0:
            print("=== PHASE 2: Deep Research ===")
            follow_up_queries = generate_follow_up_queries(topic, all_results)
            
            for follow_up_query in follow_up_queries:
                print(f"Follow-up search: {follow_up_query}")
                follow_up_results = search_duckduckgo(follow_up_query, 2)
                all_results.extend(follow_up_results)
                print(f"Follow-up found {len(follow_up_results)} results")
                
                if len(all_results) >= max_results * 3:
                    break
        
        # Phase 3: Deep crawl of promising websites
        if enable_deep_research and len(all_results) > 0:
            print("=== PHASE 3: Deep Website Crawling ===")
            crawled_results = []
            
            # Select top 3 most promising URLs for deep crawling
            promising_urls = [r.get('url') for r in all_results[:3] if r.get('url')]
            
            for url in promising_urls:
                crawled_result = crawl_website(url)
                if crawled_result:
                    crawled_results.append(crawled_result)
                    print(f"Successfully crawled: {url}")
            
            all_results.extend(crawled_results)
        
        # Filter out results we've already seen
        unseen_results = get_unseen_results(all_results, search_history)
        print(f"Found {len(unseen_results)} unseen results out of {len(all_results)} total")
        
        # If we don't have enough unseen results, include some seen ones but prioritize unseen
        if len(unseen_results) < max_results:
            # Add some seen results to fill the gap
            seen_results = [r for r in all_results if r.get('url') in [h.get('result_url') for h in search_history]]
            needed = max_results - len(unseen_results)
            unseen_results.extend(seen_results[:needed])
            print(f"Added {min(needed, len(seen_results))} previously seen results to fill gap")
        
        # Select the best results (prioritize unseen, then by relevance)
        selected_results = unseen_results[:max_results]
        
        # Save these results to history
        if selected_results:
            save_search_results(user_id, topic, search_query, selected_results, dynamodb)
        
        print(f"=== FINAL RESULT: {len(selected_results)} comprehensive results ===")
        return selected_results
        
    except Exception as e:
        print(f"Web search error: {str(e)}")
        return []

def build_conversation_prompt(user_message, conversation_history, reminder_context="", web_search_results=None, admin_knowledge="", budget_info=None, budget_summary=None):
    """Build a prompt with conversation context and reminders"""
    
    # Get current date/time information
    current_time = get_current_datetime()
    
    # System prompt for the AI assistant
    system_prompt = f"""You are a helpful AI personal assistant. Be concise and direct in your responses.

    📅 CURRENT DATE AND TIME INFORMATION:
    - Today is {current_time['full_datetime']}
    - Date: {current_time['date']}
    - Time: {current_time['time']}
    - Day of the week: {current_time['day_of_week']}
    - Month: {current_time['month']}
    - Year: {current_time['year']}

    🔔 REMINDER CAPABILITIES:
    You can help users create reminders by recognizing phrases like:
    - "remind me to..."
    - "don't forget to..."
    - "I need to remember..."
    - "set a reminder for..."

    When you see these phrases, create a reminder for the user.

    🌐 WEB SEARCH INSTRUCTIONS:
    - Use the web search results provided below when relevant
    - Be brief and to the point
    - If admin facts contradict user questions, correct them directly and briefly
    - Keep responses concise unless detailed information is specifically requested"""
    
    # Add web search results if available
    web_search_context = ""
    if web_search_results:
        web_search_context = "\n\n🌐 REAL-TIME WEB SEARCH RESULTS:\n"
        web_search_context += f"Found {len(web_search_results)} relevant references for your question:\n\n"
        for i, result in enumerate(web_search_results, 1):
            web_search_context += f"📖 REFERENCE {i}:\n"
            web_search_context += f"Title: {result.get('title', 'No title available')}\n"
            web_search_context += f"Content: {result.get('content', 'No content available')}\n"
            if result.get('url'):
                web_search_context += f"Source URL: {result.get('url')}\n"
            web_search_context += f"Search Engine: {result.get('source', 'Web Search')}\n"
            web_search_context += "---\n\n"
        web_search_context += "Use these real-time web search results to provide comprehensive, accurate, and up-to-date answers. Always cite your sources when using information from these references.\n"
    
    # Build conversation context
    context_messages = []
    
    # Add conversation history
    for conv in conversation_history[-5:]:  # Last 5 exchanges for context
        if conv.get('user_message'):
            context_messages.append({
                'role': 'user',
                'content': conv['user_message']
            })
        if conv.get('ai_response'):
            context_messages.append({
                'role': 'assistant',
                'content': conv['ai_response']
            })
    
    # Add budget context if available
    budget_context = ""
    if budget_info:
        budget_context = f"\n\n💰 BUDGET ENTRY SAVED:\n"
        budget_context += f"Amount: ${budget_info['amount']}\n"
        budget_context += f"Category: {budget_info['category']}\n"
        budget_context += f"Description: {budget_info['description']}\n"
        if budget_info.get('duration'):
            budget_context += f"Duration: {budget_info['duration']} {budget_info.get('duration_unit', 'units')}\n"
        budget_context += f"Date: {budget_info['date']}\n"
        budget_context += f"Organization: BetterBubble\n"
    
    if budget_summary:
        budget_context += f"\n\n📊 BETTERBUBBLE BUDGET SUMMARY:\n"
        budget_context += f"Total Spent: ${budget_summary['total_spent']:,.2f}\n"
        budget_context += f"Total Entries: {budget_summary['total_entries']}\n"
        budget_context += f"Organization: {budget_summary['organization']}\n\n"
        
        if budget_summary['category_breakdown']:
            budget_context += "Category Breakdown:\n"
            for category, amount in budget_summary['category_breakdown'].items():
                budget_context += f"- {category}: ${amount:,.2f}\n"
        
        if budget_summary['recent_entries']:
            budget_context += "\nRecent Entries:\n"
            for entry in budget_summary['recent_entries'][:5]:  # Show last 5
                budget_context += f"- ${entry.get('amount', 0):,.2f} on {entry.get('category', 'General')} ({entry.get('date', 'Unknown date')})\n"
    
    # Add current user message with system context
    full_user_message = f"{system_prompt}{admin_knowledge}{budget_context}{reminder_context}{web_search_context}\n\nUser: {user_message}"
    context_messages.append({
        'role': 'user',
        'content': full_user_message
    })
    
    return context_messages

def get_or_create_thread_id(user_id, dynamodb, topic='General'):
    """Get or create a thread ID for grouping conversations by topic"""
    try:
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        
        # Query for recent conversations in this topic
        response = conversations_table.query(
            KeyConditionExpression='user_id = :user_id',
            FilterExpression='topic = :topic',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':topic': topic
            },
            ScanIndexForward=False,  # Most recent first
            Limit=1
        )
        
        if response.get('Items'):
            latest_conv = response['Items'][0]
            latest_timestamp = datetime.fromisoformat(latest_conv.get('timestamp', '').replace('Z', '+00:00'))
            current_time = datetime.utcnow()
            
            # If the last conversation in this topic was within 30 minutes, use the same thread
            if (current_time - latest_timestamp).total_seconds() < 1800:  # 30 minutes
                return latest_conv.get('thread_id', f"thread_{user_id}_{topic}_{int(current_time.timestamp())}")
        
        # Create a new thread for this topic
        return f"thread_{user_id}_{topic}_{int(datetime.utcnow().timestamp())}"
        
    except Exception as e:
        print(f"Error managing thread ID: {str(e)}")
        # Fallback to a simple thread ID
        return f"thread_{user_id}_{topic}_{int(datetime.utcnow().timestamp())}"

def create_reminder(user_id, reminder_text, due_date=None, reminder_type="general"):
    """Create a persistent reminder for the user"""
    try:
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        
        reminder_id = f"rem_{int(datetime.utcnow().timestamp())}"
        
        # If no due date, set to 24 hours from now
        if not due_date:
            due_date = (datetime.utcnow().timestamp() + 86400) * 1000  # 24 hours in milliseconds
        
        reminder_item = {
            'user_id': user_id,
            'reminder_id': reminder_id,
            'reminder_text': reminder_text,
            'due_date': str(int(due_date)),
            'reminder_type': reminder_type,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'pending',
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
        }
        
        reminders_table.put_item(Item=reminder_item)
        print(f"Reminder created: {reminder_id}")
        return reminder_id
        
    except Exception as e:
        print(f"Error creating reminder: {str(e)}")
        return None

def get_due_reminders(user_id):
    """Get reminders that are due now or overdue"""
    try:
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        
        current_time = int(datetime.utcnow().timestamp() * 1000)  # Current time in milliseconds
        
        # Query for reminders due before now
        response = reminders_table.query(
            KeyConditionExpression='user_id = :user_id',
            FilterExpression='due_date <= :current_time AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':current_time': str(current_time),
                ':status': 'pending'
            },
            ScanIndexForward=True  # Oldest first
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error getting due reminders: {str(e)}")
        return []

def get_next_reminder(user_id):
    """Get the next upcoming reminder for countdown display"""
    try:
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        
        current_time = int(datetime.utcnow().timestamp() * 1000)  # Current time in milliseconds
        
        # Query for future reminders
        response = reminders_table.query(
            KeyConditionExpression='user_id = :user_id',
            FilterExpression='due_date > :current_time AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':current_time': str(current_time),
                ':status': 'pending'
            },
            ScanIndexForward=True,  # Earliest first
            Limit=1  # Only get the next one
        )
        
        items = response.get('Items', [])
        if items:
            reminder = items[0]
            due_timestamp = int(reminder.get('due_date', 0))
            time_until = due_timestamp - current_time
            
            return {
                'reminder_text': reminder.get('reminder_text', ''),
                'due_timestamp': due_timestamp,
                'time_until_seconds': max(0, time_until // 1000),  # Convert to seconds
                'due_date_formatted': datetime.fromtimestamp(due_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        
        return None
        
    except Exception as e:
        print(f"Error getting next reminder: {str(e)}")
        return None

def mark_reminder_completed(reminder_id, user_id):
    """Mark a reminder as completed"""
    try:
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        
        reminders_table.update_item(
            Key={
                'user_id': user_id,
                'reminder_id': reminder_id
            },
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'completed'}
        )
        
        print(f"Reminder marked as completed: {reminder_id}")
        return True
        
    except Exception as e:
        print(f"Error marking reminder as completed: {str(e)}")
        return False

# Admin functions
def verify_admin_key(admin_key):
    """Verify admin API key"""
    expected_key = os.environ.get('ADMIN_API_KEY', 'admin-key-2024')
    return admin_key == expected_key

def create_user_profile(email, name, role='user', notes=''):
    """Create a new user profile in DynamoDB"""
    try:
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        
        # Generate user ID
        user_id = f"user_{int(datetime.utcnow().timestamp())}"
        
        user_item = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'role': role,
            'notes': notes,
            'created_at': datetime.utcnow().isoformat(),
            'last_active': None,
            'status': 'active',
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 365))  # 1 year TTL
        }
        
        users_table.put_item(Item=user_item)
        print(f"User profile created: {user_id}")
        return user_id
        
    except Exception as e:
        print(f"Error creating user profile: {str(e)}")
        return None

def get_all_users():
    """Get all users from DynamoDB"""
    try:
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        
        response = users_table.scan()
        users = response.get('Items', [])
        
        # Get additional stats for each user
        for user in users:
            user_id = user['user_id']
            
            # Get conversation count
            conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
            conv_response = conversations_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            user['conversation_count'] = len(conv_response.get('Items', []))
            
            # Get reminder count
            reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
            rem_response = reminders_table.query(
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':user_id': user_id, ':status': 'pending'}
            )
            user['reminder_count'] = len(rem_response.get('Items', []))
            
            # Get task count
            tasks_table = dynamodb.Table(os.environ.get('TASKS_TABLE_NAME', 'aiassistant-dev-tasks'))
            task_response = tasks_table.query(
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':user_id': user_id, ':status': 'pending'}
            )
            user['task_count'] = len(task_response.get('Items', []))
        
        return users
        
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return []

def get_user_by_id(user_id):
    """Get a specific user by ID"""
    try:
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        
        response = users_table.get_item(Key={'user_id': user_id})
        user = response.get('Item')
        
        if user:
            # Get additional stats
            conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
            conv_response = conversations_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            user['conversation_count'] = len(conv_response.get('Items', []))
            
            reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
            rem_response = reminders_table.query(
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':user_id': user_id, ':status': 'pending'}
            )
            user['reminder_count'] = len(rem_response.get('Items', []))
            
            tasks_table = dynamodb.Table(os.environ.get('TASKS_TABLE_NAME', 'aiassistant-dev-tasks'))
            task_response = tasks_table.query(
                KeyConditionExpression='user_id = :user_id',
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':user_id': user_id, ':status': 'pending'}
            )
            user['task_count'] = len(task_response.get('Items', []))
        
        return user
        
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None

def delete_user(user_id):
    """Delete a user and all their data"""
    try:
        # Delete from users table
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        users_table.delete_item(Key={'user_id': user_id})
        
        # Delete conversations
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        conv_response = conversations_table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        for item in conv_response.get('Items', []):
            conversations_table.delete_item(Key={
                'user_id': item['user_id'],
                'conversation_id': item['conversation_id']
            })
        
        # Delete reminders
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        rem_response = reminders_table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        for item in rem_response.get('Items', []):
            reminders_table.delete_item(Key={
                'user_id': item['user_id'],
                'reminder_id': item['reminder_id']
            })
        
        # Delete tasks
        tasks_table = dynamodb.Table(os.environ.get('TASKS_TABLE_NAME', 'aiassistant-dev-tasks'))
        task_response = tasks_table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        for item in task_response.get('Items', []):
            tasks_table.delete_item(Key={
                'user_id': item['user_id'],
                'task_id': item['task_id']
            })
        
        print(f"User {user_id} and all associated data deleted")
        return True
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return False

def get_system_stats():
    """Get system statistics"""
    try:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'total_conversations': 0,
            'total_reminders': 0
        }
        
        # Count users
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'aiassistant-dev-users'))
        users_response = users_table.scan()
        stats['total_users'] = len(users_response.get('Items', []))
        
        # Count active users (last 24 hours)
        active_cutoff = datetime.utcnow().timestamp() - 86400
        for user in users_response.get('Items', []):
            if user.get('last_active'):
                last_active = datetime.fromisoformat(user['last_active'].replace('Z', '+00:00'))
                if last_active.timestamp() > active_cutoff:
                    stats['active_users'] += 1
        
        # Count conversations
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        conv_response = conversations_table.scan()
        stats['total_conversations'] = len(conv_response.get('Items', []))
        
        # Count active reminders
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        rem_response = reminders_table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'pending'}
        )
        stats['total_reminders'] = len(rem_response.get('Items', []))
        
        return stats
        
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return {'total_users': 0, 'active_users': 0, 'total_conversations': 0, 'total_reminders': 0}

def cleanup_old_data():
    """Clean up old data (conversations and reminders older than 30 days)"""
    try:
        cutoff_time = datetime.utcnow().timestamp() - (86400 * 30)  # 30 days ago
        cleaned_items = 0
        
        # Clean up old conversations
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        conv_response = conversations_table.scan()
        for item in conv_response.get('Items', []):
            item_time = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).timestamp()
            if item_time < cutoff_time:
                conversations_table.delete_item(Key={
                    'user_id': item['user_id'],
                    'conversation_id': item['conversation_id']
                })
                cleaned_items += 1
        
        # Clean up old completed reminders
        reminders_table = dynamodb.Table(os.environ.get('REMINDERS_TABLE_NAME', 'aiassistant-dev-reminders'))
        rem_response = reminders_table.scan()
        for item in rem_response.get('Items', []):
            if item.get('status') == 'completed':
                item_time = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')).timestamp()
                if item_time < cutoff_time:
                    reminders_table.delete_item(Key={
                        'user_id': item['user_id'],
                        'reminder_id': item['reminder_id']
                    })
                    cleaned_items += 1
        
        return cleaned_items
        
    except Exception as e:
        print(f"Error cleaning up data: {str(e)}")
        return 0

def handle_admin_request(event, context):
    """Handle admin API requests"""
    try:
        # Verify admin API key (check both cases)
        headers = event.get('headers', {})
        admin_key = headers.get('X-Admin-Key', '') or headers.get('x-admin-key', '')
        if not verify_admin_key(admin_key):
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': json.dumps({'error': 'Invalid admin API key'})
            }
        
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        # Route admin requests
        if path == '/admin/users' and method == 'GET':
            # Get all users
            users = get_all_users()
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': json.dumps({'users': users})
            }
        
        elif path == '/admin/users' and method == 'POST':
            # Create new user
            body = json.loads(event.get('body', '{}'))
            email = body.get('email', '')
            name = body.get('name', '')
            role = body.get('role', 'user')
            notes = body.get('notes', '')
            
            if not email:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Email is required'})
                }
            
            user_id = create_user_profile(email, name, role, notes)
            if user_id:
                return {
                    'statusCode': 201,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'message': 'User created successfully', 'user_id': user_id})
                }
            else:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Failed to create user'})
                }
        
        elif path.startswith('/admin/users/') and method == 'GET':
            # Get specific user
            user_id = path.split('/')[-1]
            user = get_user_by_id(user_id)
            if user:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'user': user})
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'User not found'})
                }
        
        elif path.startswith('/admin/users/') and method == 'DELETE':
            # Delete user
            user_id = path.split('/')[-1]
            if delete_user(user_id):
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'message': 'User deleted successfully'})
                }
            else:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Failed to delete user'})
                }
        
        elif path == '/admin/stats' and method == 'GET':
            # Get system statistics
            stats = get_system_stats()
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': json.dumps(stats)
            }
        
        elif path == '/admin/knowledge' and method == 'GET':
            # Get all admin knowledge
            try:
                admin_knowledge_table = dynamodb.Table(os.environ.get('ADMIN_KNOWLEDGE_TABLE_NAME', 'aiassistant-dev-admin-knowledge'))
                response = admin_knowledge_table.scan()
                knowledge_items = response.get('Items', [])
                
                # Sort by creation date (newest first)
                knowledge_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'knowledge': knowledge_items})
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': f'Failed to retrieve knowledge: {str(e)}'})
                }
        
        elif path == '/admin/knowledge' and method == 'POST':
            # Add new admin knowledge
            try:
                body = json.loads(event.get('body', '{}'))
                knowledge_text = body.get('knowledge', '').strip()
                
                if not knowledge_text:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                        },
                        'body': json.dumps({'error': 'Knowledge text is required'})
                    }
                
                if save_admin_knowledge(knowledge_text, dynamodb):
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                        },
                        'body': json.dumps({'message': 'Knowledge added successfully'})
                    }
                else:
                    return {
                        'statusCode': 500,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                        },
                        'body': json.dumps({'error': 'Failed to save knowledge'})
                    }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': f'Failed to add knowledge: {str(e)}'})
                }
        
        elif path.startswith('/admin/knowledge/') and method == 'DELETE':
            # Delete admin knowledge
            try:
                knowledge_id = path.split('/')[-1]
                admin_knowledge_table = dynamodb.Table(os.environ.get('ADMIN_KNOWLEDGE_TABLE_NAME', 'aiassistant-dev-admin-knowledge'))
                
                admin_knowledge_table.delete_item(
                    Key={'knowledge_id': knowledge_id}
                )
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'message': 'Knowledge deleted successfully'})
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': f'Failed to delete knowledge: {str(e)}'})
                }
        
        elif path == '/admin/cleanup' and method == 'POST':
            # Clean up old data
            cleaned_items = cleanup_old_data()
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': json.dumps({'message': 'Cleanup completed', 'cleaned_items': cleaned_items})
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': json.dumps({'error': 'Admin endpoint not found'})
            }
    
    except Exception as e:
        print(f"Error handling admin request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_admin_status_check(event, context):
    """Handle admin status check request"""
    try:
        # Extract and verify JWT token
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({'error': 'No valid authorization header'})
            }
        
        token = auth_header.split(' ')[1]
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        
        # Verify JWT token
        payload = verify_jwt_token(token, user_pool_id)
        if not payload:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        user_id = payload.get('sub')
        if not user_id:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({'error': 'No user ID in token'})
            }
        
        # Check if user is admin
        is_admin = is_user_admin(user_id, dynamodb)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps({
                'is_admin': is_admin,
                'user_id': user_id
            })
        }
        
    except Exception as e:
        print(f"Error in admin status check: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def handler(event, context):
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
                    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
                },
                'body': ''
            }
        
        print(f"Event: {json.dumps(event)}")
        
        # Check if this is an admin request
        path = event.get('path', '')
        if path == '/admin/check-status':
            return handle_admin_status_check(event, context)
        elif path.startswith('/admin'):
            return handle_admin_request(event, context)
        
        # Regular chatbot request
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '')
        start_new_thread = body.get('start_new_thread', False)
        topic = body.get('topic', 'General')
        
        if not user_message:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'No message provided'})
            }
        
        # Extract and verify JWT token
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'No valid authorization token provided'})
            }
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID', '')
        
        if not user_pool_id:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'User pool configuration missing'})
            }
        
        # Verify JWT token and get user info
        user_payload = verify_jwt_token(token, user_pool_id)
        if not user_payload:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'Invalid or expired token'})
            }
        
        # Extract user information from JWT payload
        user_id = user_payload.get('sub', 'unknown')
        username = user_payload.get('cognito:username', user_payload.get('username', 'unknown'))
        email = user_payload.get('email', '')
        
        print(f"Authenticated user: {username} ({user_id})")
        
        # Get conversation history for context (unless starting new thread)
        conversation_history = [] if start_new_thread else get_conversation_history(user_id, dynamodb, topic)
        
        # Check for due reminders and add them to context
        due_reminders = get_due_reminders(user_id)
        next_reminder = get_next_reminder(user_id)
        
        reminder_context = ""
        if due_reminders:
            reminder_context = "\n\n🔔 REMINDERS:\n"
            for reminder in due_reminders:
                reminder_context += f"- {reminder.get('reminder_text', '')}\n"
            reminder_context += "\nPlease acknowledge these reminders in your response.\n"
        
        # Check for admin knowledge commands (only for admin users)
        admin_knowledge_saved = False
        if is_admin_knowledge_command(user_message):
            # Check if user is admin
            if is_user_admin(user_id, dynamodb):
                knowledge_to_save = extract_knowledge_from_command(user_message)
                if knowledge_to_save:
                    admin_knowledge_saved = save_admin_knowledge(knowledge_to_save, dynamodb)
                    if admin_knowledge_saved:
                        print(f"Admin knowledge saved by admin user {user_id}: {knowledge_to_save}")
            else:
                print(f"Non-admin user {user_id} attempted to set admin knowledge: {user_message}")
                # Don't save the knowledge, but continue processing the message normally
        
        # Check for budget tracking commands (only for admin users)
        budget_saved = False
        budget_info = None
        if is_budget_command(user_message):
            # Check if user is admin
            if is_user_admin(user_id, dynamodb):
                budget_info = extract_budget_info(user_message)
                if budget_info and budget_info.get('amount'):
                    budget_saved = save_budget_entry(user_id, budget_info, dynamodb)
                    if budget_saved:
                        print(f"Budget entry saved by admin user {user_id}: ${budget_info['amount']} on {budget_info['category']}")
            else:
                print(f"Non-admin user {user_id} attempted to track budget: {user_message}")
                # Don't save the budget, but continue processing the message normally
        
        # Get admin permanent knowledge
        admin_knowledge = get_admin_knowledge(dynamodb)
        
        # Get budget summary if user is admin and asking about budget
        budget_summary = None
        if is_user_admin(user_id, dynamodb) and any(word in user_message.lower() for word in ['budget', 'spending', 'expenses', 'total', 'summary', 'tally']):
            budget_summary = get_budget_summary('BetterBubble', dynamodb)
        
        # Search the web for ALL questions to get relevant references
        print(f"Searching the web for: {user_message}")
        # Enable deep research for comprehensive knowledge building
        web_search_results = search_web_for_query(user_message, user_id, topic, max_results=8, enable_deep_research=True)
        print(f"Web search found {len(web_search_results)} results")
        
        # Prepare the prompt for Claude with conversation context and reminders
        prompt = build_conversation_prompt(user_message, conversation_history, reminder_context, web_search_results, admin_knowledge, budget_info, budget_summary)
        
        # Try to invoke Claude 3.5 Haiku model using the system-defined inference profile
        try:
            # Use the system-defined inference profile ARN for Claude 3.5 Haiku
            inference_profile_arn = 'arn:aws:bedrock:us-west-2:166199670697:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0'
            print(f"Using inference profile ARN: {inference_profile_arn}")
            
            response = bedrock.invoke_model(
                modelId=inference_profile_arn,
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1000,
                    'temperature': 0.7,
                    'messages': prompt  # Use the conversation context
                }),
                contentType='application/json'
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            ai_response = response_body.get('content', [{}])[0].get('text', 'Sorry, I could not generate a response.')
            
        except Exception as e:
            print(f"Error invoking Bedrock: {str(e)}")
            ai_response = "I'm sorry, I'm having trouble connecting to my AI service right now. Please try again in a moment."
        
        # Check if user is asking for a reminder and create one
        reminder_created = None
        if any(phrase in user_message.lower() for phrase in ['remind me to', 'don\'t forget to', 'i need to remember', 'set a reminder for']):
            reminder_created = create_reminder(user_id, user_message)
            if reminder_created:
                ai_response += f"\n\n✅ I've created a reminder for you! I'll remind you about this when it's time."
        
        # Store conversation in DynamoDB (with error handling)
        try:
            conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
            
            # Generate a unique conversation ID for this interaction
            conversation_id = f"conv_{int(datetime.utcnow().timestamp())}"
            
            # Generate or get thread ID for grouping related conversations
            thread_id = f"thread_{user_id}_{topic}_{int(datetime.utcnow().timestamp())}" if start_new_thread else get_or_create_thread_id(user_id, dynamodb, topic)
            
            conversation_item = {
                'user_id': user_id,
                'conversation_id': conversation_id,
                'thread_id': thread_id,
                'topic': topic,
                'timestamp': datetime.utcnow().isoformat(),
                'user_message': user_message,
                'ai_response': ai_response,
                'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
            }
            
            conversations_table.put_item(Item=conversation_item)
            print(f"Conversation stored successfully: {conversation_id}")
        except Exception as db_error:
            print(f"DynamoDB storage error: {str(db_error)}")
            # Continue without storing - don't fail the entire request
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'response': ai_response,
                'user_id': user_id,
                'thread_id': thread_id,
                'topic': topic,
                'timestamp': conversation_item['timestamp'],
                'reminder_created': reminder_created,
                'due_reminders_count': len(due_reminders),
                'next_reminder': next_reminder
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
