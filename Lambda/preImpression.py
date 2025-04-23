import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
items_table = dynamodb.Table('Items')  
bids_table = dynamodb.Table('Bids')  

def lambda_handler(event, context):
    # Extract user_id and category from GET queryStringParameters
    user_id = None
    category = None

    if event.get('httpMethod') == 'GET':
        query_params = event.get('queryStringParameters') or {}
        user_id = query_params.get('user_id')
        category = query_params.get('category')
    
    # Check for required user_id parameter
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'user_id is required'}),
        }

    # Step 1: Fetch items from Items table that are not by this user and are available
    scan_params = {
        'FilterExpression': Attr('user_id').ne(user_id) & Attr('status').eq('available')
    }

    if category:
        scan_params['FilterExpression'] &= Attr('category').eq(category)

    response = items_table.scan(**scan_params)
    items_to_show = response['Items']

    # Step 2: Get all bids where requested_user_id is current user and status is pending or accepted
    response_bids = bids_table.scan(
        FilterExpression=Attr('requested_user_id').eq(user_id) & (
            Attr('status').eq('pending') | Attr('status').eq('accepted')
        )
    )

    requested_items = {bid['offered_item_id'] for bid in response_bids['Items']}

    # Step 3: Filter out already requested items
    filtered_items = [item for item in items_to_show if item['item_id'] not in requested_items]

    # Step 4: Return the filtered list of items
    return {
        'statusCode': 200,
        'body': json.dumps({'items': filtered_items}),
    }
