from rest_framework import serializers

from multidb_account.education.models import Education


class EducationSerializer(serializers.ModelSerializer):
    """
    User educations serializer.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = Education
        read_only_fields = ('id', 'user')
        fields = read_only_fields + ('gpa', 'school', 'current')

    def create(self, validated_data):
        return self.Meta.model.objects.db_manager(validated_data['user'].country).create(**validated_data)
