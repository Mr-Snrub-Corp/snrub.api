from pathlib import Path

from app.models.user import UserRole, UserStatus

PHOTOS_DIR = Path(__file__).parent / "photos"

PASSWORD_HASH = "$2b$12$MUjFO0aqKG669iMeDMwoB.CCSl62Wyn92jNJZhE7t0abKVgkLczWa"

USERS = [
    {
        "email": "w.smithers@snrub-corp.io",
        "name": "Waylon Smithers",
        "role": UserRole.SUPER_ADMIN,
        "status": UserStatus.ACTIVE,
        "photo_file": "w_smithers.png",
    },
    {
        "email": "c.carlson@snrub-corp.io",
        "name": "Carl Carlson",
        "role": UserRole.ADMIN,
        "status": UserStatus.ACTIVE,
        "photo_file": "c_carlson.png",
    },
    {
        "email": "c.charlie@snrub-corp.io",
        "name": "Charlie",
        "role": UserRole.ADMIN,
        "status": UserStatus.ACTIVE,
        "photo_file": "c_charlie.png",
    },
    {
        "email": "l.leonard@snrub-corp.io",
        "name": "Lenny Leonard",
        "role": UserRole.CREATOR,
        "status": UserStatus.ACTIVE,
        "photo_file": "l_leonard.png",
    },
    {
        "email": "f.grimes@snrub-corp.io",
        "name": "Frank Grimes",
        "role": UserRole.CREATOR,
        "status": UserStatus.DECEASED,
        "photo_file": "f_grimes.png",
    },
    {
        "email": "canary.m.burns@snrub-corp.io",
        "name": "Canary M. Burns",
        "role": UserRole.CREATOR,
        "status": UserStatus.ACTIVE,
        "photo_file": "canary_m_burns.png",
    },
    {
        "email": "angel.of.death@snrub-corp.io",
        "name": "Angel of Death",
        "role": UserRole.CREATOR,
        "status": UserStatus.ACTIVE,
        "photo_file": "angel_of_death.png",
    },
    {
        "email": "t.jankovsky@snrub-corp.io",
        "name": "Tibor Jankovsky",
        "role": UserRole.VIEWER,
        "status": UserStatus.ACTIVE,
        "photo_file": "t_jankovsky.png",
    },
    {
        "email": "h.simpson@snrub-corp.io",
        "name": "Homer Simpson",
        "role": UserRole.VIEWER,
        "status": UserStatus.ACTIVE,
        "photo_file": "h_simpson.png",
    },
    {
        "email": "b.bernie@snrub-corp.io",
        "name": "Bernie",
        "role": UserRole.VIEWER,
        "status": UserStatus.SUSPENDED,
        "photo_file": "b_bernie.png",
    },
]


def get_users() -> list[dict]:
    result = []
    for user_data in USERS:
        entry = {**user_data}
        photo_file = entry.pop("photo_file")
        photo_path = PHOTOS_DIR / photo_file
        entry["photo"] = photo_path.read_bytes() if photo_path.exists() else None
        entry["password"] = PASSWORD_HASH
        result.append(entry)
    return result
