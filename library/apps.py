from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'

    def ready(self):
        import library.signals
        # import library.admin  # Ensure admin customizations are loaded
        # import library.views  # Ensure views are loaded
        # import library.tasks  # Ensure tasks are loaded
        # import library.management.commands.seed_data  # Ensure seed command is loaded
