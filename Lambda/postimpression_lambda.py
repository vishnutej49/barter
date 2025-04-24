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
        requested_id = record['requested_item_id']
        offered_id = record['offered_item_id']

        items_table.update_item(
            Key={'item_id': requested_id},
            UpdateExpression='SET #s = :new_status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':new_status': 'exchanged'}
        )
        items_table.update_item(
            Key={'item_id': offered_id},
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

        bids = bids_table.scan(
            FilterExpression='requested_item_id = :requested_item_id or offered_item_id = :offered_item_id',
            ExpressionAttributeValues={
                ':requested_item_id': requested_id,
                ':offered_item_id': offered_id
            }
        ).get('Items')

        for bid in bids:
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