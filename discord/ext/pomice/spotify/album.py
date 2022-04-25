from .track import Track


class Album:
    """The base class for a Spotify album"""

    def __init__(self, data: dict) -> None:
        self.name = data["name"]
        self.artists = ", ".join(artist["name"] for artist in data["artists"])
        self.image = data["images"][0]["url"]
        self.tracks = [Track(track, image=self.image) for track in data["tracks"]["items"]]
        self.total_tracks = data["total_tracks"]
        self.id = data["id"]
        self.uri = data["external_urls"]["spotify"]

    def __repr__(self) -> str:
        return (
            f"<Pomice.spotify.Album name={self.name} artists={self.artists} id={self.id} "
            f"total_tracks={self.total_tracks} tracks={self.tracks}>"
        )
