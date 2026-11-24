from __future__ import annotations

import json
import typing
from pathlib import Path


class Version(typing.TypedDict):
    version_name: str
    major: int
    minor: int
    patch: int
    stage: typing.Literal["alpha", "beta", "rc"] | None
    stage_number: int | None
    build: int


class VersionManager:
    VALID_STAGES: typing.ClassVar[set] = {"alpha", "beta", "rc", None}

    def __init__(self, file_path: str = "version.json"):
        self.file_path = Path(file_path)
        self.data = self.read()

    def read(self) -> Version:
        if not self.file_path.exists():
            msg = f"Version file not found: {self.file_path}"
            raise FileNotFoundError(msg)

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.loads(file.read())

        self._validate(data)
        return data

    def write(self):
        self._validate(self.data)

        temp_file = self.file_path.with_suffix(self.file_path.suffix + ".tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=4, ensure_ascii=False)
            file.write("\n")

        temp_file.replace(self.file_path)

    def _validate(self, data: typing.Any):
        required = {"version_name", "major", "minor", "patch", "stage", "stage_number", "build"}

        if not isinstance(data, dict):
            msg = "Version data must be a JSON object"
            raise ValueError(msg)

        if not required.issubset(data):
            msg = "Missing version fields"
            raise ValueError(msg)

        for field in ("major", "minor", "patch", "build"):
            value = data[field]

            if type(value) is not int or value < 0:
                msg = f"{field} must be a non-negative integer"
                raise ValueError(msg)

        if not isinstance(data["version_name"], str):
            msg = "version_name must be a string"
            raise ValueError(msg)

        if data["stage"] not in self.VALID_STAGES:
            msg = "Invalid release stage"
            raise ValueError(msg)

        stage_number = data["stage_number"]

        if data["stage"] is None:
            if stage_number is not None:
                msg = "Stable versions must have null stage_number"
                raise ValueError(msg)
        elif type(stage_number) is not int or stage_number < 1:
            msg = "Prerelease stage_number must be >= 1"
            raise ValueError(msg)

    @property
    def major(self):
        return self.data["major"]

    @property
    def minor(self):
        return self.data["minor"]

    @property
    def patch(self):
        return self.data["patch"]

    @property
    def stage(self):
        return self.data["stage"]

    @property
    def build(self):
        return self.data["build"]

    def get_version(self):
        version = f"{self.major}.{self.minor}.{self.patch}"

        if self.stage is not None:
            version += f"-{self.stage}.{self.data['stage_number']}"

        return version

    def get_full_version(self):
        return f"{self.data['version_name']} v{self.get_version()} (Build {self.build})"

    def set_stage(self, stage: typing.Literal["alpha", "beta", "rc"] | None):
        if stage not in self.VALID_STAGES:
            msg = "Invalid release stage"
            raise ValueError(msg)

        if stage != self.stage:
            self.data["stage"] = stage
            self.data["stage_number"] = 1 if stage is not None else None

        self.write()

    def next_prerelease(self):
        if self.stage is None:
            msg = "Stable versions cannot have prereleases"
            raise ValueError(msg)

        if self.data["stage_number"] is None:
            self.data["stage_number"] = 1
        else:
            self.data["stage_number"] += 1
        self.write()

    def release(self):
        self.data["stage"] = None
        self.data["stage_number"] = None
        self.write()

    def increment_major(self):
        self.data["major"] += 1
        self.data["minor"] = 0
        self.data["patch"] = 0
        self._reset_stage()
        self.write()

    def increment_minor(self):
        self.data["minor"] += 1
        self.data["patch"] = 0
        self._reset_stage()
        self.write()

    def increment_patch(self):
        self.data["patch"] += 1
        self._reset_stage()
        self.write()

    def _reset_stage(self):
        self.data["stage"] = None
        self.data["stage_number"] = None

    def increment_build(self):
        self.data["build"] += 1
        self.write()

    def increment(self, stage: typing.Literal["major", "minor", "patch", "build"]):
        match stage:
            case "major":
                self.increment_major()
            case "minor":
                self.increment_minor()
            case "patch":
                self.increment_patch()
            case "build":
                self.increment_build()
            case _:
                msg = f"Invalid stage: {stage}"
                raise ValueError(msg)

    def set_version_name(self, version_name: str):
        if not isinstance(version_name, str):
            msg = "version_name must be a string"
            raise ValueError(msg)

        self.data["version_name"] = version_name
        self.write()


version_manager = VersionManager()
