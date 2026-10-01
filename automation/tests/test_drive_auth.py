import os
import unittest

from modules.drive_auth import DriveAuthError, user_oauth_credentials_from_info


class DriveAuthTest(unittest.TestCase):
    def test_user_oauth_credentials_from_refresh_token(self):
        creds=user_oauth_credentials_from_info({
            "client_id":"client.apps.googleusercontent.com",
            "client_secret":"secret",
            "refresh_token":"refresh-token",
            "token_uri":"https://oauth2.googleapis.com/token",
        })
        self.assertEqual(creds.client_id,"client.apps.googleusercontent.com")
        self.assertEqual(creds.client_secret,"secret")
        self.assertEqual(creds.refresh_token,"refresh-token")
        self.assertEqual(creds.token_uri,"https://oauth2.googleapis.com/token")

    def test_missing_refresh_token_is_rejected(self):
        with self.assertRaises(DriveAuthError):
            user_oauth_credentials_from_info({
                "client_id":"client.apps.googleusercontent.com",
                "client_secret":"secret",
            })


if __name__=="__main__":
    unittest.main()
