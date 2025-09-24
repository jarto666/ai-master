from motor.motor_asyncio import AsyncIOMotorClient
from .settings import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.get_default_database()  # "mastering" from URI