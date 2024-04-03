import requests


class ImageFromUrl:
    def __init__(self, url: str):
        self.url = url
        self.name = self.url.split('/')[-1].split("?")[0]
        self.extension = self.name.split(".")[-1]
        if self.extension not in ['png', 'jpg', 'jpeg']:
            raise Exception("No image found")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
        self.content = requests.get(self.url, headers=headers).content
