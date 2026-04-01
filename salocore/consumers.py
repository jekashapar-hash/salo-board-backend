import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models.categories import Chat, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_group_name = f"chat_{self.chat_id}"

        if not self.user.is_authenticated:
            await self.close(code=4003)
            return

        chat = await self.get_chat(self.chat_id)
        if not chat:
            await self.close(code=4004)
            return

        # Check access: allow if user owns the chat or is staff (admin)
        if chat.user_id != self.user.id and not self.user.is_staff:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        text = text_data_json.get("message")

        if text:
            # Save message to database
            msg = await self.save_message(self.user, self.chat_id, text)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "id": msg.id,
                    "chatId": msg.chat_id,
                    "userId": msg.user_id,
                    "username": self.user.username,
                    "text": msg.text,
                    "createdAt": msg.created_at.isoformat(),
                },
            )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "id": event["id"],
                    "chatId": event["chatId"],
                    "userId": event["userId"],
                    "username": event["username"],
                    "text": event["text"],
                    "createdAt": event["createdAt"],
                }
            )
        )

    @database_sync_to_async
    def get_chat(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, user, chat_id, text):
        return Message.objects.create(
            user=user, chat_id=chat_id, text=text
        )
