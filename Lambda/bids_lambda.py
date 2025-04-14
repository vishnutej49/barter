import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'Bids'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    http_method = event['httpMethod']
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    params = event.get('queryStringParameters') or {}
    
    if http_method == 'POST':
        return create_bid(body)
    elif http_method == 'GET':
        if 'bid_id' in params:
            return get_bid(params['bid_id'])
        elif 'requested_user_id' in params:
            return get_received_bids(params['requested_user_id'], params.get('status'))
        elif 'offered_by' in params:
            return get_offered_bids(params['offered_by'])
        else:
            return list_all_bids()
    elif http_method == 'PUT':
        return update_bid(body)
    elif http_method == 'DELETE':
        bid_id = params.get('bid_id')
        return delete_bid(bid_id)

    return {
        'statusCode': 400,
        'body': json.dumps('Unsupported HTTP method')
    }

def create_bid(body):
    bid_id = body.get('bid_id')
    if not bid_id:
        return {'statusCode': 400, 'body': json.dumps('Missing bid_id')}

    item = {
        'bid_id': bid_id,
        'requested_user_id': body.get('requested_user_id', ''),
        'status': body.get('status', 'pending'),
        'offered_by': body.get('offered_by', ''),
        'created_at': datetime.utcnow().isoformat()
    }

    table.put_item(Item=item)
    return {'statusCode': 200, 'body': json.dumps('Bid created successfully')}

def get_bid(bid_id):
    response = table.get_item(Key={'bid_id': bid_id})
    item = response.get('Item')
    if not item:
        return {'statusCode': 404, 'body': json.dumps('Bid not found')}
    
    return {'statusCode': 200, 'body': json.dumps(item)}

def list_all_bids():
    response = table.scan()
    items = response.get('Items', [])
    return {'statusCode': 200, 'body': json.dumps(items)}

def get_received_bids(requested_user_id, status=None):
    index_name = 'ReceivedBidsIndex'
    key_condition = Key('requested_user_id').eq(requested_user_id)
    if status:
        key_condition &= Key('status').eq(status)

    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition
    )

    items = response.get('Items', [])
    return {'statusCode': 200, 'body': json.dumps(items)}

def get_offered_bids(offered_by):
    index_name = 'OfferedBidsIndex'
    key_condition = Key('offered_by').eq(offered_by)

    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition
    )

    items = response.get('Items', [])
    return {'statusCode': 200, 'body': json.dumps(items)}

def update_bid(body):
    bid_id = body.get('bid_id')
    if not bid_id:
        return {'statusCode': 400, 'body': json.dumps('Missing bid_id')}

    update_expression = 'SET #s = :status'
    expression_attribute_values = {
        ':status': body['status']
    }
    expression_attribute_names = {
        '#s': 'status'
    }

    table.update_item(
        Key={'bid_id': bid_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames=expression_attribute_names
    )

    return {'statusCode': 200, 'body': json.dumps('Bid updated successfully')}

def delete_bid(bid_id):
    if not bid_id:
        return {'statusCode': 400, 'body': json.dumps('Missing bid_id')}

    table.delete_item(Key={'bid_id': bid_id})
    return {'statusCode': 200, 'body': json.dumps('Bid deleted successfully')}  