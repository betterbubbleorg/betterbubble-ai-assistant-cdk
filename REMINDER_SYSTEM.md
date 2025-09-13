# 🔔 AI Assistant Reminder System

Your AI assistant now has **persistent reminder capabilities**! It can remember things across sessions and remind you when it's time.

## ✨ **Features**

### **Automatic Reminder Creation**
- ✅ **Natural Language**: "Remind me to call mom tomorrow"
- ✅ **Smart Detection**: Recognizes reminder phrases automatically
- ✅ **Cross-Session Memory**: Reminders persist across different chat sessions
- ✅ **Due Date Tracking**: Reminders trigger when they're due
- ✅ **Per-User Isolation**: Each user has their own reminders

### **Reminder Types**
- 🔔 **General Reminders**: "Remind me to..."
- 📅 **Time-Based**: "Don't forget to..." (defaults to 24 hours)
- 🎯 **Task Reminders**: "I need to remember..."
- ⏰ **Custom Timing**: "Set a reminder for..."

## 🚀 **How It Works**

### **1. Creating Reminders**
Just talk naturally to your AI assistant:

```
You: "Remind me to call the dentist tomorrow"
AI: "I'll help you with that! [response] + ✅ I've created a reminder for you! I'll remind you about this when it's time."

You: "Don't forget to buy milk"
AI: "Got it! [response] + ✅ I've created a reminder for you! I'll remind you about this when it's time."
```

### **2. Getting Reminded**
When you start a new conversation, the AI will automatically check for due reminders:

```
You: "Hello"
AI: "Hello! How can I help you today?

🔔 REMINDERS:
- Call the dentist tomorrow
- Buy milk

I see you have some reminders that are due. Would you like me to help you with any of these?"
```

### **3. Reminder Management**
- **Auto-Creation**: Reminders are created automatically when you use reminder phrases
- **Auto-Display**: Due reminders are shown at the start of conversations
- **Auto-Cleanup**: Completed reminders are marked as done
- **30-Day TTL**: Old reminders are automatically deleted

## 📡 **API Usage**

### **Creating Reminders (Automatic)**
```javascript
// Just send a normal message with reminder phrases
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: "Remind me to check the weather tomorrow"
  })
});

// Response includes reminder info
const data = await response.json();
console.log(data.reminder_created); // "rem_1703123456"
console.log(data.due_reminders_count); // 2
```

### **Response Format**
```json
{
  "response": "AI response text",
  "user_id": "user123",
  "thread_id": "thread_user123_1703123456",
  "timestamp": "2024-01-01T12:00:00Z",
  "reminder_created": "rem_1703123456",
  "due_reminders_count": 2
}
```

## 🗄️ **Database Schema**

### **Reminders Table**
- **Partition Key**: `user_id` (String)
- **Sort Key**: `reminder_id` (String)
- **Attributes**:
  - `reminder_text`: What to remind about
  - `due_date`: When to remind (timestamp)
  - `reminder_type`: Type of reminder
  - `created_at`: When created
  - `status`: pending/completed
  - `ttl`: Auto-deletion timestamp

### **GSI: due-date-index**
- **Partition Key**: `user_id`
- **Sort Key**: `due_date`
- **Purpose**: Efficient querying of due reminders

## 🧠 **Smart Features**

### **Natural Language Processing**
The AI recognizes these phrases and creates reminders:
- "Remind me to..."
- "Don't forget to..."
- "I need to remember..."
- "Set a reminder for..."

### **Context Awareness**
- Reminders are created with the full context of your message
- The AI understands what you want to be reminded about
- Reminders include the original request for clarity

### **Timing Intelligence**
- **Default**: 24 hours from creation
- **Smart Parsing**: "tomorrow", "next week", "in 2 hours"
- **Flexible**: Can be extended with more sophisticated time parsing

## 💰 **Cost Impact**

### **DynamoDB Costs**
- **Storage**: ~$0.25 per GB per month
- **Reads**: ~$0.25 per million reads (checking due reminders)
- **Writes**: ~$1.25 per million writes (creating reminders)
- **Estimated**: <$0.50/month for typical usage

### **Lambda Costs**
- **Memory**: Slight increase for reminder processing
- **Duration**: +50-100ms per request
- **Free Tier**: Still within limits

## 🔒 **Privacy & Security**

### **Data Isolation**
- ✅ Each user only sees their own reminders
- ✅ JWT token verification required
- ✅ Encrypted at rest with KMS
- ✅ 30-day automatic deletion

### **No Cross-User Access**
- ✅ User A cannot see User B's reminders
- ✅ Reminder IDs are user-specific
- ✅ DynamoDB queries are user-scoped

## 🧪 **Testing the System**

### **Test 1: Create a Reminder**
1. Send: "Remind me to test this system"
2. Check response for: "✅ I've created a reminder for you!"
3. Note the `reminder_created` field in response

### **Test 2: Get Reminded**
1. Wait a few minutes
2. Send: "Hello" (new conversation)
3. Check if reminder appears in response

### **Test 3: Multiple Reminders**
1. Create several reminders
2. Start new conversation
3. Verify all due reminders are shown

## 🔧 **Configuration**

### **Environment Variables**
- `REMINDERS_TABLE_NAME`: DynamoDB table name
- `CONVERSATIONS_TABLE_NAME`: For conversation context
- `COGNITO_USER_POOL_ID`: For user authentication

### **Tunable Parameters**
- **Default reminder time**: Currently 24 hours (in code)
- **Reminder phrases**: Configurable in `build_conversation_prompt`
- **TTL**: Currently 30 days (in code)
- **Max reminders per check**: Currently unlimited (in code)

## 📊 **Monitoring**

### **CloudWatch Metrics**
- DynamoDB read/write capacity for reminders
- Lambda duration and errors
- Reminder creation success rate

### **Logs to Watch**
- "Reminder created: rem_xxx"
- "Reminder marked as completed: rem_xxx"
- "Error creating reminder: ..."

## 🚀 **Frontend Integration**

### **Display Reminders**
```javascript
// Show reminder notifications
function displayReminders(data) {
  if (data.due_reminders_count > 0) {
    showNotification(`You have ${data.due_reminders_count} reminders!`);
  }
  
  if (data.reminder_created) {
    showSuccess("Reminder created successfully!");
  }
}
```

### **Reminder UI**
```javascript
// Add reminder button to chat interface
function addReminderButton() {
  const reminderBtn = document.createElement('button');
  reminderBtn.textContent = '🔔 Set Reminder';
  reminderBtn.onclick = () => {
    const text = prompt('What would you like to be reminded about?');
    if (text) {
      sendMessage(`Remind me to ${text}`);
    }
  };
  chatContainer.appendChild(reminderBtn);
}
```

## 🎯 **Use Cases**

### **Personal Reminders**
- "Remind me to call mom this weekend"
- "Don't forget to pick up groceries"
- "I need to remember to book that appointment"

### **Work Reminders**
- "Remind me to follow up with the client"
- "Don't forget the team meeting at 3pm"
- "Set a reminder to review the proposal"

### **Health & Wellness**
- "Remind me to take my medication"
- "Don't forget to drink water"
- "I need to remember to exercise today"

---

**Your AI assistant now has persistent memory and can remind you of important things! 🎉**

The system is designed to be natural, secure, and cost-effective while providing powerful reminder capabilities across all your conversations.
