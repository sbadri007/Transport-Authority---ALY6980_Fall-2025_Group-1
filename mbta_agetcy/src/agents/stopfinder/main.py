"""
MBTA Stop Finder Agent - Real API Integration
Searches for MBTA stops and stations using the real API
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import os
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("stopfinder-agent")

# Initialize FastAPI
app = FastAPI(title="mbta-stopfinder-agent", version="1.0.0")

# MBTA API Configuration
MBTA_API_KEY = os.getenv('MBTA_API_KEY')
MBTA_BASE_URL = "https://api-v3.mbta.com"

if not MBTA_API_KEY:
    log.warning("MBTA_API_KEY not found in environment variables!")

# Pydantic models
class A2AMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = {}


def find_stops(
    query: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = None
) -> Dict[str, Any]:
    """
    Find MBTA stops using the real API.
    
    Args:
        query: Search by stop name
        latitude: Search by location latitude
        longitude: Search by location longitude
        radius: Search radius in meters (default: 1000)
    
    Returns:
        Dictionary with stop information
    """
    try:
        # Build API request
        params = {
            "api_key": MBTA_API_KEY,
        }
        
        # Search by name
        if query:
            params["filter[name]"] = query
            log.info(f"Searching stops by name: '{query}'")
        
        # Search by location
        elif latitude is not None and longitude is not None:
            params["filter[latitude]"] = latitude
            params["filter[longitude]"] = longitude
            params["filter[radius]"] = radius or 0.01  # ~1km in degrees
            log.info(f"Searching stops near location: ({latitude}, {longitude})")
        
        else:
            # Get all stops (limited)
            log.info("Fetching all stops (limited to 100)")
            params["page[limit]"] = 100
        
        # Make API request
        response = requests.get(
            f"{MBTA_BASE_URL}/stops",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        stops = data.get("data", [])
        
        log.info(f"Found {len(stops)} stops")
        
        # No stops case
        if len(stops) == 0:
            search_text = f"matching '{query}'" if query else "in that area"
            return {
                "ok": True,
                "count": 0,
                "stops": [],
                "text": f"No MBTA stops found {search_text}. Try a different search term or location.",
                "query": query
            }
        
        # Process stops
        processed_stops = []
        
        for stop in stops[:20]:  # Limit to 20 results
            attributes = stop.get("attributes", {})
            
            stop_info = {
                "id": stop.get("id"),
                "name": attributes.get("name", "Unknown"),
                "description": attributes.get("description"),
                "latitude": attributes.get("latitude"),
                "longitude": attributes.get("longitude"),
                "wheelchair_accessible": attributes.get("wheelchair_boarding") == 1,
                "location_type": attributes.get("location_type"),
                "municipality": attributes.get("municipality"),
                "address": attributes.get("address")
            }
            
            processed_stops.append(stop_info)
        
        # Create response text
        if query:
            text = f"Found {len(stops)} stop(s) matching '{query}':\n\n"
        else:
            text = f"Found {len(stops)} nearby stops:\n\n"
        
        # List top 10 stops
        for i, stop in enumerate(processed_stops[:10]):
            name = stop["name"]
            municipality = stop.get("municipality", "")
            wheelchair = "♿" if stop.get("wheelchair_accessible") else ""
            
            stop_line = f"{i+1}. {name}"
            if municipality:
                stop_line += f" ({municipality})"
            if wheelchair:
                stop_line += f" {wheelchair}"
            
            text += stop_line + "\n"
        
        if len(stops) > 10:
            text += f"\n... and {len(stops) - 10} more stops"
        
        return {
            "ok": True,
            "count": len(stops),
            "stops": processed_stops,
            "text": text,
            "query": query
        }
    
    except requests.exceptions.RequestException as e:
        log.error(f"MBTA API request failed: {e}")
        return {
            "ok": False,
            "error": f"Failed to fetch stops from MBTA API: {str(e)}",
            "text": "Sorry, I couldn't retrieve stop information at this time. Please try again later."
        }
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return {
            "ok": False,
            "error": str(e),
            "text": "An unexpected error occurred while searching for stops."
        }


def get_stop_by_id(stop_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific stop.
    
    Args:
        stop_id: MBTA stop ID
    
    Returns:
        Dictionary with detailed stop information
    """
    try:
        params = {
            "api_key": MBTA_API_KEY,
            "include": "parent_station,facilities"
        }
        
        log.info(f"Fetching stop details for ID: {stop_id}")
        
        response = requests.get(
            f"{MBTA_BASE_URL}/stops/{stop_id}",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        stop = data.get("data", {})
        
        if not stop:
            return {
                "ok": False,
                "error": f"Stop not found: {stop_id}",
                "text": f"Could not find stop with ID {stop_id}"
            }
        
        attributes = stop.get("attributes", {})
        
        stop_info = {
            "id": stop.get("id"),
            "name": attributes.get("name", "Unknown"),
            "description": attributes.get("description"),
            "latitude": attributes.get("latitude"),
            "longitude": attributes.get("longitude"),
            "wheelchair_accessible": attributes.get("wheelchair_boarding") == 1,
            "platform_code": attributes.get("platform_code"),
            "platform_name": attributes.get("platform_name"),
            "municipality": attributes.get("municipality"),
            "address": attributes.get("address")
        }
        
        return {
            "ok": True,
            "stop": stop_info,
            "text": f"{stop_info['name']} - {stop_info.get('description', 'MBTA Stop')}"
        }
    
    except requests.exceptions.RequestException as e:
        log.error(f"MBTA API request failed: {e}")
        return {
            "ok": False,
            "error": str(e),
            "text": "Failed to fetch stop details"
        }


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "service": "mbta-stopfinder-agent",
        "version": "1.0.0",
        "mbta_api_configured": MBTA_API_KEY is not None
    }


@app.get("/stops")
def find_stops_endpoint(
    query: Optional[str] = Query(None, description="Search by stop name"),
    latitude: Optional[float] = Query(None, description="Search by latitude"),
    longitude: Optional[float] = Query(None, description="Search by longitude"),
    radius: Optional[float] = Query(None, description="Search radius in meters")
):
    """
    REST endpoint to find MBTA stops.
    
    Examples:
    - GET /stops?query=Harvard
    - GET /stops?query=Kendall
    - GET /stops?latitude=42.373362&longitude=-71.118956&radius=1000
    """
    try:
        result = find_stops(
            query=query,
            latitude=latitude,
            longitude=longitude,
            radius=radius
        )
        return result
    except Exception as e:
        log.error(f"Error in /stops endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stops/{stop_id}")
def get_stop_endpoint(stop_id: str):
    """
    REST endpoint to get a specific stop by ID.
    
    Example:
    - GET /stops/place-harsq (Harvard Square)
    """
    try:
        result = get_stop_by_id(stop_id)
        return result
    except Exception as e:
        log.error(f"Error in /stops/{stop_id} endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/a2a/message")
async def a2a_message(message: A2AMessage):
    """
    A2A protocol endpoint for agent-to-agent communication.
    
    Request format:
    {
        "type": "request",
        "payload": {
            "message": "Find stops near Harvard",
            "context": {"intent": "stop_info"}
        },
        "metadata": {}
    }
    
    Response format:
    {
        "type": "response",
        "payload": {
            "ok": true,
            "count": 5,
            "stops": [...],
            "text": "Found 5 stops..."
        },
        "metadata": {"status": "success", "agent": "stopfinder-agent"}
    }
    """
    log.info(f"Received A2A message: type={message.type}")
    
    try:
        if message.type == "request":
            payload = message.payload
            query = payload.get("message", "")
            context = payload.get("context", {})
            
            # Extract search query from message
            # Look for location names
            search_query = query
            
            # Remove common words
            for word in ["find", "stops", "near", "station", "stations", "at", "the"]:
                search_query = search_query.replace(word, "").strip()
            
            log.info(f"Processing query: '{query}' (search: {search_query})")
            
            # Find stops using MBTA API
            result = find_stops(query=search_query if search_query else None)
            
            # Return A2A response
            return {
                "type": "response",
                "payload": result,
                "metadata": {
                    "status": "success",
                    "agent": "mbta-stopfinder-agent",
                    "search_query": search_query,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        else:
            log.warning(f"Unsupported message type: {message.type}")
            return {
                "type": "error",
                "payload": {
                    "error": f"Unsupported message type: {message.type}",
                    "text": "This agent only supports 'request' messages."
                },
                "metadata": {"status": "error"}
            }
    
    except Exception as e:
        log.error(f"A2A error: {e}")
        return {
            "type": "error",
            "payload": {
                "error": str(e),
                "text": "An error occurred while processing your request."
            },
            "metadata": {"status": "error"}
        }


@app.post("/mcp/tools/list")
def mcp_tools_list():
    """
    MCP protocol: List available tools.
    """
    return {
        "tools": [
            {
                "name": "find_mbta_stops",
                "description": "Find MBTA stops and stations by name or location. Returns stop names, addresses, and accessibility information.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Stop name to search for (e.g., 'Harvard', 'Kendall', 'Park Street')"
                        }
                    }
                }
            },
            {
                "name": "get_mbta_stop",
                "description": "Get detailed information about a specific MBTA stop by its ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "stop_id": {
                            "type": "string",
                            "description": "MBTA stop ID (e.g., 'place-harsq' for Harvard Square)"
                        }
                    },
                    "required": ["stop_id"]
                }
            }
        ]
    }


@app.post("/mcp/tools/call")
def mcp_tools_call(request: Dict[str, Any]):
    """
    MCP protocol: Call a tool.
    """
    tool_name = request.get("name")
    arguments = request.get("arguments", {})
    
    if tool_name == "find_mbta_stops":
        query = arguments.get("query")
        result = find_stops(query=query)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.get("text", "No stops found")
                }
            ]
        }
    
    elif tool_name == "get_mbta_stop":
        stop_id = arguments.get("stop_id")
        result = get_stop_by_id(stop_id)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.get("text", "Stop not found")
                }
            ]
        }
    
    return {
        "error": f"Unknown tool: {tool_name}"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8003"))
    log.info(f"Starting MBTA StopFinder Agent on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)