import requests


class DuckDuckGoImagesAPI:
    def __init__(self):
        pass

    def get_url(self):
        return "https://duckduckgo.com/i.js"

    def get_params(self):
        return {
            "l": "en-us",
            "o": "json",
            "f": ",size:Medium,,,layout:Square,",
            "p": 1,
            "vqd": "4-78216246867751312120088203327573028584"
        }

    def query_image_url(self, query):
        params = self.get_params()
        params['q'] = query
        response = requests.get(self.get_url(), params=params)
        return response.json()["results"][0]["image"]