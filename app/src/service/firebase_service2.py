"""This module handles all Firebase Firestore services.

@Author: Karthick T. Sharma
"""

import os
import firebase_admin

from firebase_admin import firestore
from firebase_admin import credentials

from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker,selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import User, Question, Choice, Comment, Rating
from deep_translator import GoogleTranslator
from google.cloud import storage
import bcrypt
# from passlib.hash import bcrypt
import jwt
import datetime
import uuid
from typing import Optional, Dict, List
import xml.etree.ElementTree as ET

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'D:/GR2/quizzzy2/quizzzy-backend/app/secret/serviceAccountKey.json'

class FirebaseService:
    """FirebaseService"""
    """Handle firestore operations."""

    def __init__(self):
        """Initialize firebase firestore client."""
        firebase_admin.initialize_app(
            credentials.Certificate("secret/serviceAccountKey.json"))
        self._db = firestore.client()
    
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
        # user_ref = self._db.collection('users').document(uid)
        # user_ref.update({'avatar': avatar_url})

        return avatar_url