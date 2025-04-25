import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
items_table = dynamodb.Table('Items')
bids_table = dynamodb.Table('Bids')

def lambda_handler(event, context):
    query_params = event.get('queryStringParameters') or {}

    user_id = query_params.get('user_id')
    category = query_params.get('category')
    pagination_token_str = query_params.get('pagination_token')

    PAGE_SIZE = 1

    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'user_id is required'}),
        }

    # Step 1: Filter Expression for Items Table
    filter_expression = Attr('user_id').ne(user_id) & Attr('status').eq('available')
    if category:
        filter_expression &= Attr('category').eq(category)

    scan_params = {
        'FilterExpression': filter_expression,
        'Limit': PAGE_SIZE
    }

    # Step 2: Apply Pagination Token if Present
    if pagination_token_str:
        try:
            pagination_token = json.loads(pagination_token_str)
            scan_params['ExclusiveStartKey'] = pagination_token
        except Exception as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid pagination token'}),
                'headers': {'Access-Control-Allow-Origin': '*'}
            }

    # Step 3: Scan Items Table
    response = items_table.scan(**scan_params)
    items = response.get('Items', [])

    # Step 4: Get User's Pending/Accepted Bids
    response_bids = bids_table.scan(
        FilterExpression=Attr('requested_user_id').eq(user_id) & (
            Attr('status').eq('pending') | Attr('status').eq('accepted')
        )
    )
    requested_items = {bid['offered_item_id'] for bid in response_bids['Items']}
    filtered_items = [item for item in items if item['item_id'] not in requested_items]

    # Step 5: Prepare API Response
    response_body = {
        'items': filtered_items
    }

    # Step 6: Add Pagination Token if More Items Exist
    if 'LastEvaluatedKey' in response:
        print("DEBUG LastEvaluatedKey:", response['LastEvaluatedKey'])  # Helpful for debugging
        response_body['pagination_token'] = json.dumps(response['LastEvaluatedKey'])

    return {
        'statusCode': 200,
        'body': json.dumps(response_body),
    }
