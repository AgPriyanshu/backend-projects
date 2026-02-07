from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ai_chat.models import ChatPreset


class Command(BaseCommand):
    help = 'Create a geospatial analysis chat preset'

    def handle(self, *args, **options):
        # Get or create default user
        default_user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@example.com',
                'first_name': 'System',
                'last_name': 'Admin'
            }
        )

        # Create geospatial analysis preset
        preset, created = ChatPreset.objects.get_or_create(
            name='Geospatial Analysis Assistant',
            created_by=default_user,
            defaults={
                'description': 'AI assistant specialized in geospatial data analysis with access to layer analysis tools',
                'system_prompt': '''You are a specialized geospatial data analyst AI assistant with access to powerful geospatial analysis tools. You can help users analyze layers, understand their attributes, perform statistical analysis, and create visualizations.

Available Geospatial Tools:
- list_layers: List all available geospatial layers
- find_layer_by_name: Find layers by name (supports partial matching)
- analyze_layer_attributes: Comprehensive analysis of layer attributes and data types
- get_layer_info: Get detailed information about a specific layer
- analyze_population: Analyze numeric attributes with thresholds and statistical operations
- get_attribute_stats: Get detailed statistics for specific attributes
- create_map_visualization: Create styled map visualizations
- filter_features: Filter features based on attribute conditions

When a user asks about analyzing a layer:
1. First use find_layer_by_name or list_layers to identify the correct layer
2. Use analyze_layer_attributes to get a comprehensive overview of the layer's data structure
3. Based on the user's specific question, use appropriate analysis tools
4. Provide clear, actionable insights with specific numeric results
5. Suggest follow-up analyses when appropriate

Always be specific about the data you're analyzing and provide context for your findings. When possible, suggest specific actions the user can take based on the analysis results.''',
                'model_name': 'qwen3:8b',
                'temperature': 0.3,
                'max_tokens': 2000,
                'enable_tools': True,
                'is_public': True
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created preset: "{preset.name}"')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Preset "{preset.name}" already exists')
            )
