from aiohttp import web

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "ok",
        "service": "MzBotz File Store Bot",
        "powered_by": "MzBotz"
    })


async def web_server():
    app = web.Application(client_max_size=30 * 1024 * 1024)  # 30MB
    app.add_routes(routes)
    return app
