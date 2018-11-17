from rest_framework import serializers
from multidb_account.achievements.models import Badge, Achievement


class AchievementSerializer(serializers.ModelSerializer):
    """
    User achievements serializer.
    """

    badge_id = serializers.IntegerField()
    team = serializers.CharField(required=False, allow_blank=True)
    competition = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Achievement
        read_only_fields = ('id',)
        fields = read_only_fields + ('title', 'competition', 'date', 'badge_id', 'team')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.badge = None

    def validate_badge_id(self, badge_id):
        user = self.context['request'].user

        try:
            self.badge = Badge.objects.using(user.country).get(pk=badge_id)
        except Badge.DoesNotExist:
            raise serializers.ValidationError({"badge_id": "Unknown badge_id."})

    def validate(self, attrs):
        attrs = super().validate(attrs)

        user = self.context['request'].user
        attrs['created_by'] = user

        if self.badge is not None:
            attrs['badge'] = self.badge

        attrs.pop('badge_id', None)

        return attrs

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['created_by'].country).create(**validated_data)


class BadgeSerializer(serializers.ModelSerializer):
    """
    Badge serializer.
    """

    class Meta:
        model = Badge
        read_only_fields = fields = ('id', 'name', 'image_url')

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['user'].country).create(**validated_data)
