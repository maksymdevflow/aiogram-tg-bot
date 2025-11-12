from firebase_admin import firestore
from google.cloud.firestore import Client
import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def get_firestore_client() -> Client:
    """
    Get Firestore database client.
    Creates the client lazily to ensure Firebase is initialized first.
    """
    return firestore.client()


def verify_database_connection() -> bool:
    """
    Verify that Firestore is accessible.
    
    Returns:
        True if database is accessible, False otherwise
    """
    try:
        db = get_firestore_client()
        collections = db.collections()
        list(collections)
        logger.info("Firestore connection verified")
        return True
    except Exception as e:
        logger.error(
            f"Error verifying Firestore connection: {str(e)}\n"
        )
        return False


def add_user_sync(data: dict) -> Optional[str]:
    """
    Synchronously add a user to Firestore.
    
    Args:
        data: Dictionary containing user data
        
    Returns:
        The document ID of the new user entry, or None if error occurs
    """
    try:
        db = get_firestore_client()
        user_data = {
            **data,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = db.collection("users").add(user_data)
        doc_id = doc_ref[1].id
        logger.info(f"User added to Firestore with document ID: {doc_id}")
        return doc_id
    except Exception as e:
        logger.error(f"Error adding user to Firestore: {str(e)}", exc_info=True)
        return None


def add_resume_sync(resume: dict) -> Optional[str]:
    """
    Synchronously add a resume to Firestore.
    
    Resumes are saved in the 'resumes' collection with user_id as document ID.
    This allows one resume per user, or you can use subcollections for multiple resumes.
    
    Args:
        resume: Dictionary containing resume data (must include user_id as int)
        
    Returns:
        The document ID of the new resume entry, or None if error occurs
    """
    try:
        user_id = resume.get("user_id")
        
        # Log original user_id for debugging
        logger.debug(f"Original user_id from resume: {user_id}, type: {type(user_id)}")
        
        # Validate user_id - must be present and be an integer
        if user_id is None:
            logger.error("Resume data missing user_id. Resume keys: %s", list(resume.keys()))
            return None
        
        # Ensure user_id is int
        if not isinstance(user_id, int):
            try:
                user_id = int(user_id)
                logger.debug(f"Converted user_id to int: {user_id}")
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Invalid user_id type: {type(user_id)}, value: {user_id}, error: {str(e)}"
                )
                return None
        
        # Final validation - ensure user_id is a valid positive integer
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id value: {user_id} (must be positive integer)")
            return None
        
        # Ensure username is None if not provided (not empty string)
        username = resume.get("username")
        if username == "":
            username = None
        elif username is not None and not isinstance(username, str):
            username = str(username) if username else None
        
        db = get_firestore_client()
        
        # Create a copy of resume data without user_id and username to avoid overwriting
        resume_clean = {k: v for k, v in resume.items() if k not in ("user_id", "username")}
        
        resume_with_timestamp = {
            **resume_clean,
            "user_id": user_id,  # Always int, explicitly set
            "username": username,  # str or None, explicitly set
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        
        # Log final values before saving
        logger.debug(
            f"Final values before saving - user_id: {user_id} (type: {type(user_id)}), "
            f"username: {username} (type: {type(username)})"
        )
        
        doc_ref = db.collection("resumes").document(str(user_id))
        doc_ref.set(resume_with_timestamp)
        
        # Verify what was actually saved
        saved_doc = doc_ref.get()
        if saved_doc.exists:
            saved_data = saved_doc.to_dict()
            saved_user_id = saved_data.get("user_id") if saved_data else None
            logger.info(
                f"Resume added to Firestore - user_id: {user_id} (saved as: {saved_user_id}, type: {type(saved_user_id)}), "
                f"username: {username}, document_id: {user_id}"
            )
        else:
            logger.warning(f"Resume document was not found after saving - user_id: {user_id}")
            logger.info(
                f"Resume added to Firestore - user_id: {user_id}, username: {username}, document_id: {user_id}"
            )
        
        return str(user_id)
    except Exception as e:
        logger.error(
            f"Error adding resume to Firestore: {str(e)}",
            exc_info=True
        )
        return None


async def add_user(data: dict) -> Optional[str]:
    """
    Asynchronously add a user to Firestore.
    
    Args:
        data: Dictionary containing user data
        
    Returns:
        The document ID of the new user entry, or None if error occurs
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, add_user_sync, data)


async def add_resume(resume: dict) -> Optional[str]:
    """
    Asynchronously add a resume to Firestore.
    
    Args:
        resume: Dictionary containing resume data
        
    Returns:
        The document ID of the new resume entry, or None if error occurs
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, add_resume_sync, resume)


def get_resume_sync(user_id: int) -> Optional[dict]:
    """
    Synchronously get a resume from Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        
    Returns:
        Dictionary containing resume data, or None if not found or error occurs
    """
    try:
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id value: {user_id} (must be positive integer)")
            return None
        
        db = get_firestore_client()
        doc_ref = db.collection("resumes").document(str(user_id))
        doc = doc_ref.get()
        
        if doc.exists:
            resume_data = doc.to_dict()
            logger.info(f"Resume retrieved from Firestore - user_id: {user_id}")
            return resume_data
        else:
            logger.debug(f"Resume not found in Firestore - user_id: {user_id}")
            return None
    except Exception as e:
        logger.error(
            f"Error getting resume from Firestore: {str(e)}",
            exc_info=True
        )
        return None


async def get_resume(user_id: int) -> Optional[dict]:
    """
    Asynchronously get a resume from Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        
    Returns:
        Dictionary containing resume data, or None if not found or error occurs
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_resume_sync, user_id)


def delete_resume_sync(user_id: int) -> bool:
    """
    Synchronously delete a resume from Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        
    Returns:
        True if resume was deleted successfully, False otherwise
    """
    try:
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id value: {user_id} (must be positive integer)")
            return False
        
        db = get_firestore_client()
        doc_ref = db.collection("resumes").document(str(user_id))
        doc = doc_ref.get()
        
        if doc.exists:
            doc_ref.delete()
            logger.info(f"Resume deleted from Firestore - user_id: {user_id}")
            return True
        else:
            logger.warning(f"Resume not found for deletion - user_id: {user_id}")
            return False
    except Exception as e:
        logger.error(
            f"Error deleting resume from Firestore: {str(e)}",
            exc_info=True
        )
        return False


async def delete_resume(user_id: int) -> bool:
    """
    Asynchronously delete a resume from Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        
    Returns:
        True if resume was deleted successfully, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, delete_resume_sync, user_id)


def update_resume_sync(user_id: int, updates: dict) -> bool:
    """
    Synchronously update a resume in Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        updates: Dictionary containing fields to update
        
    Returns:
        True if resume was updated successfully, False otherwise
    """
    try:
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id value: {user_id} (must be positive integer)")
            return False
        
        db = get_firestore_client()
        doc_ref = db.collection("resumes").document(str(user_id))
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"Resume not found for update - user_id: {user_id}")
            return False
        
        # Prepare updates with timestamp
        update_data = {
            **updates,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        
        # Ensure user_id and username are preserved if they exist in updates
        existing_data = doc.to_dict()
        if existing_data:
            if "user_id" in updates:
                update_data["user_id"] = existing_data.get("user_id")
            if "username" in updates:
                update_data["username"] = existing_data.get("username")
        
        doc_ref.update(update_data)
        logger.info(f"Resume updated in Firestore - user_id: {user_id}")
        return True
    except Exception as e:
        logger.error(
            f"Error updating resume in Firestore: {str(e)}",
            exc_info=True
        )
        return False


async def update_resume(user_id: int, updates: dict) -> bool:
    """
    Asynchronously update a resume in Firestore by user_id.
    
    Args:
        user_id: Telegram user ID (must be int)
        updates: Dictionary containing fields to update
        
    Returns:
        True if resume was updated successfully, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, update_resume_sync, user_id, updates)