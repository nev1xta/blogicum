from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

    def ready(self):
        from django.core.mail.backends import filebased, locmem

        class EmailBackend(filebased.EmailBackend):
            pass

        EmailBackend.__module__ = locmem.__name__
        locmem.EmailBackend = EmailBackend
