import websocket
ws = websocket.WebSocket()
ws.connect("wss://pumpportal.fun/api/data")
ws.send('{"type":"subscribeNewToken"}')
print(ws.recv())