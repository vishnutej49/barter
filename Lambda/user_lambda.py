import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'Users'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    http_method = event.get('httpMethod', '').upper()
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    if http_method == 'POST':
        return create_user(body)
    elif http_method == 'GET':
        params = event.get('queryStringParameters') or {}
        if 'user_id' in params:
            return get_user_by_id(params['user_id'])
        elif 'phone_number' in params:
            return get_user_by_phone_number(params['phone_number'])
        else:
            return list_all_users()
    elif http_method == 'PUT':
        return update_user(body)
    elif http_method == 'DELETE':
        user_id = (event.get('queryStringParameters') or {}).get('user_id')
        return delete_user(user_id)

    return {
        'statusCode': 400,
        'body': json.dumps('Unsupported HTTP method')
    }

def create_user(body):
    user_id = body.get('user_id')
    if not user_id:
        return {'statusCode': 400, 'body': json.dumps('Missing user_id')}

    phone_number = body.get('phone_number')
    if not phone_number:
        return {'statusCode': 400, 'body': json.dumps('Missing phone_number')}

    item = {
        'user_id': user_id,
        'phone_number': phone_number,
        'created_at': datetime.utcnow().isoformat()
    }

    table.put_item(Item=item)
    return {'statusCode': 200, 'body': json.dumps('User created successfully')}

def get_user_by_id(user_id):
    response = table.get_item(Key={'user_id': user_id})
    item = response.get('Item')
    if not item:
        return {'statusCode': 404, 'body': json.dumps('User not found')}
    
    return {'statusCode': 200, 'body': json.dumps(item)}

def get_user_by_phone_number(phone_number):
    index_name = 'PhoneLookupIndex'
    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=Key('phone_number').eq(phone_number)
    )

    items = response.get('Items', [])
    if not items:
        return {'statusCode': 404, 'body': json.dumps('User not found')}
    
    return {'statusCode': 200, 'body': json.dumps(items)}

def list_all_users():
    response = table.scan()
    items = response.get('Items', [])
    return {'statusCode': 200, 'body': json.dumps(items)}

def update_user(body):
    user_id = body.get('user_id')
    if not user_id:
        return {'statusCode': 400, 'body': json.dumps('Missing user_id')}

    phone_number = body.get('phone_number')
    if not phone_number:
        return {'statusCode': 400, 'body': json.dumps('Missing phone_number')}

    update_expression = 'SET phone_number = :phone_number'
    expression_attribute_values = {
        ':phone_number': phone_number
    }

    table.update_item(
        Key={'user_id': user_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )

    return {'statusCode': 200, 'body': json.dumps('User updated successfully')}

def delete_user(user_id):
    if not user_id:
        return {'statusCode': 400, 'body': json.dumps('Missing user_id')}

    table.delete_item(Key={'user_id': user_id})
    return {'statusCode': 200, 'body': json.dumps('User deleted successfully')}
