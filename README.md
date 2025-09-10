# AI Personal Assistant - CDK Infrastructure

This directory contains the AWS CDK infrastructure code for the Better Bubble AI Personal Assistant.

## Project Structure

```
ai-assistant-cdk-project/
├── README.md                    # This file
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # Python dependencies
└── stacks/                     # CDK stack definitions
    ├── __init__.py
    ├── database.py             # DynamoDB tables
    ├── auth.py                 # Cognito user pool
    ├── ai.py                   # Bedrock AI services
    ├── backend.py              # Lambda functions & API Gateway
    ├── frontend.py             # Amplify hosting
    └── monitoring.py           # CloudWatch monitoring
```

## Prerequisites

1. **AWS CLI configured**
   ```bash
   aws configure
   ```

2. **CDK installed**
   ```bash
   npm install -g aws-cdk
   ```

3. **Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **CDK Telemetry Disabled (AUTOMATIC)**
   - Telemetry is automatically disabled in `cdk.json`
   - No additional configuration needed
   - Privacy-first approach for all CDK operations

## Getting Started

### Quick Start (Recommended)
```bash
# Deploy development environment
./deploy.sh

# Deploy staging environment
./deploy.sh -e staging

# Show what would change
./deploy.sh -a diff

# Destroy environment
./deploy.sh -a destroy
```

### Manual CDK Commands

#### 1. Bootstrap CDK (First Time Only)
```bash
cdk bootstrap
```

#### 2. Deploy Development Stage
```bash
# Deploy entire development stage
cdk deploy BetterBubble-AI-Dev --context environment=dev

# Or deploy with specific context
cdk deploy BetterBubble-AI-Dev --context environment=dev --context region=us-west-2
```

#### 3. Deploy Individual Stacks (if needed)
```bash
# Deploy specific stacks within a stage
cdk deploy BetterBubble-AI-Dev/Database-dev
cdk deploy BetterBubble-AI-Dev/Auth-dev
cdk deploy BetterBubble-AI-Dev/AI-dev
cdk deploy BetterBubble-AI-Dev/Backend-dev
cdk deploy BetterBubble-AI-Dev/Frontend-dev
cdk deploy BetterBubble-AI-Dev/Monitoring-dev
```

#### 4. View Changes Before Deploy
```bash
cdk diff BetterBubble-AI-Dev --context environment=dev
```

## Environment Configuration

### Multi-Region Architecture
This project uses a **dual-region approach** for optimal performance and compliance:

#### Primary Region (Configurable)
- **Default**: us-west-2 (configurable in `conf/environment.yaml`)
- **Purpose**: Most AWS resources deployed here
- **Services**: Lambda, DynamoDB, Cognito, Bedrock, API Gateway

#### Global Region (Fixed: us-east-1)
- **Always Available**: `config['global_region']` in all stacks
- **Required Services**: 
  - Lambda@Edge functions for CloudFront
  - WAF for CloudFront protection
  - ACM certificates for CloudFront
  - Some CloudFront features
- **Usage**: `config['generate_stack_name']('stackname', config['global_region'])`

### Configuration Files
- **`conf/environment.yaml`**: Global settings (region, account, project metadata)
- **`conf/stages/dev.yaml`**: Development environment settings
- **`conf/stages/staging.yaml`**: Staging environment settings  
- **`conf/stages/prod.yaml`**: Production environment settings

### Environment Variables
Set environment variables before deployment:

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-west-2
```

### Stage Configuration
Each stage is self-contained with its own:
- Environment name (dev, staging, prod)
- Region configuration
- Stack naming convention
- Resource tagging

## Stack Dependencies

The stacks must be deployed in this order due to dependencies:

1. **Database** - DynamoDB tables
2. **Auth** - Cognito user pool
3. **AI** - Bedrock permissions
4. **Backend** - Lambda functions & API Gateway
5. **Frontend** - S3 + CloudFront hosting with custom domain
6. **Monitoring** - CloudWatch dashboards

## Frontend Features

### Custom Domain
- **URL:** `https://chatbot.betterbubble.org`
- **SSL:** Automatic HTTPS with ACM certificate
- **CDN:** Global CloudFront distribution for fast loading

### Template System
- **Jinja2 Templates:** Clean separation of HTML/CSS/JS from Python code
- **Location:** `/templates/chatbot.html`
- **Variables:** Cognito configs and API URLs injected automatically
- **Maintainable:** Easy to modify frontend without touching CDK code

### Authentication
- **Cognito Integration:** Secure user authentication
- **User Management:** Pre-created users (admin, renee, api)
- **Session Management:** Automatic token refresh
- **Role-based Access:** Different permissions for different users

## Cost Optimization

This infrastructure is designed to stay within AWS Free Tier limits:

- **DynamoDB**: Pay-per-request billing
- **Lambda**: 1M requests/month free
- **API Gateway**: 1M API calls/month free
- **Cognito**: 50,000 MAUs free
- **Amplify**: 1,000 build minutes/month free

Expected monthly cost: $5-20 for MVP usage.

## Security

- All data encrypted at rest with KMS
- IAM roles with least privilege
- VPC endpoints for private communication
- CloudWatch monitoring and alerting

## Development Workflow

1. **Make Changes**: Edit stack files in `stacks/`
2. **Review Changes**: Use `cdk diff` to see what will change
3. **Test Locally**: Use `cdk synth` to validate configuration
4. **Deploy**: Use `cdk deploy` to apply changes
5. **Verify**: Check AWS Console to confirm deployment

## Privacy and Security

### CDK Telemetry Disabled (AUTOMATIC)
This project follows Better Bubble's privacy-first approach. **CDK telemetry is automatically disabled** in `cdk.json` to protect sensitive information.

**No additional configuration needed** - telemetry is disabled by default for all CDK operations in this project.

### Data Privacy
- All user data is encrypted at rest and in transit
- No telemetry or usage data is collected by CDK
- AWS resources follow least-privilege access principles
- All infrastructure is defined as code for transparency

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Required**
   ```bash
   cdk bootstrap aws://ACCOUNT-NUMBER/REGION
   ```

2. **Permission Issues**
   - Check AWS credentials
   - Verify IAM permissions
   - Check resource policies

3. **Deployment Failures**
   - Check CloudFormation events
   - Review CDK logs
   - Verify resource limits

### Getting Help

1. Check AWS CloudFormation console for detailed error messages
2. Review CDK documentation
3. Check AWS service documentation
4. Follow troubleshooting procedures in `../../Documents/Procedures/`

---

*This infrastructure supports the Better Bubble organization's mission through reliable, cost-effective, and secure cloud resources.*
