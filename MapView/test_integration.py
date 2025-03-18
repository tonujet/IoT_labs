import pytest
import asyncio
import websockets
import json
from main import SERVER_URL


@pytest.mark.asyncio
async def test_websocket_connection(app):
    async with websockets.connect(SERVER_URL) as websocket:
        assert websocket.open

@pytest.mark.asyncio
async def test_websocket_disconnection_reconnection(app):
    async with websockets.connect(SERVER_URL) as websocket:
        await websocket.close()
        assert not websocket.open
        async with websockets.connect(SERVER_URL) as websocket_reconnect:
            assert websocket_reconnect.open

@pytest.mark.asyncio
async def test_invalid_websocket_message_format(app):
    async with websockets.connect(SERVER_URL) as websocket:
        invalid_message = "invalid_message"
        await websocket.send(invalid_message)
        await asyncio.sleep(1)
        assert app.map.road_state is None

@pytest.mark.asyncio
async def test_multiple_websocket_messages(app):
    async with websockets.connect(SERVER_URL) as websocket:
        messages = [
            json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 25.0}, "road_state": "Even", "rain_state": "Clear"}),
            json.dumps({"agent_data": {"gps": {"latitude": 50.450387, "longitude": 30.524548}, "temperature": 26.0}, "road_state": "Pit", "rain_state": "Rain"})
        ]
        for message in messages:
            await websocket.send(message)
            await asyncio.sleep(1)
        assert app.map.car_marker.lat == 50.450387
        assert app.map.car_marker.lon == 30.524548
        assert app.map.temp == 26.0
        assert app.map.road_state == "Pit"
        assert app.map.rain_state == "Rain"

@pytest.mark.asyncio
async def test_rain_marker_opacity(app):
    async with websockets.connect(SERVER_URL) as websocket:
        message = json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 25.0}, "road_state": "Even", "rain_state": "Downpour"})
        await websocket.send(message)
        await asyncio.sleep(1)
        assert app.map.rain_widget.opacity == 0.07

@pytest.mark.asyncio
async def test_temperature_widget_update(app):
    async with websockets.connect(SERVER_URL) as websocket:
        message = json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 30.0}, "road_state": "Even", "rain_state": "Clear"})
        await websocket.send(message)
        await asyncio.sleep(1)
        assert app.map.temp_widget.text == "🌡️30.0°C🌡️"

@pytest.mark.asyncio
async def test_road_state_handling_potholes(app):
    async with websockets.connect(SERVER_URL) as websocket:
        message = json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 25.0}, "road_state": "Pit", "rain_state": "Clear"})
        await websocket.send(message)
        await asyncio.sleep(1)
        assert app.map.road_state == "Pit"

@pytest.mark.asyncio
async def test_road_state_handling_speeding_bumps(app):
    async with websockets.connect(SERVER_URL) as websocket:
        message = json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 25.0}, "road_state": "Speeding bump", "rain_state": "Clear"})
        await websocket.send(message)
        await asyncio.sleep(1)
        assert app.map.road_state == "Speeding bump"

@pytest.mark.asyncio
async def test_car_marker_update(app):
    async with websockets.connect(SERVER_URL) as websocket:
        message = json.dumps({"agent_data": {"gps": {"latitude": 50.450386, "longitude": 30.524547}, "temperature": 25.0}, "road_state": "Even", "rain_state": "Clear"})
        await websocket.send(message)