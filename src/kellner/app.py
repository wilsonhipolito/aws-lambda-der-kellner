import os
import boto3
import csv
import json

# Explicitly specifying where the default AWS region is found
# (as an environment variable) to be able to mock it in the test
s3_client = boto3.client('s3', region_name=os.environ['AWS_REGION'])
sqs_client = boto3.client('sqs', region_name=os.environ['AWS_REGION'])

SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']

file_types = [ 'customers', 'orders', 'items' ]

def lambda_handler(event, context):
    print(event)

    # Get S3 bucket and key name from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key_name = event['Records'][0]['s3']['object']['key']
    print(f"Found file {key_name} in {bucket_name}")
    # Check if the file is a CSV file
    if key_name.endswith('.csv'):
        try:
            uploaded_file_type = key_name.split('_')[0]
            uploaded_file_date = key_name.split('_')[1].replace('.csv', '')
        except Exception as e:
            return {
                "success": False,
                "response": f"Filename {key_name} is not a CSV file in format '$TYPE_$DATE.csv'."
            }
        # Check if the other files are in the bucket
        if uploaded_file_type in file_types:
            for file_type in file_types:
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=f'{file_type}_{uploaded_file_date}.csv')
                except Exception as e:
                    return {
                        "success": False,
                        "response": f"File {file_type}_{uploaded_file_date} is not in the bucket {bucket_name} yet."
                    }
            # Process the files
            try:
                messages_sent = 0
                extracted_customers = extract_customer_data(read_file(bucket_name, f'customers_{uploaded_file_date}.csv'))
                extracted_orders = extract_order_data(read_file(bucket_name, f'orders_{uploaded_file_date}.csv'))
                extracted_items = extract_item_data(read_file(bucket_name, f'items_{uploaded_file_date}.csv'))
                for customer in extracted_customers:
                    customer_orders = []
                    customer_total_spent = 0
                    customer_event= {}
                    for order in extracted_orders:
                        if order['customer_reference'] == customer['customer_reference']:
                            customer_orders.append(order)
                            order_total_amount = sum_amount_per_order(order['order_reference'], extracted_items)
                            customer_total_spent += order_total_amount
                    number_of_orders = len(customer_orders)
                    customer_event = {
                        "type": "customer_message",
                        "customer_reference": customer['customer_reference'],
                        "number_of_orders": number_of_orders,
                        "total_amount_spent": customer_total_spent
                    }
                    # Send the message to the SQS queue
                    try:
                        sqs_response = send_sqs_message(customer_event, SQS_QUEUE_URL)
                        messages_sent += 1
                        
                    except Exception as e:
                        print(e)
                        return {
                            "success": False,
                            "response": f"Failed to send message to SQS queue - {e}"
                        }
            except Exception as e:
                error_message = {
                    "type": "error_message",
                    "customer_reference": None,
                    "order_reference": None,
                    "message": "Something went wrong!"
                }
                sqs_response = send_sqs_message(error_message, SQS_QUEUE_URL)
                return {
                    "success": False,
                    "response": f"Failed to process file {e}"
                }
            finally:
                return {
                    "success": True,
                    "response": f"Processed files for bucket {bucket_name} and sent {messages_sent} messages."
                }
        else:
            return {
               "success": False,
               "response": f"Invalid file name format. File must have {file_types} prefix."
            }
    else:
        return {
            "success": False,
            "response": f"File {key_name} is Invalid. File must have .csv extension."
        }

def read_file(bucket_name, key_name):
    s3_file = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    s3_file_content = s3_file['Body'].read().decode('utf-8')

    return s3_file_content


def extract_customer_data(s3_file_content):
    dict_reader = csv.DictReader(s3_file_content.splitlines())
    costumers = [row for row in dict_reader if row['status'] == 'Active']

    return costumers


def extract_order_data(s3_file_content):
    dict_reader = csv.DictReader(s3_file_content.splitlines())
    orders = [row for row in dict_reader if row['order_status'] == 'Delivered']
    
    return orders


def extract_item_data(s3_file_content):
    dict_reader = csv.DictReader(s3_file_content.splitlines())
    order_items = [row for row in dict_reader]
    
    return order_items


def sum_amount_per_order(order_reference, order_items):
    total_amount = 0
    for order_item in order_items:
        if order_item['order_reference'] == order_reference:
            item_total = float(order_item['quantity']) * float(order_item['total_price'])
            total_amount += float(item_total)
            
    return total_amount


def send_sqs_message(event, queue_url):
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(event)
    )

    return response