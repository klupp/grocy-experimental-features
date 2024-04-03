class API:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def get_url(self):
        url = self.host
        if self.port not in [80, 443]:
            url += ":" + str(self.port)
        return url
