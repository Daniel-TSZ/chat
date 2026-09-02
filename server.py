import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, List
import uvicorn

app = FastAPI()

# Храним активные соединения по аккаунтам
connections_by_account: Dict[str, List[WebSocket]] = {
    "Алина": [],
    "Даник": []
}

@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_account = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)

                if msg.get("type") == "join":
                    sender = msg.get("sender", "")
                    if sender in connections_by_account:
                        user_account = sender
                        if websocket not in connections_by_account[user_account]:
                            connections_by_account[user_account].append(websocket)
                        broadcast_msg = {
                            "type": "join",
                            "sender": "Система",
                            "content": f"{user_account} присоединился(ась) к чату",
                            "timestamp": msg.get("timestamp", "")
                        }
                        await broadcast_to_all(broadcast_msg)
                    continue

                if msg.get("type") == "message":
                    sender = msg.get("sender", "")
                    if sender == "Алина":
                        recipient = "Даник"
                    elif sender == "Даник":
                        recipient = "Алина"
                    else:
                        continue
                    await send_to_account(recipient, msg)

            except json.JSONDecodeError:
                print("Не JSON:", data)

    except WebSocketDisconnect:
        if user_account and user_account in connections_by_account:
            if websocket in connections_by_account[user_account]:
                connections_by_account[user_account].remove(websocket)
            leave_msg = {
                "type": "join",
                "sender": "Система",
                "content": f"{user_account} покинул(а) чат",
                "timestamp": ""
            }
            await broadcast_to_all(leave_msg)

async def send_to_account(account: str, message: dict):
    if account not in connections_by_account:
        return
    message_str = json.dumps(message, ensure_ascii=False)
    for client in connections_by_account[account][:]:
        try:
            await client.send_text(message_str)
        except:
            if client in connections_by_account[account]:
                connections_by_account[account].remove(client)

async def broadcast_to_all(message: dict):
    message_str = json.dumps(message, ensure_ascii=False)
    for account, clients in connections_by_account.items():
        for client in clients[:]:
            try:
                await client.send_text(message_str)
            except:
                if client in connections_by_account[account]:
                    connections_by_account[account].remove(client)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
