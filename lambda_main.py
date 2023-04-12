import boto3
import os
import json
from difflib import SequenceMatcher
from getRecent import get_most_recent_object
# Set up AWS services
s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')
textract = boto3.client('textract')

# Set up similarity threshold
SIMILARITY_THRESHOLD = 0.0

import base64

def lambda_handler(event, context):
    # Get reference PDF file from S3
    reference_pdf_bucket = 'BUCKET_NAME'
    prefix=''
    reference_pdf_key = get_most_recent_object(reference_pdf_bucket,prefix)
    print('rpk',reference_pdf_key)
    reference_pdf = s3.get_object(Bucket=reference_pdf_bucket, Key=reference_pdf_key)
    reference_pdf_text = extract_text_from_pdf(reference_pdf['Body'].read())
    
    # Get folder of PDF files from S3
    pdf_folder_bucket = 'BUCKET_NAME'
    pdf_folder_key = "FOLDER_NAME"
    pdf_files = get_pdf_files_in_folder(pdf_folder_bucket, pdf_folder_key)
    
    # Compare similarity of each PDF file with reference PDF
    similarity_scores = {}
    for pdf_file in pdf_files:
        pdf_file_text = extract_text_from_pdf(pdf_file)
        similarity_score = calculate_similarity(reference_pdf_text, pdf_file_text)
        print(similarity_score)
        if similarity_score >= SIMILARITY_THRESHOLD:
            similarity_scores[pdf_file] = similarity_score
    
    # Sort similarity scores in descending order
    similarity_scores = dict(sorted(similarity_scores.items(), key=lambda item: item[1], reverse=True))
    
    # Create string response body
    body = ""
    for key, value in similarity_scores.items():
        key_str = base64.b64decode(key).decode('iso-8859-1')
        body += f"{key_str}: {value}\n"
    
    # Return response as string
    return {
        'statusCode': 200,
        'body': body
    }
    
def calculate_similarity(text1, text2):
    return SequenceMatcher(None, text1, text2).ratio()


def extract_text_from_pdf(pdf):
    # Detect text from PDF using Textract
    response = textract.analyze_document(Document={'Bytes': pdf}, FeatureTypes=['TABLES', 'FORMS'])

    text = b''
    # Extract text from Textract response
    for block in response['Blocks']:
        if block['BlockType'] == 'LINE':
            if block['Text']:
                text += block['Text'].encode('utf-8') + b' '

    # If no text was detected by Textract, try handwriting recognition using Comprehend
    if not text:
        response = comprehend.detect_handwriting(Image={'Bytes': pdf})
        handwriting_text = response['Text']

        # If text was detected by Comprehend, use it as the extracted text
        if handwriting_text:
            text = handwriting_text.encode('utf-8')
    print("hello**",text,end="\n")
    return text

def get_pdf_files_in_folder(bucket, folder_key):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=folder_key)
    pdf_files = []
    for item in response['Contents']:
        if item['Key'].endswith('.pdf'):
            obj = s3.get_object(Bucket=bucket, Key=item['Key'])
            pdf_files.append(obj['Body'].read())
    return pdf_files
