import requests
from bs4 import BeautifulSoup
import json
import time
import boto3


firstReview = {}

def get_reviews_from_file(file_path):
    # Read the content of the file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')

    # Find the script tag that contains the JSON-LD data
    script_tags = soup.find_all('script', {'type': 'application/ld+json'})
    
    # Extract and parse the JSON-LD data
    reviews_data = []
    for script_tag in script_tags:
        try:
            review_data = json.loads(script_tag.string)
            reviews_data.append(review_data)
        except json.JSONDecodeError:
            pass

    return reviews_data

def getReviews():
    file_path = 'page.txt'
    reviews_data = get_reviews_from_file(file_path)

    if not reviews_data:
        print("No reviews found.")
        return
    with open('data.json', 'w', encoding='utf-8') as f:
        #save data as json
        json.dump(reviews_data, f, indent=4)


def cleanData():
    # Read data from the file
    with open('data.json', 'r', encoding='utf-8') as file:
        data = file.read()

        # Parse JSON data
        json_data = json.loads(data)

        # Extract the reviews
        temp = json_data[0]["@graph"]
        
        #from temp keep only the entries which have "@type": "Review"
        reviews = [review for review in temp if review["@type"] == "Review"]

        # Append the reviews to reviews.json
        existing_reviews = []
        try:
            with open('reviews.json', 'r', encoding='utf-8') as f:
                existing_data = f.read()
                if existing_data:
                    existing_reviews = json.loads(existing_data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        existing_reviews.extend(reviews)

        #if the first review is the same as the FirstReview, then stop
        if reviews[0] == firstReview:
            #Delete the page.txt and data.json files
            import os
            
            os.remove("page.txt")
            file.close()
            os.remove("data.json")
            print("All Reviews Found")
            
            #Save the reviews to an S3 bucket
            s3 = boto3.resource('s3')
            bucket_name = 'trustpilot-bucket'
            object_key = 'reviews.json'

            # Upload the file to S3 bucket
            s3.meta.client.upload_file('reviews.json', bucket_name, object_key)


            # Generate and print the public URL of the object
            public_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
            print("Public URL:", public_url)
            print("Reviews saved to S3 bucket")
            exit(0)
        
        # Save the updated reviews to reviews.json in a human-readable format (pretty JSON)
        with open('reviews.json', 'w', encoding='utf-8') as f:
            print("Saving reviews to reviews.json")
            json.dump(existing_reviews, f, indent=4)
            
        

def savePage(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch the page. Status Code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Save the soup to a file soup.txt
    with open('page.txt', 'w', encoding='utf-8') as f:
        f.write(str(soup))
        
    getReviews()
    cleanData()




if __name__ == "__main__":
    #empty the reviews.json file
    with open('reviews.json', 'w', encoding='utf-8') as f:
        f.write("")
    firstRun_url = 'https://www.trustpilot.com/review/homeandlove.co.uk'
    print("Iteration 1")
    savePage(firstRun_url)
    
    #Get the first review from reviews.json
    with open('reviews.json', 'r', encoding='utf-8') as f:
        data = f.read()
        json_data = json.loads(data)
        firstReview = json_data[0]
    
    time.sleep(1)
    
    #Run code at least once, at most n times
    n = 500
    i=2;
    while i<=n:
        trustpilot_url = firstRun_url + '?page=' + str(i)
        print("Iteration " + str(i))
        savePage(trustpilot_url)
        #wait for 2 seconds
        time.sleep(1 + 0.2 * i)
        i+=1
    
    