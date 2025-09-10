"""
Backend Stack for AI Personal Assistant
Creates Lambda functions and API Gateway for the backend services.
"""

from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Optional


class LambdaStack(Stack):
    """Lambda functions and API Gateway for AI Personal Assistant."""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        config: dict,
        stacks: dict,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Lambda functions
        self.lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name="BetterBubble-AI-LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add DynamoDB permissions
        if stacks and 'dynamodb' in stacks:
            dynamodb_stack = stacks['dynamodb']
            # Get actual table ARNs from the DynamoDB stack
            table_arns = []
            if hasattr(dynamodb_stack, 'users_table'):
                table_arns.append(dynamodb_stack.users_table.table_arn)
            if hasattr(dynamodb_stack, 'tasks_table'):
                table_arns.append(dynamodb_stack.tasks_table.table_arn)
            if hasattr(dynamodb_stack, 'appointments_table'):
                table_arns.append(dynamodb_stack.appointments_table.table_arn)
            if hasattr(dynamodb_stack, 'notes_table'):
                table_arns.append(dynamodb_stack.notes_table.table_arn)
            if hasattr(dynamodb_stack, 'conversations_table'):
                table_arns.append(dynamodb_stack.conversations_table.table_arn)
            
            if table_arns:
                self.lambda_role.add_to_policy(
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:Query",
                            "dynamodb:Scan"
                        ],
                        resources=table_arns
                    )
                )

        # Add Bedrock permissions
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Task Manager Lambda Function
        self.task_manager_lambda = lambda_.Function(
            self, "TaskManagerLambda",
            function_name="betterbubble-ai-task-manager",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="task_manager.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import os
from datetime import datetime

def handler(event, context):
    # Basic task management logic
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Task manager function is working',
            'timestamp': datetime.utcnow().isoformat()
        })
    }
            """),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_group=logs.LogGroup(
                self, "TaskManagerLogGroup",
                log_group_name="/aws/lambda/betterbubble-ai-task-manager",
                retention=logs.RetentionDays.ONE_WEEK
            )
        )

        # AI Assistant Lambda Function
        self.ai_assistant_lambda = lambda_.Function(
            self, "AiAssistantLambda",
            function_name="betterbubble-ai-assistant",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="ai_assistant.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import os
import jwt
import requests
from datetime import datetime
from urllib.parse import urlparse

# Initialize clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
cognito = boto3.client('cognito-idp')

def get_cognito_public_keys(user_pool_id, region):
    \"\"\"Get Cognito public keys for JWT verification\"\"\"
    jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    response = requests.get(jwks_url)
    return response.json()

def verify_cognito_token(token, user_pool_id, region):
    \"\"\"Verify Cognito JWT token\"\"\"
    try:
        # Get public keys
        jwks = get_cognito_public_keys(user_pool_id, region)
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        key_id = unverified_header.get('kid')
        
        # Find the matching key
        public_key = None
        for key in jwks['keys']:
            if key['kid'] == key_id:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                break
        
        if not public_key:
            return None
        
        # Verify and decode token
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=user_pool_id,
            issuer=f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
        )
        
        return decoded_token
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None

def handler(event, context):
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': ''
            }
        
        # Get authorization header
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
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        # Verify token (you'll need to set these environment variables)
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        region = context.invoked_function_arn.split(':')[3]  # Get region from function ARN
        
        if not user_pool_id:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'Configuration error'})
            }
        
        # Verify the token
        decoded_token = verify_cognito_token(token, user_pool_id, region)
        if not decoded_token:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '')
        
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
        
        # Get user info from token
        user_id = decoded_token.get('sub', 'unknown')
        username = decoded_token.get('cognito:username', 'unknown')
        
        # Prepare the prompt for Claude
        prompt = f"Human: {user_message}\n\nAssistant:"
        
        # Invoke Claude model
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'prompt': prompt,
                'max_tokens_to_sample': 1000,
                'temperature': 0.7,
                'top_p': 0.9
            }),
            contentType='application/json'
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        ai_response = response_body.get('completion', 'Sorry, I could not process your request.')
        
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
                'username': username,
                'timestamp': datetime.utcnow().isoformat()
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
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
            """),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            log_group=logs.LogGroup(
                self, "AiAssistantLogGroup",
                log_group_name="/aws/lambda/betterbubble-ai-assistant",
                retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'COGNITO_USER_POOL_ID': stacks['cognito'].user_pool.user_pool_id if stacks and 'cognito' in stacks else ''
            }
        )

        # Note Processor Lambda Function
        self.note_processor_lambda = lambda_.Function(
            self, "NoteProcessorLambda",
            function_name="betterbubble-ai-note-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="note_processor.handler",
            code=lambda_.Code.from_inline("""
import json
import boto3
import os
from datetime import datetime

def handler(event, context):
    # Basic note processing logic
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Note processor function is working',
            'timestamp': datetime.utcnow().isoformat()
        })
    }
            """),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_group=logs.LogGroup(
                self, "NoteProcessorLogGroup",
                log_group_name="/aws/lambda/betterbubble-ai-note-processor",
                retention=logs.RetentionDays.ONE_WEEK
            )
        )

        # Create API Gateway
        self.api = apigateway.RestApi(
            self, "AiAssistantApi",
            rest_api_name="BetterBubble AI Assistant API",
            description="API Gateway for AI Personal Assistant",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            ),
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            )
        )

        # Add API Gateway permissions to Lambda role
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        # Create API endpoints
        tasks_resource = self.api.root.add_resource("tasks")
        tasks_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )
        tasks_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )

        notes_resource = self.api.root.add_resource("notes")
        notes_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.note_processor_lambda)
        )
        notes_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.note_processor_lambda)
        )

        ai_resource = self.api.root.add_resource("ai")
        ai_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.ai_assistant_lambda)
        )

        # Health check endpoint
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.task_manager_lambda)
        )
