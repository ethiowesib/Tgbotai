from telethon import TelegramClient, events
import asyncio
import os

# --- Configuration ---
# Listener Bot (Bot 1) - Using telethon
BOT1_API_ID = 25151603  # Replace with your listener bot's API ID
BOT1_API_HASH = "5b9fd1382c575bc6aaa9b2e1e1a106e3"  # Replace with your listener bot's API Hash
BOT1_SESSION = "bot1_session"  # Session file for the listener bot
bot1 = TelegramClient(BOT1_SESSION, BOT1_API_ID, BOT1_API_HASH)

# User Bot (Acting as You)
API_ID = 25151603  # Your Telegram API ID
API_HASH = "5b9fd1382c575bc6aaa9b2e1e1a106e3"  # Your Telegram API Hash
PHONE_NUMBER = "+251978494843"  # Your phone number for Telegram
USER_BOT_SESSION = "user_bot_session"  # Session file for the user bot
user_bot = TelegramClient(USER_BOT_SESSION, API_ID, API_HASH)

# Target Bot (Bot 2) - Assume you know its username or ID
TARGET_BOT_USERNAME = "@gpt3_unlim_chatbot"  # Replace with the target bot's username

# --- Data Storage ---
user_data = {}  # {user_id: {"message": ..., "response": [], "chat_id": ...}}  response is now a list

# --- Listener Bot (Bot 1) Handler - Using telethon
@bot1.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id
    chat_id = event.chat_id
    message = event.message

    # Handle /start command
    if message.text == '/start':
        await bot1.send_message(chat_id, """Hello, I am a robot. What can I help you with?

I can:

ℹ️ Answer various questions.

📂 Work with text files and tabular data like csv (draw graphs, make calculations, etc.). Just send me the file.

🖼️

when you use this bot by sending image(photo) after sendin the image if it didn't give you the answer send resend the answer 
""")
        return

    msg_text = None
    file_path = None

    if message.text:
        msg_text = message.text
        user_data[user_id] = {"message": msg_text, "response": [], "chat_id": chat_id}  # Initialize response as an empty list
        print(f"Received text message from {user_id}: {msg_text}")

    elif message.media:
        # Handle media (photos, documents, etc.)
        try:
            if hasattr(message.media, 'photo'):
                file_extension = '.jpg'  # Or determine dynamically based on mime_type if possible
                file_path = f"images/{message.id}{file_extension}"
                os.makedirs("images", exist_ok=True)
                await bot1.download_media(message, file=file_path)
                user_data[user_id] = {"message": file_path, "response": [], "chat_id": chat_id} # Initialize response as an empty list
                print(f"Received photo from {user_id}, saved to {file_path}")
            elif hasattr(message.media, 'document'):
                file_extension = ''  # Determine dynamically based on mime_type if possible
                file_path = f"documents/{message.id}{file_extension}"
                os.makedirs("documents", exist_ok=True)
                await bot1.download_media(message, file=file_path)
                user_data[user_id] = {"message": file_path, "response": [], "chat_id": chat_id}  # Initialize response as an empty list
                print(f"Received document from {user_id}, saved to {file_path}")
            else:
                await bot1.send_message(user_id, "Unsupported media type.")
                return
        except Exception as e:
            print(f"Error downloading media: {e}")
            await bot1.send_message(user_id, f"Error processing media. Try again")
            return
    else:
        await bot1.send_message(user_id, "I can only handle text and media messages for now.")
        return
    #After getting the messages from the user, process them.
    asyncio.create_task(send_to_target_bot(user_id))


async def send_to_target_bot(user_id):
    """Sends the user's message to the target bot and waits for a response."""
    global user_data

    if user_id not in user_data:
        print(f"No data found for user {user_id}")
        return

    message_content = user_data[user_id]["message"]
    chat_id = user_data[user_id]["chat_id"]

    try:
        # Find the target bot's entity
        entity = await user_bot.get_entity(TARGET_BOT_USERNAME)

        # Send the message to the target bot
        if isinstance(message_content, str) and os.path.exists(message_content):
            # Send the file
            await user_bot.send_file(entity, message_content)
            await user_bot.send_message(entity, "File sent by user, please respond.")  # Optional instructions
        else:
            await user_bot.send_message(entity, message_content)  # Send the text message
            print(f"Sent message to {TARGET_BOT_USERNAME}: {message_content}")

        # Start listening for responses from the target bot BEFORE sending messages.
        asyncio.create_task(listen_for_target_responses(TARGET_BOT_USERNAME, user_id, chat_id))


    except Exception as e:
        print(f"Error sending message to target bot: {e}")
        await bot1.send_message(chat_id, f"Error communicating with the other bot.")


async def listen_for_target_responses(target_username, user_id, chat_id, timeout=60):
    """Listens for responses from the target bot and sends them to the user."""
    try:
        @user_bot.on(events.NewMessage(from_users=target_username))
        async def handle_target_response(event):
            global user_data
            response_text = event.message.text
            print(f"Received response from {target_username}: {response_text}")

            if user_id in user_data:
                user_data[user_id]["response"].append(response_text) # Add the new response to the list
                await bot1.send_message(chat_id, f"Answer for your question : {response_text}") # Send message to user
                print(f"Sent response to user {user_id}: {response_text}")

                # Clear the user data *after* sending the response
                del user_data[user_id]
                print(f"User data cleared for user {user_id}")

            else:
                print(f"No user data found for {user_id} while handling target response.")

    except Exception as e:
        print(f"Error listening for response from {target_username}: {e}")


async def main():
    # Start both clients concurrently
    await asyncio.gather(
        bot1.start(),  # Listener Bot
        user_bot.start(phone=PHONE_NUMBER) # User Bot
    )
    print("Both bots started.")
    # Keep the main task running so the event loop doesn't exit
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        await bot1.disconnect()
        await user_bot.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
