from firetail.lifecycle import FiretailResponse


async def aiohttp_validate_responses():
    return FiretailResponse(body=b'{"validate": true}')
