from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import async_to_sync
from ai_chat.services import ChatService
from ai_chat.models import LLMModel


class Command(BaseCommand):
    help = 'Sync available LLM models from the LLM server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--set-default',
            type=str,
            help='Set a specific model as default after syncing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting LLM model synchronization...')
        )

        try:
            # Create chat service and sync models
            chat_service = ChatService()
            async_to_sync(chat_service.sync_models)()

            # Get updated model list
            available_models = LLMModel.objects.filter(is_available=True)
            unavailable_models = LLMModel.objects.filter(is_available=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully synced {available_models.count()} available models'
                )
            )

            if available_models:
                self.stdout.write('\nAvailable models:')
                for model in available_models:
                    status = ' (DEFAULT)' if model.is_default else ''
                    self.stdout.write(f'  - {model.display_name}{status}')

            if unavailable_models:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n{unavailable_models.count()} models are currently unavailable:'
                    )
                )
                for model in unavailable_models:
                    self.stdout.write(f'  - {model.display_name}')

            # Set default model if specified
            if options['set_default']:
                default_model_name = options['set_default']
                try:
                    model = LLMModel.objects.get(name=default_model_name, is_available=True)
                    
                    # Clear existing default
                    LLMModel.objects.filter(is_default=True).update(is_default=False)
                    
                    # Set new default
                    model.is_default = True
                    model.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Set {model.display_name} as the default model'
                        )
                    )
                except LLMModel.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Model "{default_model_name}" not found or not available'
                        )
                    )

            # Check if we have any default model
            if not LLMModel.objects.filter(is_default=True, is_available=True).exists():
                if available_models:
                    # Set first available model as default
                    first_model = available_models.first()
                    first_model.is_default = True
                    first_model.save()
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f'No default model set. Automatically set {first_model.display_name} as default'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            'No available models found. Please check your LLM server connection.'
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error syncing models: {str(e)}')
            )
            raise 