# 🧠 Conversation Memory System

Your AI assistant now has **conversation memory**! It can remember previous messages and provide context-aware responses.

## ✨ **Features**

### **Automatic Memory**
- ✅ **Remembers last 10 conversations** per user
- ✅ **Context-aware responses** using conversation history
- ✅ **Thread-based grouping** for related conversations
- ✅ **30-day retention** with automatic cleanup
- ✅ **Per-user isolation** - each user has their own memory

### **Smart Threading**
- 🔄 **Auto-threading**: New conversations within 30 minutes join the same thread
- 🆕 **New thread**: Conversations after 30+ minutes start a fresh thread
- 🎯 **Manual control**: Frontend can force new threads with `start_new_thread: true`

## 🔧 **How It Works**

### **1. Conversation Storage**
```json
{
  "user_id": "user123",
  "conversation_id": "conv_1703123456",
  "thread_id": "thread_user123_1703123456",
  "timestamp": "2024-01-01T12:00:00Z",
  "user_message": "What's the weather like?",
  "ai_response": "I don't have access to real-time weather data...",
  "ttl": 1705715456
}
```

### **2. Context Retrieval**
- Queries DynamoDB for recent conversations
- Includes last 5 message exchanges for context
- Builds conversation history for Claude

### **3. Thread Management**
- **Same thread**: Messages within 30 minutes
- **New thread**: Messages after 30+ minutes
- **Manual override**: `start_new_thread: true` in request

## 📡 **API Usage**

### **Normal Conversation (with memory)**
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: "What did I ask you about earlier?"
  })
});
```

### **Start New Thread (no memory)**
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: "Let's start fresh",
    start_new_thread: true
  })
});
```

### **Response Format**
```json
{
  "response": "AI response text",
  "user_id": "user123",
  "thread_id": "thread_user123_1703123456",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🗄️ **Database Schema**

### **Conversations Table**
- **Partition Key**: `user_id` (String)
- **Sort Key**: `conversation_id` (String)
- **Attributes**:
  - `thread_id`: Groups related conversations
  - `timestamp`: When the conversation occurred
  - `user_message`: What the user said
  - `ai_response`: What the AI responded
  - `ttl`: Auto-deletion timestamp (30 days)

## 💰 **Cost Impact**

### **DynamoDB Costs**
- **Storage**: ~$0.25 per GB per month
- **Reads**: ~$0.25 per million reads
- **Writes**: ~$1.25 per million writes
- **Estimated**: <$1/month for typical usage

### **Lambda Costs**
- **Memory**: Slight increase for conversation retrieval
- **Duration**: +50-100ms per request
- **Free Tier**: Still within limits

## 🔒 **Privacy & Security**

### **Data Isolation**
- ✅ Each user only sees their own conversations
- ✅ JWT token verification required
- ✅ Encrypted at rest with KMS
- ✅ 30-day automatic deletion

### **No Cross-User Access**
- ✅ User A cannot see User B's conversations
- ✅ Thread IDs are user-specific
- ✅ DynamoDB queries are user-scoped

## 🚀 **Frontend Integration**

### **Display Conversation History**
```javascript
// Show conversation in UI
function displayMessage(data) {
  const messageDiv = document.createElement('div');
  messageDiv.innerHTML = `
    <div class="message user">${data.user_message}</div>
    <div class="message ai">${data.response}</div>
    <div class="timestamp">${new Date(data.timestamp).toLocaleString()}</div>
  `;
  chatContainer.appendChild(messageDiv);
}
```

### **Thread Management**
```javascript
// Start new conversation thread
function startNewThread() {
  currentThreadId = null; // Reset thread tracking
  // Send start_new_thread: true with next message
}
```

## 🧪 **Testing**

### **Test Conversation Memory**
1. Send message: "My name is John"
2. Send message: "What's my name?"
3. AI should respond: "Your name is John"

### **Test Thread Management**
1. Send message: "Hello"
2. Wait 31+ minutes
3. Send message: "Do you remember me?"
4. AI should not remember the "Hello" (new thread)

## 🔧 **Configuration**

### **Environment Variables**
- `CONVERSATIONS_TABLE_NAME`: DynamoDB table name
- `COGNITO_USER_POOL_ID`: User pool for authentication

### **Tunable Parameters**
- **Memory limit**: Currently 10 conversations (in code)
- **Thread timeout**: Currently 30 minutes (in code)
- **TTL**: Currently 30 days (in code)

## 📊 **Monitoring**

### **CloudWatch Metrics**
- DynamoDB read/write capacity
- Lambda duration and errors
- API Gateway request count

### **Logs to Watch**
- Conversation storage success/failure
- Thread ID generation
- Memory retrieval errors

---

**Your AI assistant now has human-like memory! 🎉**
