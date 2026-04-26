# Copyright (c) 2025-2026  Cisco Systems, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import logging
import os
from typing import Any

import httpx
import virl2_client

API_TIMEOUT = 10  # seconds
MCP_CLIENT_IDENTIFIER = "CmlMCP"

# Set up logging for this module only
logger = logging.getLogger("cml-mcp.cml_client")
loglevel = logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO
logger.setLevel(loglevel)
# Configure handler with format for this module only
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


class CMLClient(object):
    """
    Async client for interacting with the CML API.
    Handles authentication and provides methods to fetch system and lab information.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        transport: str = "stdio",
        verify_ssl: bool = False,
    ) -> None:
        self.username = username
        self.password = password
        self.transport = transport
        self.verify_ssl = verify_ssl

        self._token = None
        self.admin = None
        self.needs_reauth = False

        self.base_url = host.rstrip("/")
        self.api_base = f"{self.base_url}/api/v0"
        self.vclient = virl2_client.ClientLibrary(host, username, password, ssl_verify=verify_ssl, client_type=MCP_CLIENT_IDENTIFIER)
        self.client = httpx.AsyncClient(verify=verify_ssl, timeout=API_TIMEOUT)
        self.client.headers.update({"X-CML-CLIENT": MCP_CLIENT_IDENTIFIER})

    @property
    def token(self) -> str | None:
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value
        if not value:
            self.client.headers.pop("Authorization", None)
        else:
            self.client.headers.update({"Authorization": f"Bearer {self._token}"})

    async def login(self) -> None:
        """
        Authenticate with the CML API and store the token for future requests.
        """
        url = f"{self.base_url}/api/v0/authenticate"
        try:
            resp = await self.client.post(
                url,
                json={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            self.token = resp.json()
            self.needs_reauth = False
            logger.info("Authenticated with CML API")
        except Exception as e:
            logger.exception("Failed to authenticate with CML API")
            self.needs_reauth = True
            raise e

    async def check_authentication(self) -> None:
        """
        Check if the current session is authenticated.
        If not, re-authenticate.
        """
        if self.token:
            url = f"{self.base_url}/api/v0/authok"
            try:
                resp = await self.client.get(url)
                resp.raise_for_status()
                return  # Already authenticated
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:  # Unauthorized, re-authenticate
                    logger.debug("Authentication failed, re-authenticating")
                    self.token = None
                else:
                    logger.exception("Error checking authentication")
                    raise e
            except httpx.RequestError as e:
                logger.exception("Error checking authentication")
                raise e

        # If token is None or authentication failed, re-authenticate
        if not self.token:
            logger.debug("[Re-]authenticating with CML API")
            await self.login()

    async def is_admin(self) -> bool:
        """
        Check if the current user is an admin.
        Returns True if the user is an admin, False otherwise.
        """
        if self.admin is not None:
            return self.admin

        await self.check_authentication()
        try:
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{self.username}/id")
            resp.raise_for_status()
            user_id = resp.json()
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{user_id}")
            resp.raise_for_status()
            self.admin = resp.json().get("admin", False)
            return self.admin
        except Exception:
            logger.exception("Error checking admin status")
            return False

    async def get(self, endpoint: str, params: dict | None = None, is_binary: bool = False) -> Any:
        """
        Make a GET request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            return resp.json() if not is_binary else resp.content
        except httpx.RequestError as e:
            logger.exception("Error making GET request to %s", url)
            raise e

    async def post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> Any | None:
        """
        Make a POST request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.post(url, json=data, params=params)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.exception("Error making POST request to %s", url)
            raise e

    async def put(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PUT request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.put(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.exception("Error making PUT request to %s", url)
            raise e

    async def delete(self, endpoint: str) -> dict | None:
        """
        Make a DELETE request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.delete(url)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.exception("Error making DELETE request to %s", url)
            raise e

    async def patch(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PATCH request to the CML API.
        """
        await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.patch(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.exception("Error making PATCH request to %s", url)
            raise e

    async def close(self) -> None:
        """Close the HTTP client and clean up all resources."""
        try:
            # Close the httpx async client which should clean up connection pools and semaphores
            await self.client.aclose()
            logger.debug("HTTP client closed successfully")
        except Exception:
            logger.exception("Error closing HTTP client")
