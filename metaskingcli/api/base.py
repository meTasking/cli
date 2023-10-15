import requests


class HTTPErrorBody(requests.exceptions.HTTPError):
    # We want to see the reason of the error, which is returned in the
    # response body

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_text = self.response.text

    def __repr__(self):
        return super().__repr__() + "\n" + self.response_text

    def __str__(self):
        return super().__str__() + "\n" + self.response_text


def handle_response(response: requests.Response):
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # We want to see the reason of the error, which is returned in the
        # response body
        raise HTTPErrorBody(request=e.request, response=e.response)
