import logging
import os
from sqlalchemy.orm import Session
from .config.db import engine
from .config.logging import configure_logging
from .models.userModels import UserModel, UserRole
from .models.accountModels import AccountModel
from .models.chatModels import ChatMessages
from passlib.hash import bcrypt

configure_logging()
logger = logging.getLogger(__name__)

SUPERADMIN_USERNAME = os.environ.get("SUPERADMIN_USERNAME", "superadmin")
SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "superadmin@example.com")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "supersecret")

# Hash the password
hashed_password = bcrypt.hash(SUPERADMIN_PASSWORD)


def seed_superadmin():
    with Session(engine) as session:
        # Check if a superadmin user already exists
        user = session.query(UserModel).filter_by(
            username=SUPERADMIN_USERNAME).first()
        if user:
            logger.info(
                "Superadmin already exists",
                extra={"event": "superadmin.exists"},
            )
            return
        # Create an account for the superadmin if needed
        account = session.query(AccountModel).filter_by(
            name="SuperAdminAccount").first()
        if not account:
            account = AccountModel(name="SuperAdminAccount")
            session.add(account)
            session.commit()
            session.refresh(account)
        # Create the superadmin user
        superadmin = UserModel(
            account_id=account.id,
            username=SUPERADMIN_USERNAME,
            email=SUPERADMIN_EMAIL,
            password=hashed_password,
            role=UserRole.SUPER_ADMIN
        )
        session.add(superadmin)
        session.commit()
        logger.info(
            "Superadmin created",
            extra={"event": "superadmin.created"},
        )


if __name__ == "__main__":
    seed_superadmin()
