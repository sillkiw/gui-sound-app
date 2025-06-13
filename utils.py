import json

def format_time(ms):
    """
    Преобразует миллисекунды в формат MM:SS для отображения.
    """
    s = ms // 1000
    m, s = divmod(int(s), 60)
    return f"{m:02d}:{s:02d}"


def save_playlist_json(path: str, playlist: list[dict]):
    """
    Сохраняет плейлист в JSON-файл.
    Из каждого трека берёт только 'path', 'title' и 'duration'.
    """
    serializable = []
    for tr in playlist:
        serializable.append({
            'path':     tr['path'],
            'title':    tr['title'],
            'duration': tr['duration']
        })
    data = {'playlist': serializable}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_playlist_json(path: str) -> list[dict]:
    """
    Загружает плейлист из JSON-файла и возвращает список треков.
    Ожидаемый формат тот же, что и при сохранении.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("playlist", [])
