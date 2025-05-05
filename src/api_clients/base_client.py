from typing import Any, Dict, Optional
import httpx
from urllib.parse import quote
import asyncio
from httpx import TimeoutException

class BaseAPIClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 120.0, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = self._create_client()
        self.async_client = self._create_async_client()

    def _create_client(self) -> httpx.Client:
        """Create an HTTP client with timeout"""
        return httpx.Client(
            timeout=httpx.Timeout(
                connect=self.timeout,
                read=self.timeout, 
                write=self.timeout,
                pool=self.timeout
            ),
            follow_redirects=True,
        )

    def _create_async_client(self) -> httpx.AsyncClient:
        """Create an async HTTP client with timeout"""
        return httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=self.timeout,
                read=self.timeout, 
                write=self.timeout,
                pool=self.timeout
            ),
            follow_redirects=True,
        )

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers with API key if available"""
        headers = {"accept": "*/*"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        if additional_headers:
            headers.update(additional_headers)
        return headers

    async def _make_request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make async HTTP request with error handling and retries"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(headers)
        
        retries = 0
        while retries < self.max_retries:
            try:
                # Verify timeout settings before making request
                current_timeout = self.async_client.timeout
                print(f"Making request with timeout settings: connect={current_timeout.connect}s, read={current_timeout.read}s")
                
                response = await self.async_client.request(
                    method, url, params=params, headers=headers, json=json
                )
                response.raise_for_status()
                return response
            except TimeoutException:
                retries += 1
                if retries == self.max_retries:
                    raise Exception(f"Request timed out after {self.max_retries} retries")
                await asyncio.sleep(2 ** retries)  # Exponential backoff
            except httpx.HTTPStatusError as e:
                content = e.response.text
                raise Exception(f"API request failed [{e.response.status_code}]: {content}")
            except httpx.HTTPError as e:
                raise Exception(f"Unexpected HTTP error: {str(e)}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request with error handling and retries"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(headers)

        retries = 0
        while retries < self.max_retries:
            try:
                response = self.client.request(method, url, params=params, headers=headers, json=json)
                response.raise_for_status()
                return response
            except TimeoutException:
                retries += 1
                if retries == self.max_retries:
                    raise Exception(f"Request timed out after {self.max_retries} retries")
                asyncio.sleep(2 ** retries)  # Exponential backoff
            except httpx.HTTPStatusError as e:
                content = e.response.text
                raise Exception(f"API request failed [{e.response.status_code}]: {content}")
            except httpx.HTTPError as e:
                raise Exception(f"Unexpected HTTP error: {str(e)}")

    async def get_async(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make async GET request and return JSON response"""
        response = await self._make_request_async("GET", endpoint, params=params, headers=headers)
        return response.json()

    async def post_async(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make async POST request and return JSON response"""
        response = await self._make_request_async("POST", endpoint, params=params, json=json, headers=headers)
        return response.json()

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make GET request and return JSON response"""
        response = self._make_request("GET", endpoint, params=params, headers=headers)
        return response.json()

    def post(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make POST request and return JSON response"""
        response = self._make_request("POST", endpoint, params=params, json=json, headers=headers)
        return response.json()

    def encode_url_component(self, value: str) -> str:
        """Safely encode URL components"""
        return quote(value, safe='')
    
    def post_with_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make POST request and return JSON response using requests library"""
        url = f"{self.base_url}/{endpoint}"
        
        # Prepare headers
        request_headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }
        if headers:
            request_headers.update(headers)
            
        # Make request
        response = requests.post(
            url,
            params=params,
            json=json,
            headers=request_headers,
            timeout=self.timeout
        )
        
        return response.json()
