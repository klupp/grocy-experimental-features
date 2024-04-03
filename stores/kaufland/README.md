# Kaufland API
### Resources Found Online
Client ID found online: 88207bfc-780b-400d-92ee-893ae72dab40

### How to get tokens
Login to kaufland online and go to Filial-Angebote.
Then open dev console and go to `Storage > Local Storage > https://filiale.kaufland.de`.
Find the `localAuthDataKey > tokens` and copy
- `sub` as `user_id` to use it as path variable
- `access_token` as `Authorization`: "Bearer `access_token`"
- `client_id`: use the provided id. 

_Note:_ The access token expires in 24 hours, it has to be renewed.