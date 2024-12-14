import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PastebinHandler:
    def __init__(self):
        self.api_key = os.getenv('PASTEBIN_API_KEY')
        self.base_url = "https://pastebin.com/api"
        
        if not self.api_key:
            logger.warning("PASTEBIN_API_KEY not found in environment variables")
    
    def create_paste(self, content, title=None, expiration='1M', private=1):
        """
        Create a new paste on Pastebin
        
        Args:
            content (str): The text content to paste
            title (str, optional): Title of the paste
            expiration (str): Expiration time ('N'=never, '10M'=10min, '1H'=1hour, '1D'=1day, '1M'=1month)
            private (int): Privacy level (0=public, 1=unlisted, 2=private)
        
        Returns:
            str: URL of the created paste or None if failed
        """
        try:
            if not self.api_key:
                logger.error("No Pastebin API key configured")
                return None

            data = {
                'api_dev_key': self.api_key,
                'api_option': 'paste',
                'api_paste_code': content,
                'api_paste_private': private,
                'api_paste_name': title or f'Decrypted_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'api_paste_expire_date': expiration
            }
            
            response = requests.post(f"{self.base_url}/api_post.php", data=data, timeout=10)
            
            if 'Bad API request' in response.text:
                logger.error(f"Pastebin API Error: {response.text}")
                return None
            
            if not response.text.startswith('https://pastebin.com/'):
                logger.error(f"Unexpected Pastebin response: {response.text}")
                return None
                
            return response.text.strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error creating paste: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating paste: {str(e)}")
            return None
    
    def delete_paste(self, paste_key):
        """
        Delete a paste (requires PRO account)
        
        Args:
            paste_key (str): The paste key (last part of the paste URL)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = {
                'api_dev_key': self.api_key,
                'api_option': 'delete',
                'api_paste_key': paste_key
            }
            
            response = requests.post(f"{self.base_url}/api_post.php", data=data, timeout=10)
            return 'Paste Removed' in response.text
            
        except Exception as e:
            logger.error(f"Error deleting paste: {str(e)}")
            return False

# Initialize the handler
pastebin_handler = PastebinHandler()