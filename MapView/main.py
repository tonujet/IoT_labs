import asyncio
import json
from threading import Thread

import logging
import websockets
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.label import Label
from kivy_garden.mapview import MapMarker
from kivy_garden.mapview import MapView, MapLayer
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout

import fileDatasource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SERVER_URL = "ws://localhost:8000/ws/1"


def get_overlay_pos(margin_x, margin_y):
    return Window.width + margin_x, Window.height + margin_y


class RainMarker(MapLayer):
    def __init__(self, lat, lon, radius=100, opacity=0.1, **kwargs):
        super().__init__(**kwargs)
        self.lat = lat
        self.lon = lon
        self.radius = radius
        self.fade_radius = 100
        self.opacity = opacity
        self.circle = None

    def reposition(self):
        self.canvas.clear()

        x, y = self.parent.get_window_xy_from(self.lat, self.lon, self.parent.zoom)

        zoom_factor = 2 ** (self.parent.zoom - 16)
        radius_pixels = self.radius * zoom_factor
        fade_radius_pixels = self.fade_radius * zoom_factor

        num_fade_layers = 20
        for i in range(num_fade_layers):
            current_radius = radius_pixels + (fade_radius_pixels * (i / num_fade_layers))
            opacity = self.opacity * (1 - (i / num_fade_layers))

            with self.canvas:
                Color(0, 0, 1, opacity)
                Ellipse(
                    pos=(x - current_radius, y - current_radius),
                    size=(2 * current_radius, 2 * current_radius)
                )


class CustomWidget(MapLayer):
    def __init__(self, text, margin=(-205, -55), size=(200, 50), color=(0.2, 0.6, 1, 0.8), radius=10,  **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.color = color
        self.size = size
        self.radius = radius
        self.margin = margin
        self.label = None

    def draw(self):
        if self.label:
            self.remove_widget(self.label)

        self.canvas.clear()
        pos = get_overlay_pos(*self.margin)
        s, r = self.size, self.radius

        with self.canvas:
            Color(*self.color)

            # Main rectangle
            Rectangle(
                pos=(pos[0] + r, pos[1] + r),
                size=(s[0] - 2 * r, s[1] - 2 * r)
            )

            # Corner circles (Ellipses)
            Ellipse(pos=pos, size=(2 * r, 2 * r)),  # Bottom-left corner
            Ellipse(pos=(pos[0] + s[0] - 2 * r, pos[1]),
                    size=(2 * r, 2 * r)),  # Bottom-right
            Ellipse(pos=(pos[0], pos[1] + s[1] - 2 * r),
                    size=(2 * r, 2 * r)),  # Top-left
            Ellipse(pos=(pos[0] + s[0] - 2 * r,
                         pos[1] + s[1] - 2 * r),
                    size=(2 * r, 2 * r))  # Top-right

            # Rectangles for the edges between the corners
            Rectangle(pos=(pos[0] + r, pos[1]),
                      size=(s[0] - 2 * r, r)),  # Bottom edge
            Rectangle(pos=(pos[0] + r, pos[1] + s[1] - r),
                      size=(s[0] - 2 * r, r)),  # Top edge
            Rectangle(pos=(pos[0], pos[1] + r),
                      size=(r, s[1] - 2 * r)),  # Left edge
            Rectangle(pos=(pos[0] + s[0] - r, pos[1] + r),
                      size=(r, s[1] - 2 * r))  # Right edge

        self.label = Label(
            text=self.text,
            size_hint=(None, None),
            size=(200, 50),
            pos=(pos[0], pos[1]),
            color=(1, 1, 1, 1),
            bold=True,
            font_size=23,
            font_name="seguiemj.ttf"
        )

        self.add_widget(self.label)


class Map(FloatLayout):
    car_label: str = None
    rain_label: str = None
    road_state: str = None
    rain_state: str = None
    speeding_bump_counter: int = 4
    temp: float = None

    car_marker: MapMarker = None
    rain_rect: Rectangle = None
    rain_widget: CustomWidget = None
    temp_widget: CustomWidget = None

    def build(self):
        return self.mapview

    def __init__(self):
        super().__init__()
        self.mapview = MapView(zoom=15, lat=50.450386085935094, lon=30.524547100067142)
        self.add_widget(self.mapview)

        self.setup_car()
        self.set_basic_analysis()

        Clock.schedule_interval(self.update_state, 0.000001)

        self.pending_updates = []
        self.road_state_handlers = {
            "pit": self.set_pothole_marker,
            "speeding bump": self.set_bump_marker,
        }


    def setup_car(self):
        self.car_label = Label(
            size_hint=(None, None),
            size=(120, 40),
            color=(1, 0, 0, 1),
        )
        self.mapview.add_widget(self.car_label)

    def update_state(self, dt):
        self.update_rain_widget(dt)
        self.update_temp_widget(dt)
        self.update_layers(dt)
        self.update_label_position(dt)


    def process_updating_message(self, message):
        try:
            data = json.loads(json.loads(message))
            agent_data = data.get("agent_data")
            self.road_state = data.get("road_state")
            self.speeding_bump_fix()

            self.rain_state = data.get("rain_state")
            self.temp = agent_data.get("temperature")

            point = agent_data.get("gps")
            lat = point.get("latitude")
            lon = point.get("longitude")

            if lat is not None and lon is not None:
                Clock.schedule_once(lambda dt: self.update_markers(lat, lon))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid message format: {message}, error: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def set_rain_marker(self, lat, lon):
        opacity_map = {
            "Clear": 0,
            "Drizzle": 0.04,
            "Sprinkle": 0.05,
            "Shower": 0.055,
            "Rain": 0.06,
            "Downpour": 0.07,
        }
        opacity = opacity_map.get(self.rain_state, 0)
        if opacity > 0:
            marker = RainMarker(lat=lat, lon=lon, opacity=opacity)
            self.mapview.add_layer(marker)

    def update_rain_widget(self, dt):
        if self.rain_widget:
            self.mapview.remove_layer(self.rain_widget)

        rain_text = f"🌧️{self.rain_state if self.rain_state else 'Unknown'} 🌧️"
        self.rain_widget = CustomWidget(rain_text)
        self.rain_widget.draw()
        self.mapview.add_layer(self.rain_widget)

    def update_temp_widget(self, dt):
        if self.temp_widget:
            self.mapview.remove_layer(self.temp_widget)

        temp_text = f"🌡️{self.temp if self.temp else '~'}°C🌡️"
        self.temp_widget = CustomWidget(
            text=temp_text,
            margin=(-205, -115),
            color=(1, 0.5, 0, 0.8),
        )
        self.temp_widget.draw()
        self.mapview.add_layer(self.temp_widget)

    def update_layers(self, dt):
        for layer in self.mapview._layers:
            if hasattr(layer, 'reposition'):
                layer.reposition()

    def update_markers(self, lat, lon):
        handler = self.road_state_handlers.get(self.road_state.lower())
        if handler and len(self.pending_updates) == 0:
            self.pending_updates.append([3, handler, (lat, lon)])
        else:
            self.road_state = "Even"

        self.execute_pending_updates()

        if self.car_marker:
            self.mapview.remove_marker(self.car_marker)
        self.car_marker = MapMarker(lat=lat, lon=lon, source="images/car.png")
        self.mapview.add_marker(self.car_marker)

        self.set_rain_marker(lat, lon)

    def speeding_bump_fix(self):
        if self.road_state == "Speeding bump":
            self.speeding_bump_counter -= 1
            if self.speeding_bump_counter == 0:
                self.speeding_bump_counter = 4
            else:
                self.road_state = "Pit"

    def execute_pending_updates(self):
        for update in self.pending_updates:
            delay, handler, (lat, lon) = update
            update[0] = delay - 1
            if update[0] == 0:
                handler(lat, lon)
        self.pending_updates = [update for update in self.pending_updates if update[0] > 0]

    def update_label_position(self, dt):
        if not self.car_marker or not self.car_label or not self.road_state:
            return

        x, y = self.mapview.get_window_xy_from(
            self.car_marker.lat,
            self.car_marker.lon,
            self.mapview.zoom
        )

        self.car_label.pos = x - 60, y - 30
        self.car_label.text = self.road_state

    def set_pothole_marker(self, lat, lon):
        pothole_marker = MapMarker(lat=lat, lon=lon, source='images/pothole.png')
        self.mapview.add_marker(pothole_marker)

    def set_bump_marker(self, lat, lon):
        bump_marker = MapMarker(lat=lat, lon=lon, source='images/bump.png')
        self.mapview.add_marker(bump_marker)

    def set_basic_analysis(self):
        speed_bump_cor = fileDatasource.get_bump_cor()
        pothole_cor = fileDatasource.get_pothole_cor()

        for _, (lat, lon) in pothole_cor.iterrows():
            self.set_pothole_marker(lat, lon)

        for _, (lat, lon) in speed_bump_cor.iterrows():
            self.set_bump_marker(lat, lon)


class MyApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.map = Map()

    def build(self):
        return self.map

    def on_start(self):
        self.start_websocket_listener()

    def start_websocket_listener(self):
        websocket_thread = Thread(target=self.run_websocket_client, daemon=True)
        websocket_thread.start()
        logger.info("WebSocket listener started")

    def run_websocket_client(self):
        asyncio.run(self.connect_to_websocket())

    async def connect_to_websocket(self):
        try:
            async with websockets.connect(SERVER_URL, ping_interval=300, ping_timeout=100) as websocket:
                logger.info(f"Connected to {SERVER_URL}")
                while True:
                    message = await websocket.recv()
                    self.process_websocket_message(message)
        except Exception as e:
            logger.info(f"WebSocket connection error: {e}")

    def process_websocket_message(self, message):
        self.map.process_updating_message(message)


if __name__ == '__main__':
    MyApp().run()
