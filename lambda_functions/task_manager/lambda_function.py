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
        tasks_table_name = os.environ.get('TASKS_TABLE_NAME', 'aiassistant-dev-tasks')
        tasks_table = dynamodb.Table(tasks_table_name)
        
        # Simplified user ID for now
        user_id = 'test-user'
        
        if http_method == 'GET':
            # Get all tasks for user
            response = tasks_table.query(
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
            # Create new task
            task_id = f"task_{int(datetime.utcnow().timestamp())}"
            task = {
                'user_id': user_id,
                'task_id': task_id,
                'title': body.get('title', ''),
                'description': body.get('description', ''),
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow().timestamp() + 86400 * 30))  # 30 days TTL
            }
            
            tasks_table.put_item(Item=task)
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps(task)
            }
            
        elif http_method == 'PUT':
            # Update task
            task_id = path_parameters.get('task_id')
            if not task_id:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Task ID required'})
                }
            
            # Update task attributes
            update_expression = "SET updated_at = :updated_at"
            expression_attribute_values = {':updated_at': datetime.utcnow().isoformat()}
            
            if 'title' in body:
                update_expression += ", title = :title"
                expression_attribute_values[':title'] = body['title']
            
            if 'description' in body:
                update_expression += ", description = :description"
                expression_attribute_values[':description'] = body['description']
            
            if 'status' in body:
                update_expression += ", #status = :status"
                expression_attribute_values[':status'] = body['status']
            
            tasks_table.update_item(
                Key={'user_id': user_id, 'task_id': task_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames={'#status': 'status'} if 'status' in body else {}
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'message': 'Task updated successfully'})
            }
            
        elif http_method == 'DELETE':
            # Delete task
            task_id = path_parameters.get('task_id')
            if not task_id:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                    },
                    'body': json.dumps({'error': 'Task ID required'})
                }
            
            tasks_table.delete_item(
                Key={'user_id': user_id, 'task_id': task_id}
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
                },
                'body': json.dumps({'message': 'Task deleted successfully'})
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
