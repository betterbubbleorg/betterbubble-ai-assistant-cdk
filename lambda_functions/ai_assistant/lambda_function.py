import json
import boto3
import os
from datetime import datetime
import jwt
import requests

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
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                break
        
        if not key:
            raise ValueError('Unable to find appropriate key')
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=os.environ.get('COGNITO_USER_POOL_CLIENT_ID'),
            issuer=f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
        )
        
        return payload
    except Exception as e:
        print(f"JWT verification error: {str(e)}")
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
        
        print(f"Event: {json.dumps(event)}")
        
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
        
        # Prepare the prompt for Claude
        prompt = f"Human: {user_message}\n\nAssistant:"
        
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
                    'messages': [
                        {
                            'role': 'user',
                            'content': user_message
                        }
                    ]
                }),
                contentType='application/json'
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            ai_response = response_body.get('content', [{}])[0].get('text', 'Sorry, I could not generate a response.')
            
        except Exception as bedrock_error:
            print(f"Bedrock error: {str(bedrock_error)}")
            # Fallback response when Bedrock is not available
            ai_response = f"I received your message: '{user_message}'. However, I'm currently unable to access my AI capabilities as the Bedrock model needs to be enabled in your AWS account. Please enable the Claude model in AWS Bedrock to get full AI responses."
        
        # Store conversation in DynamoDB (with error handling)
        try:
            conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
            
            # Generate a unique conversation ID for this interaction
            conversation_id = f"conv_{int(datetime.utcnow().timestamp())}"
            
            conversation_item = {
                'user_id': user_id,
                'conversation_id': conversation_id,
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
                'timestamp': conversation_item['timestamp']
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
