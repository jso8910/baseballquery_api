from django.db import models
import uuid

# Create your models here.
class SavedQuery(models.Model):
    key = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    params = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "key": str(self.key),
            "created_at": self.created_at.isoformat(),
            "params": self.params,
        }