from src.loaders.database import get_database
from models import User
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, or_
from google.cloud import storage
from fastapi import HTTPException


import bcrypt

from src.interface import IFilterUser
from src.enums import UserRole

class UserRepository:
    def __init__(self):
        self.db = get_database()

    # create
    async def create_user(self, email: str, username: str, password: str, role: int = UserRole.USER):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(
            email=email,
            username=username,
            password=hashed_password.decode('utf-8'),
            role=role,
            generator_working=False,
            current_token=None,
            avatar=None 
        )
        self.db.add(new_user)
        try:
            await self.db.commit()
            return new_user
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("username_or_email_exist")
    
    # get one
    async def get_one(self, filter: IFilterUser) -> User | None:
        query = self.build_query(filter)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def find_by_pk(self, id: int) -> User | None:
        query = select(User).where(User.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_username_from_uid(self, uid: int) -> str:
        user = await self.find_or_fail(uid)
        return user.username
    
    # update
    async def change_password(self, uid: int, new_password: str):
        user = await self.find_or_fail(uid)
        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password = new_hashed_password
        await self.db.commit()

    async def update_user(self, uid: int, new_email: str, new_username: str) -> bool:
        user = await self.find_or_fail(uid)
        user.email = new_email
        user.username = new_username

        try:
            await self.db.commit()
            return user
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("username_or_email_exist")
    
    def upload_avatar(self, uid: str, file):
        """Upload avatar for a user and update Firestore.

        Args:
            uid (str): User ID.
            file: File object of the avatar image.

        Returns:
            str: Public URL of the uploaded avatar.
        """
        # Initialize the Cloud Storage client
        storage_client = storage.Client()
        bucket_name = 'nabingx_bucket'
        bucket = storage_client.bucket(bucket_name)

        # Create a new blob and upload the file's content.
        blob = bucket.blob(f'avatars/{uid}/{file.filename}')
        blob.upload_from_file(file.file)

        # No need to call make_public() because we're using uniform bucket-level access
        # Instead, configure the bucket IAM policy to allow public access to objects if needed

        # Make the blob public
        blob.make_public()

        # Update Firestore with the avatar URL
        avatar_url = blob.public_url
        user_ref = self._db.collection('users').document(uid)
        user_ref.update({'avatar': avatar_url})

        return avatar_url


    async def update_avatar_url(self, uid: int, avatar_url: str):
        user = await self.find_or_fail(uid)
        user.avatar_url = avatar_url
        await self.db.commit()

    async def update_generator_working_status(self, uid: str, generator_working: bool):
        user = await self.find_or_fail(uid)
        user.generator_working = generator_working
        await self.db.commit()

    # delete
    async def delete_user(self, uid: int) -> bool:
        user = await self.find_or_fail(uid)
        await self.db.delete(user)
        await self.db.commit()
    
    # validate
    async def validate_unique_username_or_email(self, username_or_email: str):
        user = await self.get_one(IFilterUser(username_or_email)) 
        if user:
            raise HTTPException(status_code=400, detail="user.username_or_email_exist")

    async def find_or_fail(self, id: int):
        user = await self.find_by_pk(id)
        if not user:
            raise HTTPException(status_code=400, detail="user.not_found")
        return user
    
    # helper
    def build_query(filter: IFilterUser):
        conditions = []
        
        if filter.email_or_username:
            conditions.append(
                or_(User.email == filter.email_or_username, User.username == filter.email_or_username)
            )
        else:
            if filter.email:
                conditions.append(User.email == filter.email)
            if filter.username:
                conditions.append(User.username == filter.username)
        
        if conditions:
            return select(User).where(*conditions)
        
        return select(User)