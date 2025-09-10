import json
import boto3
import os
from datetime import datetime

# Initialize DynamoDB
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
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': ''
            }
        
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        http_method = event.get('httpMethod', 'GET')
        path_parameters = event.get('pathParameters') or {}
        
        # Get table names from environment
        notes_table_name = os.environ.get('NOTES_TABLE_NAME', 'aiassistant-dev-notes')
        notes_table = dynamodb.Table(notes_table_name)
        
        # Simplified user ID for now
        user_id = 'test-user'
        
        if http_method == 'GET':
            # Get all notes for user
            response = notes_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps(response['Items'])
            }
            
        elif http_method == 'POST':
            # Create new note
            note_id = f"note_{int(datetime.utcnow().timestamp())}"
            note = {
                'user_id': user_id,
                'note_id': note_id,
                'title': body.get('title', ''),
                'content': body.get('content', ''),
                'tags': body.get('tags', []),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
            }
            
            notes_table.put_item(Item=note)
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps(note)
            }
            
        elif http_method == 'PUT':
            # Update note
            note_id = path_parameters.get('note_id')
            if not note_id:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Note ID required'})
                }
            
            # Update note attributes
            update_expression = "SET updated_at = :updated_at"
            expression_attribute_values = {':updated_at': datetime.utcnow().isoformat()}
            
            if 'title' in body:
                update_expression += ", title = :title"
                expression_attribute_values[':title'] = body['title']
            
            if 'content' in body:
                update_expression += ", content = :content"
                expression_attribute_values[':content'] = body['content']
            
            if 'tags' in body:
                update_expression += ", tags = :tags"
                expression_attribute_values[':tags'] = body['tags']
            
            notes_table.update_item(
                Key={'user_id': user_id, 'note_id': note_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'message': 'Note updated successfully'})
            }
            
        elif http_method == 'DELETE':
            # Delete note
            note_id = path_parameters.get('note_id')
            if not note_id:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'error': 'Note ID required'})
            }
            
            notes_table.delete_item(
                Key={'user_id': user_id, 'note_id': note_id}
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'message': 'Note deleted successfully'})
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
