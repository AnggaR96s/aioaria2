# aioaria2


[![pypi](https://img.shields.io/pypi/v/aioaria2.svg)](https://pypi.org/project/aioaria2/)
![python](https://img.shields.io/pypi/pyversions/aioaria2)
![implementation](https://img.shields.io/pypi/implementation/aioaria2)
![wheel](https://img.shields.io/pypi/wheel/aioaria2)
![license](https://img.shields.io/github/license/synodriver/aioaria2.svg)

## Support async rpc call with aria2 and process management

## Usage:

### example

```python
import asyncio
from pprint import pprint

import aioaria2


async def main():
    async with aioaria2.Aria2HttpClient("http://117.0.0.1:6800/jsonrpc",
                                        token="token") as client:
        pprint(await client.getVersion())


asyncio.run(main())
```

### The ip address should be replaced with your own

### See [aria2 manual](http://aria2.github.io/manual/en/html/) for more detail about client methods

```python
# exampe of http
import asyncio
from pprint import pprint

import aioaria2
import ujson


async def main():
    async with aioaria2.Aria2HttpClient("http://127.0.0.1:6800/jsonrpc",
                                        token="token",
                                        loads=ujson.loads,
                                        dumps=ujson.dumps) as client:
        pprint(await client.addUri(["http://www.demo.com"]))  # that would start downloading


asyncio.run(main())
```

```python
# exampe of websocket
import asyncio
from pprint import pprint

import aioaria2
import ujson


@aioaria2.run_sync
def on_download_complete(trigger, data):
    print(f"downlaod complete {data}")


async def main():
    client: aioaria2.Aria2WebsocketClient = await aioaria2.Aria2WebsocketClient.new("http://127.0.0.1:6800/jsonrpc",
                                                                                      token="token",
                                                                                      loads=ujson.loads,
                                                                                      dumps=ujson.dumps)
    client.onDownloadComplete(on_download_complete)
    pprint(await client.addUri(["http://www.demo.com"]))


loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
```

- Run that coroutine function and each method represent an aria2-rpc call. As for server, each instance represent an aria2 process.

```python
import aioaria2
import asyncio


async def main():
    server = aioaria2.AsyncAria2Server(r"aria2c.exe",
                                       r"--conf-path=aria2.conf", "--rpc-secret=admin", daemon=True)
    await server.start()
    await server.wait()


asyncio.run(main())
```

#### this start an aria2 process

[Aria2 Manual](http://aria2.github.io/manual/en/html/)

### todolist

- [x] async http
- [x] async websocket
- [x] async process management
- [x] unitest

This module is built on top of [aria2jsonrpc](https://xyne.archlinux.ca/projects/python3-aria2jsonrpc)
with async and websocket support.

### For windows users, you should

```
# for start async aria2 process
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.set_event_loop(asyncio.ProactorEventLoop())
```

For python version greater than 3.8, asyncio uses ProactorEventLoop by default, so there is no need to modify

#### v1.2.0

new Aria2WebsocketTrigger class for websocket events, use on* methods to add callbacks

Like

```
@trigger.onDownloadStart
async def onDownloadStart(trigger, future):
    print("下载开始{0}".format(future.result()))
```

#### v1.2.3

Now you can add multiple callbacks for one event ,must be coroutine function or an async callable, use ```aioaria2.run_sync``` to wrap a sync function

```
@trigger.onDownloadStart
async def callback1(trigger, future):
    print("第一个回调{0}".format(future.result()))

@trigger.onDownloadStart
@run_sync
def callback2(trigger, future):
    print("第二个回调{0}".format(future.result()))
```

#### v1.3.0

* Big changes for class```Aria2WebsocketTrigger```

* Callbacks now accept```dict```as second parameter instead of```asyncio.Future```
* methods of class```Aria2WebsocketTrigger``` now have same return value as ```Aria2HttpClient```
* ```id``` parameter now accept a callable as idfactory to generate uuid, otherwise default uuid factory is used.


```
@trigger.onDownloadStart
async def callback1(trigger, data:dict):
    print("第一个回调{0}".format(data))

@trigger.onDownloadStart
@run_sync
def callback2(trigger, data:dict):
    print("第二个回调{0}".format(data))
```

### v1.3.1

* custom json library with keyword arguments ```loads``` ```dumps```

### v1.3.2

* fix  unclosed client_session when exception occurs during ws_connect
* alias for ```Aria2WebsocketTrigger```,named ```Aria2WebsocketClient```

### v1.3.3

* fix method problems in client

### v1.3.4rc1

* handle reconnect simply
* handle InvalidstateError while trying to ping aria2

### v1.3.4

* add async id factory support
* allow unregister callbacks in websocketclient
* add contextvars support in ```run_sync```

### v1.3.5rc1

* graceful shutdown

### v1.3.5rc2

* add parser for aria2 files

```python
from pprint import pprint
from aioaria2 import DHTFile

pprint(DHTFile.from_file2("dht.dat"))
```

### v1.3.5rc3

* add strong ref to pending tasks

### v1.3.6

* update latest aiohttp version

## TLS (JA3/JA4) & HTTP/2 Fingerprint Spoofing

Aria2 natively does not support changing its TLS Fingerprint (JA3) or HTTP/2 Fingerprint (Akamai), which are often used by anti-bot protections (like Cloudflare, Akamai, etc.) to block non-browser traffic.

`aioaria2` now includes a local proxy (`Aria2BrowserProxy`) that can intercept aria2 requests and forward them using `curl_cffi`. This allows you to fully impersonate a real browser (e.g., Chrome, Safari) at the network layer.

**Features Supported:**
*   **JA3 / JA4 Signatures:** Matches the TLS handshake of a real browser.
*   **HTTP/2 Fingerprinting:** Matches the HTTP/2 frame settings and order of a real browser.
*   **Header Ordering:** Sends headers in the correct order for the impersonated browser.

### Usage

```python
import asyncio
from aioaria2 import Aria2BrowserProxy, Aria2HttpClient

async def main():
    # 1. Start the Spoofing Proxy
    # 'impersonate' can be "chrome", "safari", "edge", etc.
    # This will spoof JA3, JA4, and HTTP/2 fingerprints.
    proxy = Aria2BrowserProxy(port=0, impersonate="chrome")
    await proxy.start()

    proxy_url = proxy.address
    print(f"Proxy started at {proxy_url}")

    # 2. Configure aria2 to use this proxy
    # NOTE: You must use 'http' scheme for the target URL in aria2
    # and pass the 'X-Target-Scheme: https' header so the proxy knows to use HTTPS upstream.
    # This is required because aria2c's native CONNECT method for HTTPS would expose its own fingerprint.

    target_url = "http://target-site.com/file.zip" # Use http here to talk to the proxy

    options = {
        "all-proxy": proxy_url,
        "header": [
            "X-Target-Scheme: https",  # Tell proxy to fetch https
            "User-Agent: Mozilla/5.0..." # Optional: match the impersonated browser
        ]
    }

    async with Aria2HttpClient("http://127.0.0.1:6800/jsonrpc", token="token") as client:
        await client.addUri([target_url], options=options)
        print("Download started with Browser Impersonation!")

    # Keep proxy running while downloading...
    # await proxy.stop() # call this when done

if __name__ == "__main__":
    asyncio.run(main())
```

### Dependencies

To use this feature, you must install `curl_cffi`:

```bash
pip install curl_cffi
```

(This is automatically installed if you install `aioaria2` with dependencies).