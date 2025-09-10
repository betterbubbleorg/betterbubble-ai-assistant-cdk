import json
import boto3
import os
from datetime import datetime

# Initialize clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

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
        
        # Simplified - use default user info for now
        user_id = 'test-user'
        username = 'test-user'
        
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
        ai_response = response_body.get('completion', 'Sorry, I could not generate a response.')
        
        # Store conversation in DynamoDB
        conversations_table = dynamodb.Table(os.environ.get('CONVERSATIONS_TABLE_NAME', 'aiassistant-dev-conversations'))
        
        conversation_item = {
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'user_message': user_message,
            'ai_response': ai_response,
            'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
        }
        
        conversations_table.put_item(Item=conversation_item)
        
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
