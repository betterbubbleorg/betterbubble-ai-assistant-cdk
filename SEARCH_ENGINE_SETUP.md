# Search Engine Setup Guide

Your AI assistant now has **dual search engine support** for comprehensive internet access! The system uses both DuckDuckGo and Google Knowledge Graph together to provide the best results.

## 🦆 DuckDuckGo (Active - FREE)

**Status**: ✅ Already configured and working
- **Cost**: Free
- **Rate Limit**: No official limit (be respectful)
- **Setup**: No API key needed
- **Quality**: Good for general searches
- **Purpose**: General web search, news, articles

**Current Configuration**:
```bash
SEARCH_ENGINES=duckduckgo,google_kg
SEARCH_QUERIES=AI news,technology updates,programming tutorials,latest tech trends
```

## 🧠 Google Knowledge Graph (Active - FREE)

**Status**: ✅ Already configured and working
- **Cost**: 100,000 requests/day free
- **Rate Limit**: 100,000 requests/day
- **Setup**: Uses your existing Google API key
- **Quality**: Excellent for structured data and facts
- **Purpose**: Entity information, facts, relationships

**Current Configuration**:
```bash
SEARCH_ENGINES=duckduckgo,google_kg
GOOGLE_API_KEY_PARAM=/aiassistant-dev-bedrock/search/google-api-key
```

## 🔍 Google Custom Search API

**Status**: Requires setup
- **Cost**: 100 free searches/day, then $5 per 1,000 queries
- **Rate Limit**: 10,000 queries/day
- **Quality**: Excellent results
- **Setup Required**:

### Step 1: Create Google Custom Search Engine
1. Go to [Google Custom Search](https://cse.google.com/cse/)
2. Click "Add" to create a new search engine
3. Enter `*` in "Sites to search" (searches entire web)
4. Click "Create"
5. Note your **Search Engine ID** (cx parameter)

### Step 2: Get API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Custom Search API"
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy your **API Key**

### Step 3: Update Lambda Environment
```bash
aws lambda update-function-configuration \
  --function-name aiassistant-dev-bedrock-document-processor \
  --environment Variables='{
    "BUCKET_NAME":"betterbubble-kb-166199670697-us-west-2",
    "SEARCH_ENGINE":"google",
    "GOOGLE_API_KEY":"YOUR_API_KEY_HERE",
    "GOOGLE_SEARCH_ENGINE_ID":"YOUR_SEARCH_ENGINE_ID_HERE",
    "SEARCH_QUERIES":"AI news,technology updates,programming tutorials,latest tech trends"
  }'
```

## 🔍 Bing Search API

**Status**: Requires setup
- **Cost**: 1,000 free queries/month, then $5 per 1,000 queries
- **Rate Limit**: 1,000 queries/month free
- **Quality**: Good results
- **Setup Required**:

### Step 1: Get Bing API Key
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create a new "Bing Search v7" resource
3. Choose "Free" pricing tier
4. Copy your **API Key**

### Step 2: Update Lambda Environment
```bash
aws lambda update-function-configuration \
  --function-name aiassistant-dev-bedrock-document-processor \
  --environment Variables='{
    "BUCKET_NAME":"betterbubble-kb-166199670697-us-west-2",
    "SEARCH_ENGINE":"bing",
    "BING_API_KEY":"YOUR_BING_API_KEY_HERE",
    "SEARCH_QUERIES":"AI news,technology updates,programming tutorials,latest tech trends"
  }'
```

## 🎯 Customizing Search Queries

You can customize what your AI assistant searches for by updating the `SEARCH_QUERIES` environment variable:

```bash
# Example: Focus on specific topics
SEARCH_QUERIES="AWS Lambda updates,Python programming,AI research papers,cloud computing news"

# Example: Industry-specific searches
SEARCH_QUERIES="fintech news,blockchain updates,cryptocurrency trends,DeFi developments"

# Example: Technology stack searches
SEARCH_QUERIES="React.js updates,Node.js news,TypeScript tutorials,JavaScript frameworks"
```

## 📊 Cost Comparison

| Search Engine | Free Tier | Paid Cost | Best For |
|---------------|-----------|-----------|----------|
| DuckDuckGo | Unlimited* | Free | Privacy, general use |
| Google Custom Search | 100/day | $5/1K queries | High-quality results |
| Bing Search | 1K/month | $5/1K queries | Microsoft ecosystem |

*DuckDuckGo has no official limits but be respectful with requests

## 🔧 Testing Your Setup

Test your search configuration:

```bash
# Test current configuration
aws lambda invoke --function-name aiassistant-dev-bedrock-document-processor --payload '{}' response.json && cat response.json

# Check CloudWatch logs for detailed output
aws logs tail /aws/lambda/aiassistant-dev-bedrock-document-processor --follow
```

## 🚀 Recommended Setup

For the best balance of cost and quality:

1. **Start with DuckDuckGo** (already working)
2. **Add Google Custom Search** for high-quality results when needed
3. **Use Bing** if you need more free queries than Google

## 📈 Monitoring Usage

Check your search usage:

```bash
# Check Lambda logs for search results
aws logs filter-log-events \
  --log-group-name /aws/lambda/aiassistant-dev-bedrock-document-processor \
  --filter-pattern "Found" \
  --start-time $(date -d '1 hour ago' +%s)000
```

## 🔄 Switching Between Search Engines

You can switch search engines without redeploying by updating the Lambda environment variables:

```bash
# Switch to Google
aws lambda update-function-configuration \
  --function-name aiassistant-dev-bedrock-document-processor \
  --environment Variables='{
    "BUCKET_NAME":"betterbubble-kb-166199670697-us-west-2",
    "SEARCH_ENGINE":"google",
    "GOOGLE_API_KEY":"YOUR_KEY",
    "GOOGLE_SEARCH_ENGINE_ID":"YOUR_ID",
    "SEARCH_QUERIES":"AI news,technology updates,programming tutorials,latest tech trends"
  }'

# Switch back to DuckDuckGo
aws lambda update-function-configuration \
  --function-name aiassistant-dev-bedrock-document-processor \
  --environment Variables='{
    "BUCKET_NAME":"betterbubble-kb-166199670697-us-west-2",
    "SEARCH_ENGINE":"duckduckgo",
    "SEARCH_QUERIES":"AI news,technology updates,programming tutorials,latest tech trends"
  }'
```

Your AI assistant now has access to real-time information from the entire web! 🎉
