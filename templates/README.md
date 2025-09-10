# Frontend Templates

This directory contains Jinja2 templates for the Better Bubble AI Assistant frontend.

## Templates

- `chatbot.html` - Main chatbot interface with authentication and chat functionality

## Template Variables

The templates receive the following variables from the CDK stack:

- `cognito_user_pool_id` - Cognito User Pool ID
- `cognito_client_id` - Cognito User Pool Client ID  
- `cognito_identity_pool_id` - Cognito Identity Pool ID
- `api_url` - API Gateway URL for the backend

## Usage

Templates are automatically rendered by the FrontendStack during deployment. The rendered HTML is deployed to S3 and served via CloudFront at `chatbot.betterbubble.org`.
