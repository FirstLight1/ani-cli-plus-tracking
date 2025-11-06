#!/usr/bin/env python3
# filepath: tracker

import sys
import webbrowser
import requests
import os
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import mpv

def load_environment_variables():
    load_dotenv()
    global client_id, client_secret, redirect_uri, access_token
    client_id = os.getenv("ID")
    client_secret = os.getenv("SECRET")
    redirect_uri = os.getenv("REDIRECT")
    access_token = os.getenv("ACCESS_TOKEN")

def open_authorization_url():
    webbrowser.open(f"https://anilist.co/api/v2/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code")
    redirect_response = input("> ").strip()
    
    # Extract code from URL
    if "code=" in redirect_response:
        code = redirect_response.split("code=")[1].split("&")[0]
        response = requests.post("https://anilist.co/api/v2/oauth/token", data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        responseData = response.json()
        access_token = responseData.get("access_token")
        print(f"Access Token: {access_token}")
        return
    else:
        print("Error: No code found in URL")
        return None

def updateProgress(title, progress):
    query = '''
        query MyQuery {
            Media(search: "{title}") {
                id
                }
        }
        '''
    url = 'https://graphql.anilist.co'
    headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
    }
    body={
        'query':query
    }
    response = requests.post(url, headers=headers, json=body)
    print(response.json())

    update_query = '''
    mutation MyMutation {
        SaveMediaListEntry(mediaId: {mediaId}, progress: {progress}) {
            progress
        }
    }
    '''
    update_body={
        'query':update_query.replace("{mediaId}", str(response.json()['data']['Media']['id'])).replace("{progress}", str(progress))
    }
    authHeader = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    update_response = requests.post(url, headers=authHeader, json=update_body)
    print(update_response.json())



if __name__ == "__main__":
    if (not os.path.exists(".env")):
        print("Error: .env file not found. Please create one with your credentials.")
        sys.exit(1)
    load_environment_variables()
    if len(sys.argv) < 2:
        print("Usage: tracker.py [command]")
        print("Use 'tracker.py help' for more information.")
        sys.exit(1)
    if (sys.argv[1] == 'get-token'):
        open_authorization_url()
        sys.exit(0)
    elif (sys.argv[1] == 'help'):
        print("Usage: tracker.py [command]")
        print("Commands:")
        print("  get-token   Get a new access token")
        print("  help        Show this help message")
        sys.exit(0)
    elif (sys.argv[1] == 'run'):
        print('main')
        updateProgress(sys.argv[2], sys.argv[3])
        sys.exit(0)