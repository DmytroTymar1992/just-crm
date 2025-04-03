from django.db import models

class Visitor(models.Model):
    visitor_id = models.CharField(max_length=50, unique=True)
    ip_address = models.GenericIPAddressField()
    first_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visitor {self.visitor_id} from {self.ip_address}"
