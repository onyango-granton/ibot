import websockets
import json
import asyncio

async def test_connection():
    # Using Deriv's test app_id
    app_id = "67456"
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    try:
        async with websockets.connect(url) as websocket:
            print("Connected successfully!")
            
            # Test by subscribing to ticks
            tick_request = {
                "ticks": "1HZ10V",
                "subscribe": 1
            }
            
            await websocket.send(json.dumps(tick_request))
            print("Subscription request sent")
            
            # Listen for a few responses
            for _ in range(5):
                response = await websocket.recv()
                print(f"Received: {response}")
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())