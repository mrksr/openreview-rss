Add your OpenReview credentials to the this directory by creating a `credentials.json` file here. This will be read to access the server to avoid hardcoding the credentials or accidentally sharing them.

`credentials.json` file structure:
```json 
{ "username": "???", "password": "???"}
```

For the dev server (`setup_client(test_venue=True)`), create `credentials_dev.json` with the same structure.
For MFA via 1Password, add `"op_item"` (the 1Password item ID) and optionally `"op_account"` to either file.
