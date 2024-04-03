# Netto API
The API token has to be obtained trough mitmproxy on the android app. 
Also, you have to remove the certificate pinning.

The token is valid for 4months.

1. `export PATH=$PATH:$HOME/Android/Sdk/emulator`
2. `export PATH=$PATH:$HOME/Android/Sdk/platform-tools`
3. `emulator -avd proxy_test -writable-system &`
4. `cd Downloads/mitmproxy-10.2.2-linux-x86_64`
5. `./mitmweb`
6. In the mitmproxy search for `einkaufhistorie`
7. and copy the `authorization` token from the headers.

# Disclaimer
The api was changed from JSON to xml SOAP service. This app needs to be reimplemented :(