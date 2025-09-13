# BetterBubble AI Assistant - Complete System Documentation

## 🎯 **System Overview**

This is a comprehensive AI Personal Assistant system built on AWS with advanced features including web search, admin knowledge management, budget tracking, and multi-threaded conversations. The system is designed for BetterBubble organization with admin-only features and user management.

## 🏗️ **Architecture**

### **Core Components**
- **AI Assistant**: Bedrock-powered chatbot with web search capabilities
- **Admin Portal**: User management and knowledge control center
- **Budget Tracking**: Organization spending and expense management
- **Multi-Threaded Conversations**: Per-user topic management
- **Reminder System**: Persistent reminders with live countdown
- **Web Search Integration**: DuckDuckGo + Google Knowledge Graph

### **AWS Services Used**
- **Lambda**: Serverless compute for AI Assistant and Admin API
- **DynamoDB**: NoSQL database for users, conversations, reminders, budget, admin knowledge
- **Cognito**: User authentication and management
- **Bedrock**: AI/ML service for Claude 3.5 Haiku
- **S3**: Static website hosting and data storage
- **CloudFront**: CDN for global content delivery
- **API Gateway**: REST API endpoints
- **SSM Parameter Store**: Secure API key storage

## 🚀 **Deployment Status**

### **Current URLs**
- **Chatbot**: `https://chatbot.betterbubble.org`
- **Admin Portal**: `https://dlzki3kkd9171.cloudfront.net`
- **API Endpoint**: `https://myffqy5vnh.execute-api.us-west-2.amazonaws.com/prod`

### **Deployed Stacks**
- `aiassistant-dev-dynamodb` - Database tables
- `aiassistant-dev-cognito` - User authentication
- `aiassistant-dev-lambda` - AI Assistant and Admin API
- `aiassistant-dev-bedrock` - AI/ML services
- `aiassistant-dev-frontend` - Chatbot interface
- `aiassistant-dev-admin-frontend` - Admin portal
- `aiassistant-dev-cloudwatch` - Monitoring

## 🧠 **AI Assistant Features**

### **1. Web Search Integration**
- **Dual Search Engines**: DuckDuckGo (free) + Google Knowledge Graph
- **Deep Research**: Multi-phase searches with follow-up queries
- **Website Crawling**: Extracts detailed information from web pages
- **Search History**: Tracks previous searches to avoid repetition
- **Intelligent Iteration**: Cycles through different search results

### **2. Admin Knowledge System**
- **Permanent Knowledge**: Admin can set facts that override web search
- **Commands**: 
  - `"Remember that the sky is blue forever"`
  - `"Admin knowledge: BetterBubble AI is the most advanced"`
  - `"Permanently remember [anything]"`
- **Priority Override**: Admin knowledge always takes precedence
- **10-Year TTL**: Knowledge persists for a decade

### **3. Budget Tracking System**
- **Spending Tracking**: `"I spent $500 today on marketing"`
- **Duration Tracking**: `"This will cover 3 months"`
- **Category Management**: Automatic categorization of expenses
- **Organization Tally**: BetterBubble-wide budget tracking
- **Keyword Retrieval**: Search by category, amount, date
- **Admin-Only**: Only admin users can track spending

### **4. Multi-Threaded Conversations**
- **Topic Management**: Up to 3 parallel conversation threads per user
- **Per-User Isolation**: Each user has private conversation history
- **Smart Threading**: Automatic thread creation based on topics
- **Context Preservation**: Maintains conversation context within threads

### **5. Reminder System**
- **Natural Language**: `"Remind me to call John tomorrow"`
- **Persistent Storage**: Reminders survive across sessions
- **Live Countdown**: Real-time countdown to next reminder
- **Due Date Tracking**: Shows reminders when they're due
- **Auto-Cleanup**: 30-day TTL with automatic deletion

## 🔐 **Security & Access Control**

### **User Roles**
- **Admin Users**: Can set permanent knowledge, track budget, manage users
- **Regular Users**: Can use chatbot, set reminders, have conversations
- **Role Checking**: All admin functions verify user role in DynamoDB

### **Authentication**
- **Cognito JWT**: Secure token-based authentication
- **Admin Portal**: Uses `X-Admin-Key: admin-key-2024`
- **API Security**: All endpoints require proper authentication

### **Data Protection**
- **Encryption**: All data encrypted at rest with KMS
- **TTL**: Automatic data expiration for privacy
- **IAM Roles**: Least privilege access principles

## 📊 **Database Schema**

### **DynamoDB Tables**
1. **`aiassistant-dev-users`** - User profiles and roles
2. **`aiassistant-dev-conversations`** - Chat history and threads
3. **`aiassistant-dev-reminders`** - Reminder system
4. **`aiassistant-dev-tasks`** - Task management
5. **`aiassistant-dev-notes`** - Note storage
6. **`aiassistant-dev-appointments`** - Calendar events
7. **`aiassistant-dev-search-history`** - Web search tracking
8. **`aiassistant-dev-admin-knowledge`** - Permanent admin knowledge
9. **`aiassistant-dev-budget`** - Budget and expense tracking

### **Global Secondary Indexes**
- **Topic Index**: Query conversations by topic
- **Due Date Index**: Query reminders by due date
- **Organization Index**: Query budget by organization
- **Category Index**: Query budget by category

## 🛠️ **Admin Portal Features**

### **User Management**
- **Create Users**: Add new users with email and role
- **User Search**: Find users by email or name
- **Role Assignment**: Set admin vs regular user roles
- **User Details**: View user information and activity

### **Knowledge Management**
- **Add Knowledge**: Set permanent facts for the AI
- **View Knowledge**: See all admin-defined knowledge
- **Delete Knowledge**: Remove outdated information
- **Real-time Updates**: Changes apply immediately

### **System Statistics**
- **User Counts**: Total users, active users
- **Conversation Stats**: Total conversations, reminders
- **Data Cleanup**: Remove old data

## 💰 **Budget Tracking System**

### **Spending Commands**
- `"I spent $500 today on marketing"`
- `"Spent $1200 on software for 6 months"`
- `"Paid $300 for office supplies"`
- `"Bought $2000 worth of equipment"`

### **Budget Queries**
- `"Show me the budget summary"`
- `"What's our total spending?"`
- `"How much did we spend on marketing?"`
- `"Show recent expenses"`

### **Features**
- **Automatic Parsing**: Extracts amount, category, duration
- **Category Breakdown**: Groups expenses by category
- **Duration Tracking**: Tracks how long expenses cover
- **Organization Tally**: BetterBubble-wide spending totals
- **Recent Entries**: Shows last 10 expenses
- **Keyword Search**: Find expenses by category or description

## 🔧 **Technical Implementation**

### **Lambda Functions**
- **`ai_assistant`**: Main chatbot with all features
- **Admin API**: User management and knowledge control
- **Web Search**: DuckDuckGo and Google integration
- **Budget Processing**: Expense tracking and analysis

### **API Endpoints**
- **`POST /ai`**: Main chatbot endpoint
- **`GET /admin/users`**: List all users
- **`POST /admin/users`**: Create new user
- **`GET /admin/knowledge`**: List admin knowledge
- **`POST /admin/knowledge`**: Add admin knowledge
- **`DELETE /admin/knowledge/{id}`**: Delete knowledge

### **Environment Variables**
- **`CONVERSATIONS_TABLE_NAME`**: DynamoDB table for conversations
- **`REMINDERS_TABLE_NAME`**: DynamoDB table for reminders
- **`USERS_TABLE_NAME`**: DynamoDB table for users
- **`BUDGET_TABLE_NAME`**: DynamoDB table for budget
- **`ADMIN_KNOWLEDGE_TABLE_NAME`**: DynamoDB table for admin knowledge
- **`COGNITO_USER_POOL_ID`**: Cognito user pool ID
- **`ADMIN_API_KEY`**: Admin portal authentication key

## 🚀 **Deployment Commands**

### **Full Deployment**
```bash
cdk deploy --all --require-approval never
```

### **Individual Stacks**
```bash
cdk deploy aiassistant-dev-dynamodb
cdk deploy aiassistant-dev-cognito
cdk deploy aiassistant-dev-lambda
cdk deploy aiassistant-dev-admin-frontend
```

### **Update Lambda Code**
```bash
cdk deploy aiassistant-dev-lambda --require-approval never
```

## 🧪 **Testing the System**

### **1. Set Up Admin User**
```bash
curl -X POST https://myffqy5vnh.execute-api.us-west-2.amazonaws.com/prod/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: admin-key-2024" \
  -d '{"email": "adam@betterbubble.ai", "name": "Adam (Admin)", "role": "admin"}'
```

### **2. Test Admin Knowledge**
```bash
curl -X POST https://myffqy5vnh.execute-api.us-west-2.amazonaws.com/prod/ai \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "Remember that the sky is blue forever", "topic": "General"}'
```

### **3. Test Budget Tracking**
```bash
curl -X POST https://myffqy5vnh.execute-api.us-west-2.amazonaws.com/prod/ai \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "I spent $500 today on marketing for 3 months", "topic": "Finance"}'
```

### **4. Test Budget Summary**
```bash
curl -X POST https://myffqy5vnh.execute-api.us-west-2.amazonaws.com/prod/ai \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "Show me the budget summary", "topic": "Finance"}'
```

## 📝 **User Commands Reference**

### **Admin Knowledge Commands**
- `"Remember that [fact]"`
- `"Remember the [fact]"`
- `"Admin knowledge: [fact]"`
- `"Permanently remember [fact]"`
- `"Set knowledge: [fact]"`

### **Budget Tracking Commands**
- `"I spent $[amount] on [category]"`
- `"Spent $[amount] for [duration]"`
- `"Paid $[amount] for [description]"`
- `"Bought $[amount] worth of [item]"`

### **Budget Query Commands**
- `"Show budget summary"`
- `"What's our total spending?"`
- `"How much on [category]?"`
- `"Show recent expenses"`

### **Reminder Commands**
- `"Remind me to [task]"`
- `"Don't forget to [task]"`
- `"I need to remember [task]"`
- `"Set a reminder for [task]"`

## 🔍 **Troubleshooting**

### **Common Issues**
1. **Admin Knowledge Not Working**: Check if user has admin role
2. **Budget Tracking Failing**: Verify admin user setup
3. **Web Search Issues**: Check API keys in SSM Parameter Store
4. **Authentication Errors**: Verify JWT token validity

### **Debug Commands**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/aiassistant-dev-ai-assistant --follow

# Check DynamoDB tables
aws dynamodb scan --table-name aiassistant-dev-users
aws dynamodb scan --table-name aiassistant-dev-admin-knowledge
aws dynamodb scan --table-name aiassistant-dev-budget
```

## 🎯 **Next Steps After Reboot**

1. **Set Up Admin User**: Create your admin profile
2. **Test Admin Knowledge**: Verify permanent knowledge works
3. **Test Budget Tracking**: Try spending commands
4. **Verify Admin Portal**: Check user management
5. **Test Web Search**: Ensure search integration works

## 📞 **Support**

- **Admin Portal**: https://dlzki3kkd9171.cloudfront.net
- **Chatbot**: https://chatbot.betterbubble.org
- **API Documentation**: Available in Lambda function code
- **System Status**: Check CloudWatch logs and metrics

---

**This system represents a complete AI assistant with advanced features for BetterBubble organization, including admin controls, budget tracking, and intelligent web search capabilities.**