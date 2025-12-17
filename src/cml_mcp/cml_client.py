# Copyright (c) 2025  Cisco Systems, Inc.
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
        host: str | None,
        username: str | None,
        password: str | None,
        transport: str = "stdio",
        verify_ssl: bool = False,
    ) -> None:
        if transport == "stdio":
            assert host is not None, "Host must be provided for stdio transport"
            assert username is not None, "Username must be provided for stdio transport"
            assert password is not None, "Password must be provided for stdio transport"
            self.base_url = host.rstrip("/")
            self.api_base = f"{self.base_url}/api/v0"
            self.vclient = virl2_client.ClientLibrary(host, username, password, ssl_verify=verify_ssl)
        else:
            self.base_url = ""
            self.api_base = ""
            self.vclient = None

        self.client = httpx.AsyncClient(verify=verify_ssl, timeout=API_TIMEOUT)
        self._token = None
        self.username = username
        self.password = password
        self.admin = None
        self.transport = transport
        self.verify_ssl = verify_ssl

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

    def update_client(self, host: str, username: str, password: str, verify_ssl: bool) -> None:
        """
        Update the client with new host, username, and password.
        Resets the token and admin status.
        """
        assert self.transport == "http", "update_client is only valid for HTTP transport"
        self.base_url = host.rstrip("/")
        self.api_base = f"{self.base_url}/api/v0"
        if verify_ssl != self.verify_ssl:
            self.client = httpx.AsyncClient(verify=verify_ssl, timeout=API_TIMEOUT)
            self.verify_ssl = verify_ssl
        self.vclient = virl2_client.ClientLibrary(host, username, password, ssl_verify=self.verify_ssl)
        self.username = username
        self.password = password
        self.token = None
        self.admin = None

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
            logger.info("Authenticated with CML API")
        except Exception as e:
            logger.exception(f"Failed to authenticate with CML API: {e}", exc_info=True)
            raise e

    async def check_authentication(self) -> None:
        """
        Check if the current session is authenticated.
        If not, re-authenticate.
        """
        # Token should always be None when HTTP transport is used.
        if self.token and self.transport == "stdio":
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
                    logger.error(f"Error checking authentication: {e}", exc_info=True)
                    raise e
            except httpx.RequestError as e:
                logger.error(f"Error checking authentication: {e}", exc_info=True)
                raise e

        # If token is None or authentication failed, re-authenticate
        if not self.token or self.transport == "http":
            logger.debug("[Re-]authenticating with CML API")
            await self.login()

    async def is_admin(self) -> bool:
        """
        Check if the current user is an admin.
        Returns True if the user is an admin, False otherwise.
        """
        if self.admin is not None and self.transport == "stdio":
            return self.admin

        if self.transport == "stdio":
            await self.check_authentication()
        try:
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{self.username}/id")
            resp.raise_for_status()
            user_id = resp.json()
            resp = await self.client.get(f"{self.base_url}/api/v0/users/{user_id}")
            resp.raise_for_status()
            self.admin = resp.json().get("admin", False)
            return self.admin
        except Exception as e:
            logger.error(f"Error checking admin status: {e}", exc_info=True)
            return False

    async def get(self, endpoint: str, params: dict | None = None) -> Any:
        """
        Make a GET request to the CML API.
        """
        if self.transport == "stdio":
            await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making GET request to {url}: {e}", exc_info=True)
            raise e

    async def post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> Any | None:
        """
        Make a POST request to the CML API.
        """
        if self.transport == "stdio":
            await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.post(url, json=data, params=params)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making POST request to {url}: {e}", exc_info=True)
            raise e

    async def put(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PUT request to the CML API.
        """
        if self.transport == "stdio":
            await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.put(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making PUT request to {url}: {e}", exc_info=True)
            raise e

    async def delete(self, endpoint: str) -> dict | None:
        """
        Make a DELETE request to the CML API.
        """
        if self.transport == "stdio":
            await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.delete(url)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making DELETE request to {url}: {e}", exc_info=True)
            raise e

    async def patch(self, endpoint: str, data: dict | None = None) -> Any | None:
        """
        Make a PATCH request to the CML API.
        """
        if self.transport == "stdio":
            await self.check_authentication()
        url = f"{self.api_base}{endpoint}"
        try:
            resp = await self.client.patch(url, json=data)
            resp.raise_for_status()
            if resp.status_code == 204:  # No content
                return None
            return resp.json()
        except httpx.RequestError as e:
            logger.error(f"Error making PATCH request to {url}: {e}", exc_info=True)
            raise e

    async def close(self) -> None:
        await self.client.aclose()
