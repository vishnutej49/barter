import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'Items'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    http_method = event['httpMethod']
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    query = event.get('queryStringParameters') or {}

    if http_method == 'POST':
        return create_item(body)
    elif http_method == 'GET':
        if 'item_id' in query:
            return get_item(query['item_id'])
        elif 'user_id' in query:
            return get_items_by_user(query['user_id'])
        else:
            return list_all_items()
    elif http_method == 'PUT':
        return update_item(body)
    elif http_method == 'DELETE':
        return delete_item(query.get('item_id'))

    return {'statusCode': 400, 'body': json.dumps('Unsupported HTTP method')}

def create_item(body):
    item_id = body.get('item_id', str(uuid.uuid4()))
    user_id = body.get('user_id')
    created_at = datetime.utcnow().isoformat()

    if not user_id:
        return {'statusCode': 400, 'body': json.dumps('Missing user_id')}

    item = {
        'item_id': item_id,
        'user_id': user_id,
        'created_at': created_at
    }

    table.put_item(Item=item)
    return {'statusCode': 200, 'body': json.dumps({'message': 'Item created', 'item_id': item_id})}

def get_item(item_id):
    response = table.get_item(Key={'item_id': item_id})
    item = response.get('Item')
    if not item:
        return {'statusCode': 404, 'body': json.dumps('Item not found')}
    return {'statusCode': 200, 'body': json.dumps(item)}

def get_items_by_user(user_id):
    response = table.query(
        IndexName='UserItemsIndex',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
    )
    return {'statusCode': 200, 'body': json.dumps(response.get('Items', []))}

def list_all_items():
    response = table.scan()
    return {'statusCode': 200, 'body': json.dumps(response.get('Items', []))}

def update_item(body):
    item_id = body.get('item_id')
    if not item_id:
        return {'statusCode': 400, 'body': json.dumps('Missing item_id')}

    update_expr = []
    expr_vals = {}
    expr_names = {}

    for key in ['user_id', 'created_at']:
        if key in body:
            update_expr.append(f"#{key} = :{key}")
            expr_vals[f":{key}"] = body[key]
            expr_names[f"#{key}"] = key

    if not update_expr:
        return {'statusCode': 400, 'body': json.dumps('No fields to update')}

    table.update_item(
        Key={'item_id': item_id},
        UpdateExpression='SET ' + ', '.join(update_expr),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals
    )
    return {'statusCode': 200, 'body': json.dumps('Item updated')}

def delete_item(item_id):
    if not item_id:
        return {'statusCode': 400, 'body': json.dumps('Missing item_id')}
    table.delete_item(Key={'item_id': item_id})
    return {'statusCode': 200, 'body': json.dumps('Item deleted')}
