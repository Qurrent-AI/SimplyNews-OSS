from typing import Any, Dict, Optional
from uuid import UUID

import uvloop
from quart import Response, request

from qurrent import (
    HTTPMethod,
    Ingress,
    QurrentConfig,
    WebServer,
    events,
    spawn_task,
)

from workflow import SimplyNews


class GenericWebServerIntegration:
    ingress: Ingress
    _registry: Dict[UUID, UUID]

    @staticmethod
    async def start(
        config: QurrentConfig,
        base_url: Optional[str] = None,
        host: str = "0.0.0.0",
        port: int = 8085,
        webhook_endpoint: str = "/start",
    ) -> "GenericWebServerIntegration":
        self = GenericWebServerIntegration()

        self.ingress = config.get("INGRESS")
        self._registry = {}

        server = await WebServer.start(host, port)

        @server.route(webhook_endpoint, methods=[HTTPMethod.POST])
        async def webhook_listener() -> Response:
            data: Dict = await request.get_json()

            await self.process_webhook(data)

            return Response(status=200)

        return self

    async def process_webhook(self, data: Dict) -> None:
        event = events.GenericWebhookEvent(
            workflow_instance_id=None,
            data=data,
        )
        await self.ingress.add_event(event)

    def link(self, workflow_instance_id: UUID, source_id: UUID) -> None:
        self._registry[source_id] = workflow_instance_id

    def unlink(self, source_id: UUID) -> None:
        self._registry.pop(source_id, None)


async def handle_event(config: QurrentConfig, data) -> None:
    description = data.get("description")
    name = data.get("name")
    custom_podcast = await SimplyNews.create(config=config)

    try:
        await custom_podcast.run(description, name)
    except Exception as e:
        print(
            f"Error running workflow instance {custom_podcast.workflow_instance_id}: {e}"
        )
        await custom_podcast.close(status="failed")
    else:
        await custom_podcast.close(status="completed")


async def main() -> None:
    qconfig = await QurrentConfig.from_file("config.yaml")

    await GenericWebServerIntegration.start(qconfig)

    while True:
        data = await qconfig["INGRESS"].get(-1)
        spawn_task(handle_event(qconfig, data.get("data")))


if __name__ == "__main__":
    uvloop.run(main())
