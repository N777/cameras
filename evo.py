import json
import os
from concurrent.futures.process import ProcessPoolExecutor
from os import getenv
import requests
import cv2
from jwt import JWT
from jwt.exceptions import JWTDecodeError

from detection import detect_free_spaces, create_reference


class EvoClient:
    _token = ""
    _login = getenv("login")
    _password = getenv("password")
    _token_file = "evo_token.json"

    def __init__(self):
        self._load_token_from_cache()

    def _load_token_from_cache(self):
        """Загружает токен из файлового кеша"""
        try:
            if os.path.exists(self._token_file):
                with open(self._token_file, "r") as f:
                    token_data = json.load(f)
                    self._token = token_data["token"]
            return False
        except Exception as e:
            print(f"Ошибка загрузки токена из кеша: {e}")
            return False

    def _save_token_to_cache(self, token):
        """Сохраняет токен в файловый кеш"""
        token_data = {
            "token": token,
        }
        with open(self._token_file, "w") as f:
            json.dump(token_data, f, indent=2)

    def get_new_token(self):
        data = {"login": self._login, "password": self._password}
        response = requests.post("https://api.vms.evo73.ru/v2/login", data=data)
        self._token = response.json()["data"]["token"]
        self._save_token_to_cache(self._token)

    @property
    def token(self):
        jwt_class = JWT()
        try:
            jwt_class.decode(self._token, do_verify=False)
        except JWTDecodeError:
            self.get_new_token()
        return "Bearer" + self._token

    def get_playlists(self):
        response = requests.get(
            "https://api.vms.evo73.ru/v2/playlist",
            headers={"Authorization": self.token},
        )
        return response.json()

    def get_cameras_from_playlist(self, playlist_id):
        response = requests.get(
            f"https://api.vms.evo73.ru/v2/playlist/{playlist_id}?get-all=true",
            headers={"Authorization": self.token},
        )
        return response.json()["cameras"]


def get_frame_from_stream(stream_url):
    """
    Простой способ чтения HLS потока с помощью OpenCV
    """
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        print("Ошибка: не удалось открыть поток")
        return

    ret, frame = cap.read()

    if not ret:
        print("Не удалось получить кадр")

    cap.release()
    return frame


def get_frame_with_detect(stream_url_with_camera_id):
    camera_id, stream_url = stream_url_with_camera_id
    frame = get_frame_from_stream(stream_url)
    grid_json = f"etalon/parking_grid_config_{camera_id}.json"
    detected_frame = detect_free_spaces(grid_json, frame)
    return detected_frame


def generate_etalon(stream_url_with_camera_id):
    camera_id, stream_url = stream_url_with_camera_id
    frame = get_frame_from_stream(stream_url)
    grid_json = f"etalon/parking_grid_config_{camera_id}.json"
    markup_frame = create_reference(frame, grid_json)
    return markup_frame


def get_stream_urls():
    client = EvoClient()
    playlists = client.get_playlists()["playlists"]
    park_playlist = next(filter(lambda p: p["name"] == "parking", playlists))
    park_playlist_id = park_playlist["id"]
    cameras = client.get_cameras_from_playlist(park_playlist_id)
    stream_urls = {camera["camera_id"]: camera["stream_url"] for camera in cameras}
    return stream_urls


def generate_etalon_for_cameras():
    stream_urls = get_stream_urls()
    with ProcessPoolExecutor(max_workers=len(stream_urls)) as executor:
        future_results = list(executor.map(generate_etalon, stream_urls.items()))
    frames = [frame for frame in future_results if frame is not None]
    return frames


def get_images_from_stream(detect: bool):
    stream_urls = get_stream_urls()
    with ProcessPoolExecutor(max_workers=len(stream_urls)) as executor:
        if detect:
            future_results = list(executor.map(get_frame_with_detect, stream_urls.items()))
        else:
            future_results = list(executor.map(get_frame_from_stream, stream_urls.values()))
    frames = [frame for frame in future_results if frame is not None]
    return frames
