"""Create or promote a superuser.

The ``is_superuser`` flag is deliberately not exposed on the API schemas, so a
superuser is bootstrapped out-of-band with this script.

Usage:
    uv run python -m scripts.create_superuser --email admin@habit.rpg --password secret123 --name Admin

If a user with the given email already exists, it is promoted to superuser
instead of being recreated.
"""

import argparse
import asyncio

from apps.core.security import hash_password
from apps.db.session import AsyncSessionLocal
from apps.CRUD.from_models.user import user_crud


async def create_superuser(email: str, password: str, name: str) -> None:
    async with AsyncSessionLocal() as db:
        existing = await user_crud.get_by_email(db, email)
        if existing:
            if existing.is_superuser:
                print(f"User {email} is already a superuser.")
                return
            existing.is_superuser = True
            await db.commit()
            print(f"Promoted existing user {email} to superuser.")
            return

        user = await user_crud.create(
            db,
            {
                "name": name,
                "email": email.lower(),
                "password": hash_password(password),
                "is_superuser": True,
            },
        )
        print(f"Created superuser {user.email} (id={user.id}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote a superuser.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Admin")
    args = parser.parse_args()

    asyncio.run(create_superuser(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
