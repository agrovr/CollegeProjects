import os

import pygame


SOUND_FILES = {
    "ambience": "forge_ambience.wav",
    "pickup": "crystal_pickup.wav",
    "trap": "trap_burst.wav",
    "turn": "shift_turn.wav",
    "lift": "skyforge_lift.wav",
    "portal": "portal_chime.wav",
    "scare": "forge_scare.wav",
}

STEP_FILES = (
    "stone_step_1.wav",
    "stone_step_2.wav",
    "stone_step_3.wav",
)

STEP_ORDER = (0, 1, 2, 1)


def initialize(folder):
    audio_data = {
        "enabled": False,
        "sounds": {},
        "step_index": 0,
        "ambience_channel": None,
        "step_channel": None,
    }

    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(44100, -16, 2, 512)

        pygame.mixer.set_num_channels(12)
        pygame.mixer.set_reserved(2)
        audio_data["ambience_channel"] = pygame.mixer.Channel(0)
        audio_data["step_channel"] = pygame.mixer.Channel(1)

        for name, filename in SOUND_FILES.items():
            path = os.path.join(folder, filename)
            audio_data["sounds"][name] = pygame.mixer.Sound(path)

        audio_data["sounds"]["step"] = [
            pygame.mixer.Sound(os.path.join(folder, filename))
            for filename in STEP_FILES
        ]

        volumes = {
            "ambience": 0.22,
            "pickup": 0.48,
            "trap": 0.52,
            "turn": 0.43,
            "lift": 0.50,
            "portal": 0.60,
            "scare": 0.64,
        }
        for name, volume in volumes.items():
            audio_data["sounds"][name].set_volume(volume)
        for step_sound in audio_data["sounds"]["step"]:
            step_sound.set_volume(0.08)

        audio_data["enabled"] = True
        audio_data["ambience_channel"].play(
            audio_data["sounds"]["ambience"], -1, fade_ms=1200
        )
    except (FileNotFoundError, pygame.error) as error:
        print(f"Audio unavailable, continuing silently: {error}")
        audio_data["sounds"] = {}

    return audio_data


def play(audio_data, name):
    if not audio_data["enabled"] or name not in audio_data["sounds"]:
        return

    if name == "step":
        order_index = audio_data["step_index"] % len(STEP_ORDER)
        sound_index = STEP_ORDER[order_index]
        step_sound = audio_data["sounds"]["step"][sound_index]
        audio_data["step_channel"].play(step_sound)
        audio_data["step_index"] += 1
    else:
        audio_data["sounds"][name].play()


def toggle(audio_data):
    if not audio_data["sounds"]:
        return False

    audio_data["enabled"] = not audio_data["enabled"]
    if audio_data["enabled"]:
        audio_data["ambience_channel"].play(
            audio_data["sounds"]["ambience"], -1, fade_ms=450
        )
    else:
        pygame.mixer.stop()
    return audio_data["enabled"]


def shutdown(audio_data):
    if audio_data["sounds"]:
        pygame.mixer.stop()
