from rest_framework import serializers

from apps.staff.models import Staff


class StaffSerializer(serializers.ModelSerializer):
    prefixed_id = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()
    mobile_telephone = serializers.CharField(read_only=True)
    current_picture_url = serializers.SerializerMethodField()
    picture_url = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = (
            "id",
            "prefixed_id",
            "full_name",
            "first_name",
            "last_name",
            "email",
            "mobile_telephone",
            "job_title",
            "is_departed",
            "current_picture_url",
            "picture_url",
            "photo_url",
            "thumbnail_url",
        )

    def get_full_name(self, obj):
        return str(obj).strip()

    def get_current_picture_url(self, obj):
        return str(obj.picture) if obj.picture else None

    def get_picture_url(self, obj):
        return self.get_current_picture_url(obj)

    def get_photo_url(self, obj):
        return self.get_current_picture_url(obj)

    def get_thumbnail_url(self, obj):
        return self.get_current_picture_url(obj)
