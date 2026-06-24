from uuid import UUID

from orchestrator.core.db import db
from orchestrator.core.db.database import BaseModel
from sqlalchemy import String, select, text
from sqlalchemy.orm import mapped_column

from pydantic_forms.types import UUIDstr


class CustomerTable(BaseModel):
    __tablename__ = "customers"

    # Only customer_id is mandatory for the customer table, the other fields are optional and can be chosen by the user
    customer_id = mapped_column(String, server_default=text("uuid_generate_v4()"), primary_key=True)
    fullname = mapped_column(String(255))
    shortcode = mapped_column(String(255), index=True)

    @classmethod
    def get_customer_name(cls, customer_id: UUID | UUIDstr) -> str | None:
        stmt = select(cls.fullname).where(cls.customer_id == str(customer_id))
        return db.session.execute(stmt).scalars().one_or_none()
