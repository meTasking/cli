import requests


def handle_response(response: requests.Response):
    if response.status_code != 200:
        raise Exception(f"Error: {response.text}")
    return response.json()
