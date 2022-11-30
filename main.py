import pandas as pd
from faker import Faker
import random
import psycopg2
from sqlalchemy import create_engine
import boto3
import json

def handle_message(resp, sqs, queue_url):
    """Reads message from the queue, extracts the body and timestamp, and deletes the message."""

    # Extract the body of the SQS message as 'message' and the timestamp as 'time_stamp'
    message = json.loads(resp['Messages'][0]['Body'])
    time_stamp = {'create_date':resp['ResponseMetadata']['HTTPHeaders']['date']}

    # Creates one dict object including the message body contents and timestamp
    formatted_message = {**message,**time_stamp}
    
    # Removes processed message from the queue
    sqs.delete_message(
        QueueUrl = queue_url,
        ReceiptHandle = resp['Messages'][0]['ReceiptHandle']
    )

    return formatted_message

def mask_device_id(dataframe):
    """Masks all device_id values in a DataFrame, ensuring that duplicated values still match after masking."""

    duplicatedDeviceID = df[df.duplicated(['device_id'])]   # Finds indexes of rows with duplicated device_id values
    masked_device_ids = []
    masked_duplicate_ids = {}

    # Iterates through the DataFrame and builds a list of masked device IDs, preserving duplicates
    for index, row in dataframe.iterrows():
        
        id = ''     # Holds the masked id for each individual row

        # Check if the device ID is duplicated within the dataset
        if index in duplicatedDeviceID == True:
            
            """
            Check if the duplicated device ID already has a masked value.
            If so, use the corresponding value. If not, generate one and add
            it to the dictionary of masked duplicate values.
            """

            # If the duplicated device ID already has a corresponding mask, use it
            if row['device_id'] in masked_duplicate_ids.keys(): 
                id = masked_duplicate_ids.get(row['device_id'])
            # If the duplicated device ID doesn't have an assigned mask, generate one
            else:
                id = str(random.randint(100, 999)) + '-' + str(random.randint(10, 99)) + '-' + str(random.randint(100, 999))
                masked_duplicate_ids[row['device_id']] = id
        # If the device ID is unique within the dataset, generate a mask
        else:
            id = str(random.randint(100, 999)) + '-' + str(random.randint(10, 99)) + '-' + str(random.randint(100, 999))
        
        masked_device_ids.append(id)

    return masked_device_ids

def mask_ip(dataframe):
    """Masks all ip values in a DataFrame, ensuring that duplicated values still match after masking."""

    duplicatedIP = df[df.duplicated(['ip'])]    # Finds indexes of rows with duplicate ip values
    masked_ips = []
    masked_duplicate_ips = {}

    for index, row in dataframe.iterrows():

        ip = ''     # Holds the masked ip for each individual row

        # Check if the IP is duplicated within the dataset
        if index in duplicatedIP == True:

            """
            Check if the duplicated IP address already has a masked value.
            If so, use the corresponding value. If not, generate one and add
            it to the dictionary of masked duplicate values.
            """

            # If the duplicated IP already has a corresponding mask, use it
            if row['ip'] in masked_duplicate_ips.keys():
                ip = masked_duplicate_ips.get(row['ip'])
            # If the duplicated IP doesn't have an assigned mask, generate one
            else:
                ip = fake.ipv4()
                masked_duplicate_ips[row['ip']] = ip
        # If the IP is unique within the dataset, generate a mask
        else:
            ip = fake.ipv4()

        masked_ips.append(ip)

    return masked_ips

# Connect to SQS
queue_url = 'http://localhost:4566/000000000000/login-queue'

session = boto3.Session(
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

sqs = session.client('sqs', endpoint_url='http://localhost:4566/000000000000/login-queue')

data = []   # To hold all the message contents as a JSON object

# Append the body and timestamp from each message to the data list while there are messages in the queue
while True:
    resp = sqs.receive_message(
        QueueUrl = queue_url,
        MaxNumberOfMessages=1,
        AttributeNames = ['SentTimestamp']
    )

    if 'Messages' in resp:
        msg = handle_message(resp, sqs, queue_url)
        data.append(msg)
    else:
        break

# Connect to PostgreSQL database
conn = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

# Import data from the data list into a pandas dataframe
df = pd.DataFrame.from_records(data)

# Create lists of masked device ids and ip addresses, with duplicated values still matching
fake = Faker()
masked_ids = mask_device_id(df)
masked_ips = mask_ip(df)

# Build the final DataFrame, with columns matching user-logins table in Postgres
masked_df = df[['user_id', 'device_type', 'locale', 'app_version', 'create_date']].copy()
masked_df.insert(2, 'masked_ip', masked_ips)
masked_df.insert(3, 'masked_device_id', masked_ids)
masked_df.replace({'None': None})

# Write the DataFrame, including masked fields, to the user-logins table
masked_df.to_sql('user_logins', con=conn, if_exists='append', index=False)