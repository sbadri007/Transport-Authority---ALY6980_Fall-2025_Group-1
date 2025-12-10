"""
MBTA Route Planner Agent - Real API Integration
Plans routes between stops using real MBTA data
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
log = logging.getLogger("planner-agent")

# Initialize FastAPI
app = FastAPI(title="mbta-planner-agent", version="1.0.0")

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


def find_stop_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Find a stop by name using MBTA API.
    
    Args:
        name: Stop name to search for
    
    Returns:
        Stop information or None if not found
    """
    try:
        params = {
            "api_key": MBTA_API_KEY,
            "filter[name]": name
        }
        
        response = requests.get(
            f"{MBTA_BASE_URL}/stops",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        stops = data.get("data", [])
        
        if stops:
            stop = stops[0]  # Take first match
            attributes = stop.get("attributes", {})
            
            return {
                "id": stop.get("id"),
                "name": attributes.get("name"),
                "latitude": attributes.get("latitude"),
                "longitude": attributes.get("longitude")
            }
        
        return None
    
    except Exception as e:
        log.error(f"Error finding stop '{name}': {e}")
        return None


def get_routes_between_stops(origin_id: str, destination_id: str) -> List[Dict[str, Any]]:
    """
    Find routes that serve both origin and destination stops.
    
    Args:
        origin_id: Origin stop ID
        destination_id: Destination stop ID
    
    Returns:
        List of routes that connect the stops
    """
    try:
        # Get routes serving origin stop
        params = {
            "api_key": MBTA_API_KEY,
            "filter[stop]": origin_id
        }
        
        response = requests.get(
            f"{MBTA_BASE_URL}/routes",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        origin_routes = response.json().get("data", [])
        origin_route_ids = {route.get("id") for route in origin_routes}
        
        # Get routes serving destination stop
        params["filter[stop]"] = destination_id
        
        response = requests.get(
            f"{MBTA_BASE_URL}/routes",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        dest_routes = response.json().get("data", [])
        dest_route_ids = {route.get("id") for route in dest_routes}
        
        # Find common routes
        common_route_ids = origin_route_ids.intersection(dest_route_ids)
        
        # Get details of common routes
        common_routes = []
        for route in origin_routes:
            if route.get("id") in common_route_ids:
                attributes = route.get("attributes", {})
                common_routes.append({
                    "id": route.get("id"),
                    "name": attributes.get("long_name", attributes.get("short_name", "Unknown")),
                    "type": attributes.get("type"),
                    "color": attributes.get("color"),
                    "text_color": attributes.get("text_color"),
                    "description": attributes.get("description")
                })
        
        return common_routes
    
    except Exception as e:
        log.error(f"Error finding routes: {e}")
        return []


def plan_route(origin: str, destination: str) -> Dict[str, Any]:
    """
    Plan a route between two locations using real MBTA data.
    
    Note: MBTA API doesn't provide direct trip planning with transfers.
    This is a simplified version that finds direct routes.
    
    Args:
        origin: Origin stop name
        destination: Destination stop name
    
    Returns:
        Dictionary with route information
    """
    try:
        log.info(f"Planning route from '{origin}' to '{destination}'")
        
        # Step 1: Find origin stop
        origin_stop = find_stop_by_name(origin)
        if not origin_stop:
            return {
                "ok": False,
                "error": f"Could not find origin stop: {origin}",
                "text": f"Sorry, I couldn't find a stop matching '{origin}'. Please check the name and try again."
            }
        
        # Step 2: Find destination stop
        dest_stop = find_stop_by_name(destination)
        if not dest_stop:
            return {
                "ok": False,
                "error": f"Could not find destination stop: {destination}",
                "text": f"Sorry, I couldn't find a stop matching '{destination}'. Please check the name and try again."
            }
        
        log.info(f"Found stops - Origin: {origin_stop['name']}, Destination: {dest_stop['name']}")
        
        # Step 3: Find routes connecting the stops
        routes = get_routes_between_stops(origin_stop["id"], dest_stop["id"])
        
        if not routes:
            return {
                "ok": True,
                "origin": origin_stop,
                "destination": dest_stop,
                "routes": [],
                "text": f"No direct routes found between {origin_stop['name']} and {dest_stop['name']}. You may need to transfer between lines."
            }
        
        # Step 4: Format response
        route_names = [route["name"] for route in routes]
        
        if len(routes) == 1:
            route = routes[0]
            text = f"Take the {route['name']} from {origin_stop['name']} to {dest_stop['name']}."
        else:
            text = f"Multiple options available from {origin_stop['name']} to {dest_stop['name']}:\n"
            for i, route in enumerate(routes, 1):
                text += f"\n{i}. {route['name']}"
        
        return {
            "ok": True,
            "origin": origin_stop,
            "destination": dest_stop,
            "routes": routes,
            "text": text,
            "summary": f"{len(routes)} route(s) available"
        }
    
    except requests.exceptions.RequestException as e:
        log.error(f"MBTA API request failed: {e}")
        return {
            "ok": False,
            "error": f"Failed to plan route: {str(e)}",
            "text": "Sorry, I couldn't plan your route at this time. Please try again later."
        }
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return {
            "ok": False,
            "error": str(e),
            "text": "An unexpected error occurred while planning your route."
        }


def get_predictions(stop_id: str, route_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get real-time arrival predictions for a stop.
    
    Args:
        stop_id: Stop ID
        route_id: Optional route filter
    
    Returns:
        Dictionary with prediction information
    """
    try:
        params = {
            "api_key": MBTA_API_KEY,
            "filter[stop]": stop_id,
            "sort": "arrival_time"
        }
        
        if route_id:
            params["filter[route]"] = route_id
        
        response = requests.get(
            f"{MBTA_BASE_URL}/predictions",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        predictions = data.get("data", [])
        
        if not predictions:
            return {
                "ok": True,
                "count": 0,
                "predictions": [],
                "text": "No upcoming arrivals at this time."
            }
        
        # Process predictions
        processed = []
        for pred in predictions[:5]:  # Top 5
            attributes = pred.get("attributes", {})
            
            arrival_time = attributes.get("arrival_time")
            departure_time = attributes.get("departure_time")
            direction_id = attributes.get("direction_id")
            
            processed.append({
                "arrival_time": arrival_time,
                "departure_time": departure_time,
                "direction_id": direction_id,
                "status": attributes.get("status")
            })
        
        return {
            "ok": True,
            "count": len(predictions),
            "predictions": processed
        }
    
    except Exception as e:
        log.error(f"Error fetching predictions: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "service": "mbta-planner-agent",
        "version": "1.0.0",
        "mbta_api_configured": MBTA_API_KEY is not None
    }


@app.get("/plan")
def plan_route_endpoint(
    origin: str = Query(..., description="Origin stop name"),
    destination: str = Query(..., description="Destination stop name")
):
    """
    REST endpoint to plan a route.
    
    Examples:
    - GET /plan?origin=Harvard&destination=MIT
    - GET /plan?origin=Park%20Street&destination=Downtown%20Crossing
    """
    try:
        result = plan_route(origin=origin, destination=destination)
        return result
    except Exception as e:
        log.error(f"Error in /plan endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/a2a/message")
async def a2a_message(message: A2AMessage):
    """
    A2A protocol endpoint for agent-to-agent communication.
    
    Request format:
    {
        "type": "request",
        "payload": {
            "message": "How do I get from Harvard to MIT?",
            "context": {"intent": "trip_planning"}
        },
        "metadata": {}
    }
    
    Response format:
    {
        "type": "response",
        "payload": {
            "ok": true,
            "origin": {...},
            "destination": {...},
            "routes": [...],
            "text": "Take the Red Line..."
        },
        "metadata": {"status": "success", "agent": "planner-agent"}
    }
    """
    log.info(f"Received A2A message: type={message.type}")
    
    try:
        if message.type == "request":
            payload = message.payload
            query = payload.get("message", "")
            context = payload.get("context", {})
            
            # Parse origin and destination from query
            # Look for "from X to Y" pattern
            query_lower = query.lower()
            
            origin = None
            destination = None
            
            # Try to extract locations
            if "from" in query_lower and "to" in query_lower:
                parts = query_lower.split("from")[1].split("to")
                if len(parts) >= 2:
                    origin = parts[0].strip()
                    destination = parts[1].strip()
                    
                    # Clean up common words
                    for word in ["get", "go", "travel", "the", "station", "?"]:
                        origin = origin.replace(word, "").strip()
                        destination = destination.replace(word, "").strip()
            
            # Fallback: try "origin to destination" pattern
            elif "to" in query_lower:
                parts = query_lower.split("to")
                if len(parts) >= 2:
                    origin = parts[0].strip()
                    destination = parts[1].strip()
                    
                    # Clean up
                    for word in ["how", "do", "i", "get", "from", "the", "?"]:
                        origin = origin.replace(word, "").strip()
                        destination = destination.replace(word, "").strip()
            
            # Default values if parsing failed
            if not origin:
                origin = "Harvard"
            if not destination:
                destination = "MIT"
            
            log.info(f"Processing query: '{query}' (origin: {origin}, dest: {destination})")
            
            # Plan route using MBTA API
            result = plan_route(origin=origin, destination=destination)
            
            # Return A2A response
            return {
                "type": "response",
                "payload": result,
                "metadata": {
                    "status": "success",
                    "agent": "mbta-planner-agent",
                    "origin_parsed": origin,
                    "destination_parsed": destination,
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
                "name": "plan_mbta_trip",
                "description": "Plan a trip between two MBTA stops. Returns available routes and directions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin stop name (e.g., 'Harvard', 'Park Street')"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination stop name (e.g., 'MIT', 'Downtown Crossing')"
                        }
                    },
                    "required": ["origin", "destination"]
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
    
    if tool_name == "plan_mbta_trip":
        origin = arguments.get("origin")
        destination = arguments.get("destination")
        result = plan_route(origin=origin, destination=destination)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.get("text", "Could not plan route")
                }
            ]
        }
    
    return {
        "error": f"Unknown tool: {tool_name}"
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8002"))
    log.info(f"Starting MBTA Planner Agent on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)