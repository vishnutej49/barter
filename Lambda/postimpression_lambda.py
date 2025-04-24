import json
import boto3

dynamodb = boto3.resource('dynamodb')
bids_table = dynamodb.Table('Bids')
items_table = dynamodb.Table('Items')

def lambda_handler(event, context):
    http_method = event['httpMethod']
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    if http_method == 'PUT':
        return put_bid(event, body)
    return {
        'statusCode': 400,
        'body': json.dumps('Invalid HTTP Method')
    }

def put_bid(event, body):
    try:
        bid_id = body['bid_id']
        if not bid_id:
            return {
                'statusCode': 400,
                'body': json.dumps('Bid ID is required')
            }
        record = bids_table.get_item(Key={'bid_id': bid_id}).get('Item')
        requested_item_id = record['requested_item_id']
        offered_item_id = record['offered_item_id']

        #updating status to in items table
        items_table.update_item(
            Key={'item_id': requested_item_id},
            UpdateExpression='SET #s = :new_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':new_status': 'exchanged'}
        )

        items_table.update_item(
            Key={'item_id': offered_item_id},
            UpdateExpression='SET #s = :new_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':new_status': 'exchanged'}
        )

        bids_table.update_item(
            Key={'bid_id': bid_id},
            UpdateExpression='SET #s = :new_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':new_status': 'accepted'}
        )

        #Rejecting bids with same requested_item_id / offered_item_id
        response = bids_table.query(
            IndexName='requested_item_id-index',
            KeyConditionExpression='requested_item_id = :requested_item_id',
            ExpressionAttributeValues={':requested_item_id': requested_item_id}
        )
        for bid in response['Items']:
            if bid['bid_id'] != bid_id:
                bids_table.update_item(
                    Key={'bid_id': bid['bid_id']},
                    UpdateExpression='SET #s = :new_status',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':new_status': 'rejected'}
                )
        response = bids_table.query(
            IndexName='offered_item_id-index',
            KeyConditionExpression='offered_item_id = :offered_item_id',
            ExpressionAttributeValues={':offered_item_id': offered_item_id}
        )
        for bid in response['Items']:
            if bid['bid_id'] != bid_id:
                bids_table.update_item(
                    Key={'bid_id': bid['bid_id']},
                    UpdateExpression='SET #s = :new_status',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':new_status': 'rejected'}
                )
        
        return {
            'statusCode': 200,
            'body': json.dumps('Bid placed successfully')
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps("Unknown error occured")
        }