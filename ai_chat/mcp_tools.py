# import logging
# from typing import Any, Dict, List, Optional
# from urllib.parse import quote_plus

# import httpx


# logger = logging.getLogger(__name__)


# class MCPTool:
#     """MCP Tool definition"""

#     def __init__(
#         self, name: str, description: str, parameters: Dict[str, Any], handler: callable
#     ):
#         self.name = name
#         self.description = description
#         self.parameters = parameters
#         self.handler = handler


# class DjangoMCPServer:
#     """Django-based MCP Server with direct database access"""

#     def __init__(self):
#         self.tools: Dict[str, MCPTool] = {}
#         self._register_tools()

#     def _register_tools(self):
#         """Register all available MCP tools"""

#         # Web search tool
#         self.register_tool(
#             name="web_search",
#             description="Search the web for information using DuckDuckGo",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "query": {"type": "string", "description": "Search query"},
#                     "max_results": {
#                         "type": "integer",
#                         "description": "Maximum number of results (default: 5)",
#                         "default": 5,
#                     },
#                 },
#                 "required": ["query"],
#             },
#             handler=self._web_search_handler,
#         )

#         # Calculator tool
#         self.register_tool(
#             name="calculate",
#             description="Perform mathematical calculations",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "expression": {
#                         "type": "string",
#                         "description": "Mathematical expression to evaluate",
#                     }
#                 },
#                 "required": ["expression"],
#             },
#             handler=self._calculate_handler,
#         )

#         # GEOSPATIAL ANALYSIS TOOLS (with direct Django database access)

#         # List available layers
#         self.register_tool(
#             name="list_layers",
#             description="List all available geospatial layers with their names and IDs",
#             parameters={"type": "object", "properties": {}},
#             handler=self._list_layers_handler,
#         )

#         # Find layer by name
#         self.register_tool(
#             name="find_layer_by_name",
#             description="Find a layer by its name and get basic information",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "layer_name": {
#                         "type": "string",
#                         "description": (
#                             "Name of the layer to find (case-insensitive partial match)"
#                         ),
#                     }
#                 },
#                 "required": ["layer_name"],
#             },
#             handler=self._find_layer_by_name_handler,
#         )

#         # Get layer information
#         self.register_tool(
#             name="get_layer_info",
#             description="Get detailed information about a specific layer",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "layer_id": {
#                         "type": "integer",
#                         "description": "ID of the layer to analyze",
#                     },
#                     "layer_name": {
#                         "type": "string",
#                         "description": (
#                             "Name of the layer to analyze (alternative to layer_id)"
#                         ),
#                     },
#                 },
#             },
#             handler=self._get_layer_info_handler,
#         )

#         # Analyze population data
#         self.register_tool(
#             name="analyze_population",
#             description="Analyze population data in a layer and highlight features based on population thresholds",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "layer_id": {
#                         "type": "integer",
#                         "description": "ID of the layer containing population data",
#                     },
#                     "layer_name": {
#                         "type": "string",
#                         "description": (
#                             "Name of the layer containing population data (alternative to layer_id)"
#                         ),
#                     },
#                     "population_field": {
#                         "type": "string",
#                         "description": (
#                             "Name of the field containing population data (e.g., 'population', 'pop_est')"
#                         ),
#                     },
#                     "threshold": {
#                         "type": "number",
#                         "description": (
#                             "Population threshold for highlighting (optional)"
#                         ),
#                     },
#                     "operation": {
#                         "type": "string",
#                         "enum": ["greater_than", "less_than", "between", "top_n"],
#                         "description": "Type of analysis operation",
#                         "default": "greater_than",
#                     },
#                 },
#                 "required": ["population_field"],
#             },
#             handler=self._analyze_population_handler,
#         )

#         # Get attribute statistics
#         self.register_tool(
#             name="get_attribute_stats",
#             description="Get statistical analysis of a specific attribute in a layer",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "layer_id": {"type": "integer", "description": "ID of the layer"},
#                     "layer_name": {
#                         "type": "string",
#                         "description": "Name of the layer (alternative to layer_id)",
#                     },
#                     "attribute_key": {
#                         "type": "string",
#                         "description": "Name of the attribute to analyze",
#                     },
#                 },
#                 "required": ["attribute_key"],
#             },
#             handler=self._get_attribute_stats_handler,
#         )

#         # Comprehensive layer analysis
#         self.register_tool(
#             name="analyze_layer_attributes",
#             description="Perform comprehensive attribute analysis on a layer including statistics, data types, and insights",
#             parameters={
#                 "type": "object",
#                 "properties": {
#                     "layer_id": {
#                         "type": "integer",
#                         "description": "ID of the layer to analyze",
#                     },
#                     "layer_name": {
#                         "type": "string",
#                         "description": (
#                             "Name of the layer to analyze (alternative to layer_id)"
#                         ),
#                     },
#                     "include_statistics": {
#                         "type": "boolean",
#                         "description": (
#                             "Include detailed statistics for numeric attributes"
#                         ),
#                         "default": True,
#                     },
#                 },
#             },
#             handler=self._analyze_layer_attributes_handler,
#         )

#     def register_tool(
#         self, name: str, description: str, parameters: Dict[str, Any], handler: callable
#     ):
#         """Register a new MCP tool"""
#         self.tools[name] = MCPTool(
#             name=name, description=description, parameters=parameters, handler=handler
#         )
#         # logger.info(f"Registered MCP tool: {name}")

#     async def execute_tool(
#         self, tool_name: str, arguments: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """Execute an MCP tool"""
#         if tool_name not in self.tools:
#             return {"success": False, "error": f"Unknown tool: {tool_name}"}

#         try:
#             handler = self.tools[tool_name].handler
#             result = await handler(arguments)
#             return {"success": True, "result": result}
#         except Exception as e:
#             logger.error(f"Error executing tool {tool_name}: {str(e)}")
#             return {"success": False, "error": str(e)}

#     def get_tools_schema(self) -> List[Dict[str, Any]]:
#         """Get OpenAI-compatible tools schema"""
#         return [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": tool.name,
#                     "description": tool.description,
#                     "parameters": tool.parameters,
#                 },
#             }
#             for tool in self.tools.values()
#         ]

#     # TOOL HANDLERS

#     def _resolve_layer_id(
#         self, layer_id: Optional[int] = None, layer_name: Optional[str] = None
#     ) -> Optional[int]:
#         """Resolve layer name to ID, or return provided ID - using direct Django ORM"""
#         if layer_id:
#             return layer_id

#         if not layer_name:
#             return None

#         try:
#             layer = Layer.objects.filter(name__icontains=layer_name).first()
#             return layer.id if layer else None
#         except Exception as e:
#             logger.error(f"Error resolving layer name: {str(e)}")
#             return None

#     async def _list_layers_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for listing all available layers - using direct Django ORM"""
#         try:
#             layers = Layer.objects.all().order_by("-created_at")

#             if layers.exists():
#                 result = "Available Geospatial Layers:\n"
#                 for layer in layers:
#                     feature_count = Feature.objects.filter(layer=layer).count()
#                     result += f"- ID: {layer.id}, Name: {layer.name}\n"
#                     result += (
#                         f"  Description: {layer.description or 'No description'}\n"
#                     )
#                     result += f"  Features: {feature_count} features\n"
#                     result += f"  Created: {layer.created_at}\n\n"
#                 return result
#             else:
#                 return "No geospatial layers found. Upload a shapefile to get started."

#         except Exception as e:
#             logger.error(f"Error listing layers: {str(e)}")
#             return f"Error listing layers: {str(e)}"

#     async def _find_layer_by_name_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for finding a layer by name - using direct Django ORM"""
#         layer_name = args.get("layer_name")

#         try:
#             layers = Layer.objects.filter(name__icontains=layer_name)

#             if not layers.exists():
#                 return f"No layers found matching '{layer_name}'"

#             result = f"Found {layers.count()} layer(s) matching '{layer_name}':\n\n"
#             for layer in layers:
#                 feature_count = Feature.objects.filter(layer=layer).count()
#                 result += f"- ID: {layer.id}, Name: {layer.name}\n"
#                 result += f"  Description: {layer.description or 'No description'}\n"
#                 result += f"  Features: {feature_count} features\n"
#                 result += f"  Created: {layer.created_at}\n\n"

#             return result

#         except Exception as e:
#             logger.error(f"Error finding layer by name: {str(e)}")
#             return f"Error finding layer by name: {str(e)}"

#     async def _get_layer_info_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for getting detailed layer information - using direct Django ORM"""
#         layer_id = self._resolve_layer_id(args.get("layer_id"), args.get("layer_name"))

#         if not layer_id:
#             return "Please provide either a layer_id or layer_name"

#         try:
#             layer = Layer.objects.get(id=layer_id)
#             feature_count = Feature.objects.filter(layer=layer).count()

#             result = "Layer Information:\n"
#             result += f"ID: {layer.id}\n"
#             result += f"Name: {layer.name}\n"
#             result += f"Description: {layer.description or 'No description'}\n"
#             result += f"Created: {layer.created_at}\n"
#             result += f"Features: {feature_count}\n\n"

#             # Get attribute summary
#             try:
#                 summary = AttributeManager.get_layer_attribute_summary(layer)
#                 if summary:
#                     result += "Available Attributes:\n"
#                     for attr_name, attr_info in summary.items():
#                         result += (
#                             f"- {attr_name}: {attr_info.get('data_type', 'unknown')} "
#                         )
#                         result += f"({attr_info.get('count', 0)} values)\n"
#                         if attr_info.get("sample_values"):
#                             result += f"  Sample values: {', '.join(map(str, attr_info['sample_values'][:3]))}\n"
#             except Exception as e:
#                 result += f"Could not retrieve attribute information: {str(e)}\n"

#             return result

#         except Layer.DoesNotExist:
#             return f"Layer {layer_id} not found"
#         except Exception as e:
#             logger.error(f"Error getting layer info: {str(e)}")
#             return f"Error getting layer info: {str(e)}"

#     async def _analyze_population_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for population analysis - using direct Django ORM"""
#         layer_id = self._resolve_layer_id(args.get("layer_id"), args.get("layer_name"))

#         if not layer_id:
#             return "Please provide either a layer_id or layer_name"

#         population_field = args.get("population_field")
#         threshold = args.get("threshold")
#         operation = args.get("operation", "greater_than")

#         try:
#             layer = Layer.objects.get(id=layer_id)

#             # Get features with the population field
#             features_with_pop = Feature.objects.filter(
#                 layer=layer, attributes__key=population_field
#             ).prefetch_related("attributes")

#             if not features_with_pop.exists():
#                 return f"Population field '{population_field}' not found in layer {layer_id}"

#             # Build result
#             result = "Population Analysis Results:\n"
#             result += f"Layer: {layer.name}\n"
#             result += f"Field analyzed: {population_field}\n"
#             result += f"Operation: {operation}\n"

#             # Get population values for analysis
#             pop_values = []
#             feature_data = []

#             for feature in features_with_pop:
#                 for attr in feature.attributes.all():
#                     if attr.key == population_field:
#                         try:
#                             pop_value = float(attr.value)
#                             pop_values.append(pop_value)

#                             # Get feature name if available
#                             name = "Unknown"
#                             for name_attr in feature.attributes.all():
#                                 if name_attr.key.lower() in [
#                                     "name",
#                                     "country",
#                                     "admin",
#                                     "name_en",
#                                 ]:
#                                     name = name_attr.value
#                                     break

#                             feature_data.append(
#                                 {
#                                     "name": name,
#                                     "population": pop_value,
#                                     "feature_id": feature.id,
#                                 }
#                             )
#                         except (ValueError, TypeError):
#                             continue

#             if pop_values:
#                 result += "Population Statistics:\n"
#                 result += f"- Min: {min(pop_values):,.0f}\n"
#                 result += f"- Max: {max(pop_values):,.0f}\n"
#                 result += f"- Average: {sum(pop_values)/len(pop_values):,.0f}\n"
#                 result += f"- Total features: {len(pop_values)}\n\n"

#                 # Filter based on operation
#                 filtered_features = []
#                 if operation == "greater_than" and threshold is not None:
#                     filtered_features = [
#                         f for f in feature_data if f["population"] > threshold
#                     ]
#                 elif operation == "less_than" and threshold is not None:
#                     filtered_features = [
#                         f for f in feature_data if f["population"] < threshold
#                     ]
#                 elif operation == "top_n":
#                     n = args.get("n", 10)
#                     filtered_features = sorted(
#                         feature_data, key=lambda x: x["population"], reverse=True
#                     )[:n]

#                 result += f"Features matching criteria: {len(filtered_features)}\n\n"

#                 if filtered_features:
#                     result += "Matching Features:\n"
#                     for feature in filtered_features[:10]:  # Show first 10
#                         result += f"- {feature['name']}: {feature['population']:,.0f}\n"

#                     if len(filtered_features) > 10:
#                         result += (
#                             f"... and {len(filtered_features) - 10} more features\n"
#                         )

#             return result

#         except Layer.DoesNotExist:
#             return f"Layer {layer_id} not found"
#         except Exception as e:
#             logger.error(f"Error in population analysis: {str(e)}")
#             return f"Error in population analysis: {str(e)}"

#     async def _get_attribute_stats_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for getting attribute statistics - using direct Django ORM"""
#         layer_id = self._resolve_layer_id(args.get("layer_id"), args.get("layer_name"))

#         if not layer_id:
#             return "Please provide either a layer_id or layer_name"

#         attribute_key = args.get("attribute_key")

#         try:
#             layer = Layer.objects.get(id=layer_id)

#             # Get all attribute values for this key
#             attributes = FeatureAttribute.objects.filter(
#                 feature__layer=layer, key=attribute_key
#             )

#             if not attributes.exists():
#                 return f"Attribute '{attribute_key}' not found in layer {layer_id}"

#             values = [attr.value for attr in attributes]

#             result = f"Attribute Statistics for '{attribute_key}':\n"
#             result += f"Layer: {layer.name}\n"
#             result += f"Total values: {len(values)}\n"

#             # Try to determine if values are numeric
#             numeric_values = []
#             for value in values:
#                 try:
#                     numeric_values.append(float(value))
#                 except (ValueError, TypeError):
#                     pass

#             if numeric_values:
#                 result += "Data type: numeric\n"
#                 result += f"Minimum: {min(numeric_values):,.2f}\n"
#                 result += f"Maximum: {max(numeric_values):,.2f}\n"
#                 result += f"Average: {sum(numeric_values)/len(numeric_values):,.2f}\n"
#                 result += f"Sum: {sum(numeric_values):,.2f}\n"
#             else:
#                 result += "Data type: text/categorical\n"

#             # Show unique values (limited)
#             unique_values = list(set(values))
#             result += f"Unique values: {len(unique_values)}\n"
#             result += f"Sample values: {', '.join(map(str, unique_values[:10]))}\n"

#             return result

#         except Layer.DoesNotExist:
#             return f"Layer {layer_id} not found"
#         except Exception as e:
#             logger.error(f"Error getting attribute stats: {str(e)}")
#             return f"Error getting attribute stats: {str(e)}"

#     async def _analyze_layer_attributes_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for comprehensive layer attribute analysis - using direct Django ORM"""
#         layer_id = self._resolve_layer_id(args.get("layer_id"), args.get("layer_name"))

#         if not layer_id:
#             # If no layer specified, list available layers
#             return await self._list_layers_handler({})

#         try:
#             layer = Layer.objects.get(id=layer_id)
#             feature_count = Feature.objects.filter(layer=layer).count()

#             result = "📊 COMPREHENSIVE LAYER ANALYSIS\n"
#             result += f"{'='*50}\n\n"

#             result += "🗺️  LAYER INFORMATION:\n"
#             result += f"   Name: {layer.name}\n"
#             result += f"   ID: {layer.id}\n"
#             result += f"   Description: {layer.description or 'No description'}\n"
#             result += f"   Geometry Type: {layer.geometry_type or 'Unknown'}\n"
#             result += f"   Features: {feature_count}\n"
#             result += f"   Created: {layer.created_at}\n\n"

#             # Get attribute summary using Django ORM
#             try:
#                 summary = AttributeManager.get_layer_attribute_summary(layer)

#                 if summary:
#                     result += "📋 ATTRIBUTE ANALYSIS:\n"
#                     result += f"   Total Attributes: {len(summary)}\n\n"

#                     # Categorize attributes by type
#                     numeric_attrs = []
#                     text_attrs = []
#                     date_attrs = []

#                     for attr_name, attr_info in summary.items():
#                         data_type = attr_info.get("data_type", "unknown")
#                         if data_type in ["integer", "float"]:
#                             numeric_attrs.append((attr_name, attr_info))
#                         elif data_type in ["date", "datetime"]:
#                             date_attrs.append((attr_name, attr_info))
#                         else:
#                             text_attrs.append((attr_name, attr_info))

#                     # Numeric attributes analysis
#                     if numeric_attrs:
#                         result += f"🔢 NUMERIC ATTRIBUTES ({len(numeric_attrs)}):\n"
#                         for attr_name, attr_info in numeric_attrs:
#                             result += f"   • {attr_name}: {attr_info.get('data_type', 'unknown')} "
#                             result += f"({attr_info.get('count', 0)} values)\n"

#                             if attr_info.get("sample_values"):
#                                 samples = ", ".join(
#                                     map(str, attr_info["sample_values"][:3])
#                                 )
#                                 result += f"     Sample values: {samples}\n"
#                             result += "\n"

#                     # Text attributes analysis
#                     if text_attrs:
#                         result += f"📝 TEXT ATTRIBUTES ({len(text_attrs)}):\n"
#                         for attr_name, attr_info in text_attrs:
#                             result += f"   • {attr_name}: {attr_info.get('data_type', 'unknown')} "
#                             result += f"({attr_info.get('count', 0)} values)\n"

#                             if attr_info.get("sample_values"):
#                                 samples = ", ".join(
#                                     map(str, attr_info["sample_values"][:3])
#                                 )
#                                 result += f"     Sample values: {samples}\n"
#                             result += "\n"

#                     # Analysis insights
#                     result += "💡 ANALYSIS INSIGHTS:\n"
#                     if numeric_attrs:
#                         result += f"   • Found {len(numeric_attrs)} numeric attribute(s) suitable for statistical analysis\n"
#                         result += "   • Can perform population analysis, filtering, and visualization\n"
#                     if text_attrs:
#                         result += f"   • Found {len(text_attrs)} text attribute(s) for categorical analysis\n"

#                     result += "\n🔧 SUGGESTED ACTIONS:\n"
#                     if numeric_attrs:
#                         top_numeric = numeric_attrs[0][0]  # First numeric attribute
#                         result += f"   • Try: analyze_population(layer_name='{layer.name}', population_field='{top_numeric}')\n"
#                         result += f"   • Try: get_attribute_stats(layer_name='{layer.name}', attribute_key='{top_numeric}')\n"
#                 else:
#                     result += "No attributes found for this layer.\n"
#             except Exception as e:
#                 result += f"Could not retrieve attribute information: {str(e)}\n"

#             return result

#         except Layer.DoesNotExist:
#             return f"Layer {layer_id} not found"
#         except Exception as e:
#             logger.error(f"Error in layer analysis: {str(e)}")
#             return f"Error in layer analysis: {str(e)}"

#     async def _web_search_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for web search tool"""
#         query = args.get("query")
#         max_results = args.get("max_results", 5)

#         if not query:
#             return "Error: No search query provided"

#         try:
#             async with httpx.AsyncClient(timeout=120.0) as client:
#                 # DuckDuckGo Instant Answer API
#                 ddg_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
#                 response = await client.get(ddg_url)

#                 if response.status_code == 200:
#                     data = response.json()
#                     results = []

#                     # Add abstract if available
#                     if data.get("Abstract"):
#                         results.append(f"Summary: {data['Abstract']}")
#                         if data.get("AbstractURL"):
#                             results.append(f"Source: {data['AbstractURL']}")

#                     # Add definition if available
#                     if data.get("Definition"):
#                         results.append(f"Definition: {data['Definition']}")

#                     # Add related topics
#                     if data.get("RelatedTopics"):
#                         topics = data["RelatedTopics"][:max_results]
#                         for i, topic in enumerate(topics, 1):
#                             if isinstance(topic, dict) and topic.get("Text"):
#                                 results.append(f"{i}. {topic['Text']}")

#                     if results:
#                         return f"Search results for '{query}':\n" + "\n".join(results)
#                     else:
#                         return f"No search results found for '{query}'"
#                 else:
#                     return f"Search request failed with status code: {response.status_code}"

#         except Exception as e:
#             logger.error(f"Error in web search: {str(e)}")
#             return f"Error performing web search: {str(e)}"

#     async def _calculate_handler(self, args: Dict[str, Any]) -> str:
#         """Handler for calculator tool"""
#         expression = args.get("expression")
#         try:
#             # Safe evaluation of mathematical expressions
#             allowed_names = {
#                 k: v
#                 for k, v in __builtins__.items()
#                 if k in ["abs", "round", "min", "max"]
#             }
#             allowed_names.update(
#                 {
#                     "pow": pow,
#                     "sqrt": lambda x: x**0.5,
#                     "pi": 3.14159265359,
#                     "e": 2.71828182846,
#                 }
#             )

#             result = eval(expression, {"__builtins__": {}}, allowed_names)
#             return f"Result: {result}"
#         except Exception as e:
#             return f"Error calculating: {str(e)}"


# # Global instance
# mcp_server = DjangoMCPServer()
