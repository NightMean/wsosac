# wsosac
Webshare content search utility - Play your videos directly from the console.

![](https://raw.githubusercontent.com/chama-chomo/wsosac/master/images/scshot_main.jpg)

## What's needed to run this tool

First, you need to create your creds file in a below form (you may want to change its
permissions to 600, so only you can read it, until I provide a better way for
storing a password):

```
cat ~/.wscreds
<your WS username> <your WS password>
```

mpv - have media player installed on your system

```
[packages]
crypto = "*"
urlparse2 = "*"
requests-html = "*"
urllib3 = "*"
passlib = "*"
```

run `pipenv install` and `pipenv run wsosac.py` to run the tool from venv.
