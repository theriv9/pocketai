from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import os

load_dotenv()

client = CosmosClient(os.getenv("COSMOS_ENDPOINT"), os.getenv("COSMOS_KEY"))
db = client.get_database_client("PocketAI_DB")
container = db.get_container_client("Receipts")

# Delete all items
items = list(container.query_items("SELECT * FROM c", enable_cross_partition_query=True))
for item in items:
    container.delete_item(item, partition_key=item['id'])

print(f"DELETED {len(items)} receipts!")


# Add to clear_db.py
container.delete_container()  # Delete container
db.create_container(id="Receipts", partition_key=PartitionKey(path="/id"))
print("CONTAINER RESET!")