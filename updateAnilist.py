#!/usr/bin/env python3
# filepath: updateAnilist.py

import sys
import webbrowser
import requests
import os
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import json
import time
import socket


class MPVClient:
    """Lightweight MPV IPC client using socket communication"""
    
    def __init__(self, socket_path="/tmp/mpvsocket"):
        self.socket_path = socket_path
        self.sock = None
        self._request_id = 0
        
    def connect(self):
        """Connect to mpv IPC socket"""
        try:
            self.sock = socket.socket(socket.AF_UNIX)
            self.sock.connect(self.socket_path)
            self.sock.settimeout(1.0)
            return True
        except Exception as e:
            return False
    
    def _send_request(self, command):
        """Send a request and get response"""
        if not self.sock:
            return None
        
        try:
            self._request_id += 1
            request = json.dumps({
                "command": command,
                "request_id": self._request_id
            }) + "\n"
            
            self.sock.sendall(request.encode('utf-8'))
            
            # Read response
            response = b""
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\n" in chunk:
                        break
                except socket.timeout:
                    break
            
            if response:
                return json.loads(response.decode('utf-8').strip())
            return None
        except Exception as e:
            return None
    
    def get_property(self, prop):
        """Get a property value"""
        response = self._send_request(["get_property", prop])
        if response and response.get("error") == "success":
            return response.get("data")
        return None
    
    @property
    def duration(self):
        """Get video duration"""
        return self.get_property("duration")
    
    @property
    def time_pos(self):
        """Get current time position"""
        return self.get_property("time-pos")
    
    @property
    def percent_pos(self):
        """Get percentage position"""
        return self.get_property("percent-pos")
    
    @property
    def pause(self):
        """Get pause state"""
        return self.get_property("pause")
    
    @property
    def filename(self):
        """Get current filename"""
        return self.get_property("filename")
    
    def close(self):
        """Close connection"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    if seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def cli_main(title, progress, command=None):
    player = MPVClient()
    if command == "kill":
        print("Killing mpv connection...")
        player.close()
        return
    # Wait for socket to exist
    print("Waiting for mpv to start...")
    while not os.path.exists("/tmp/mpvsocket"):
        time.sleep(0.5)
    
    time.sleep(0.5)
    
    # Connect
    max_retries = 10
    for i in range(max_retries):
        if player.connect():
            print("Connected to mpv!\n")
            break
        time.sleep(1)
    else:
        print("Failed to connect to mpv")
        return
    
    try:
        print("Monitoring mpv playback... (Ctrl+C to stop)\n")
        while True:
            duration = player.duration
            time_pos = player.time_pos
            percent = player.percent_pos
            paused = player.pause
            
            if duration and time_pos is not None:
                remaining = duration - time_pos
                time_str = format_time(time_pos)
                duration_str = format_time(duration)
                remaining_str = format_time(remaining)
                
                if int(percent) >= 80:
                    print("\nUpdating Anilist...")
                    updateProgress(title, progress)  # Replace TITLE_PLACEHOLDER with actual 
                    player.close()
                status = "⏸ PAUSED" if paused else "▶ PLAYING"
                print(f"\r\033[K{status} | name: {player.filename} | Time: {time_str} / {duration_str} ({percent:.1f}%) | Remaining: {remaining_str}",
                      end="", flush=True)
            else:
                print("\r\033[KWaiting for playback data...", end="", flush=True)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopped monitoring")
    finally:
        player.close()




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

    headers = {
        "Content-Type": "application/json",
		"Accept": "application/json"
    }
    
    # Extract code from URL
    if "code=" in redirect_response:
        code = redirect_response.split("code=")[1].split("&")[0]
        response = requests.post("https://anilist.co/api/v2/oauth/token", headers=headers, json={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        responseData = response.json()
        access_token = responseData.get("access_token")
        print(responseData)
        print(f"Access Token: {access_token}")
        return
    else:
        print("Error: No code found in URL")
        return None

def updateProgress(title, progress):
    title = title.split(" (")[0]  # Remove any extra info in parentheses
    print(f"Updating '{title}' to episode {progress}...")
    query = '''
        query MyQuery {
            Media(search: "{title}" type: ANIME) {
                id
                episodes
                }
        }
        '''
    query = query.replace("{title}", title)
    url = 'https://graphql.anilist.co'
    headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
    }
    body={
        'query':query
    }
    response = requests.post(url, headers=headers, json=body)
    try:
        mediaId = response.json()['data']['Media']['id']
    except TypeError:
        print(response.json())
        print("Error: Unexpected response format")
        return
    try:
        totalEpisodes = response.json()['data']['Media']['episodes']
    except TypeError:
        print(response.json())
        print("Error: Unexpected response format")
        return

    authHeader = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    if progress == totalEpisodes:
        score = input("Score (0-10):")
        update_query = '''
        mutation MyMutation {
            SaveMediaListEntry(mediaId: {mediaId}, progress: {progress}, score: {score}, status: COMPLETED) {
                id
                progress
                score(format: POINT_10)
                status
            }
        }
        '''
        
        update_body={
            'query':update_query.replace("{mediaId}", str(mediaId)).replace("{progress}", str(progress)).replace("{score}", str(score))
        }
        update_response = requests.post(url, headers=authHeader, json=update_body)
        
    else:
        update_query = '''
        mutation MyMutation {
            SaveMediaListEntry(mediaId: {mediaId}, progress: {progress}) {
                id
                progress
            }
        }
        '''
        update_body={
            'query':update_query.replace("{mediaId}", str(mediaId)).replace("{progress}", str(progress))
        }
        

        update_response = requests.post(url, headers=authHeader, json=update_body)
        print(update_response.json())

def get_config_dir():
    """Get or create config directory"""
    from pathlib import Path
    config_home = os.getenv('XDG_CONFIG_HOME', Path.home() / '.config')
    config_dir = Path(config_home) / 'ani-cli-tracker'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def main():
    """Main entry point for the CLI"""
    if not os.path.exists(get_config_dir() / '.env'):
        print("Setting up config for first time...")
        config_dir = get_config_dir()
        env_template = """# AniList API Credentials
ID=
SECRET=
REDIRECT=http://localhost
ACCESS_TOKEN=
"""
        (config_dir / '.env').write_text(env_template)
        print(f"Created config at: {config_dir / '.env'}")
        print("Please edit with your credentials and run 'ani-tracker get-token'")
        sys.exit(0)

    load_environment_variables()
    
    if len(sys.argv) < 2:
        print("Usage: ani-tracker [command]")
        print("Use 'ani-tracker help' for more information.")
        sys.exit(1)
    if (sys.argv[1] == 'get-token'):
        open_authorization_url()
        sys.exit(0)
    elif (sys.argv[1] == 'help'):
        print("Usage: ani-tracker [command]")
        print("Commands:")
        print("  get-token   Get a new access token")
        print("  help        Show this help message")
        print("  run <title> <episode>  Track anime progress")
        sys.exit(0)
    elif (sys.argv[1] == 'run'):
        if len(sys.argv) < 4:
            print("Usage: ani-tracker run <title> <episode>")
            sys.exit(1)
        cli_main(sys.argv[2], int(sys.argv[3]))
        #updateProgress(sys.argv[2], int(sys.argv[3]))
        sys.exit(0)
    elif (sys.argv[1] == 'kill'):
        cli_main("","", "kill")
        sys.exit(0)

if __name__ == "__main__":
    main()