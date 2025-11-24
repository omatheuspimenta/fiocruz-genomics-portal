from elasticsearch import AsyncElasticsearch
from app.core.config import settings

class ElasticsearchClient:
    client: AsyncElasticsearch = None

    async def connect(self):
        if self.client is None:
            self.client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
            print(f"✓ Connecting to Elasticsearch at {settings.ELASTICSEARCH_URL}")

    async def close(self):
        if self.client:
            await self.client.close()
            print("✓ Closed Elasticsearch connection")

es_client = ElasticsearchClient()

async def get_es_client() -> AsyncElasticsearch:
    if es_client.client is None:
        await es_client.connect()
    return es_client.client
